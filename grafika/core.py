R"""core.py - shared logic for grafika: extract -> compile -> inject -> reset.

Imported by both the CLI entry (grafika.py) and the TUI (app.py / commands/*).
All long-running work lives here; UI layers only dispatch + confirm.
"""

import ctypes
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

GAME_DIR = Path(r"C:\XboxGames\Minecraft for Windows\Content")
GAME_MATERIALS_DIR = GAME_DIR / "data" / "renderer" / "materials"
GAME_PROCESS = "Minecraft.Windows.exe"

ELEVATE_GUARD_ENV = "GRAFIKA_ELEVATED"
RETRIES = 10
RETRY_DELAY = 1.0


# ---------- repo layout ----------

def find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in (here.parent, *here.parents):
        if (parent / "tool" / "__main__.py").exists() and (parent / "src" / "materials").exists():
            return parent
    # fallback: cwd
    return Path.cwd()


ROOT = find_repo_root()
DATA_DIR = ROOT / "tool" / "data"
MATERIALS_JSON_DIR = DATA_DIR / "materials"
VANILLA_DIR = DATA_DIR / "vanilla"
VANILLA_MANIFEST = DATA_DIR / "vanilla_manifest.json"
INSTALL_MANIFEST = DATA_DIR / "install_manifest.json"
BUILD_MULTI = ROOT / "build" / "multiplatform"
SHADERC = DATA_DIR / ("shaderc.exe" if os.name == "nt" else "shaderc")


# ---------- helpers ----------

def log(msg: str) -> None:
    print(msg, flush=True)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def game_version() -> str:
    try:
        tree = ET.parse(GAME_DIR / "appxmanifest.xml")
        for el in tree.getroot().iter():
            if el.tag.endswith("Identity"):
                return el.attrib.get("Version", "unknown")
    except Exception:
        pass
    return "unknown"


def list_game_bins() -> list[Path]:
    if not GAME_MATERIALS_DIR.is_dir():
        log(f"Error: game materials dir not found: {GAME_MATERIALS_DIR}")
        sys.exit(1)
    return sorted(p for p in GAME_MATERIALS_DIR.glob("*.material.bin") if p.is_file())


def material_platforms(bin_path: Path) -> set[str]:
    from lazurite.material import Material
    return {p.name for p in Material.load_bin_file(str(bin_path)).get_platforms()}


def is_pristine(platforms: set[str]) -> bool:
    # Vanilla Windows bins carry ONLY Direct3D_* platforms (or none at all
    # for shaderless data-only materials like BRDF/PostFX).
    # Our compiled multiplatform bins carry ESSL_*/Metal -> modified.
    return all(p.startswith("Direct3D_") for p in platforms)


# ---------- admin ----------

def is_admin() -> bool:
    if os.name != "nt":
        return True
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def ensure_admin(argv: list[str]) -> None:
    """Re-launch elevated. Prefers gsudo (same window) so Warp/bash keep
    working; falls back to UAC runas (opens a new window). Opt-in only —
    normal runs stay in the current terminal, no popup."""
    if os.name != "nt":
        return
    if os.environ.get(ELEVATE_GUARD_ENV) == "1":
        if not is_admin():
            log("Error: administrator rights required. Re-run and accept the UAC prompt.")
            sys.exit(1)
        return
    if is_admin():
        return
    entry = str(Path(__file__).resolve().parent / "grafika.py")
    if shutil.which("gsudo"):
        log("Elevating in place via gsudo...")
        r = subprocess.run(["gsudo", sys.executable, entry, *argv])
        sys.exit(r.returncode)
    log("Requesting administrator rights (new window)...")
    log("Tip: `winget install gsudo` enables same-window elevation for Warp/bash.")
    os.environ[ELEVATE_GUARD_ENV] = "1"
    try:
        rc = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{entry}" {subprocess.list2cmdline(argv)}', str(ROOT), 1
        )
        if rc is None or int(rc) <= 32:
            log(f"Error: elevation failed (code {rc}).")
            sys.exit(1)
    except Exception as e:
        log(f"Error: elevation failed: {e}")
        sys.exit(1)
    sys.exit(0)


def note_admin() -> None:
    """One-line notice when running non-elevated. Writes usually succeed
    anyway (game dir grants authenticated users modify); elevation only
    matters if a copy hits PermissionError."""
    if os.name == "nt" and not is_admin():
        log("Note: not running as admin. Trying in place - "
            "use --elevate (or an elevated terminal) if writes get denied.")


# ---------- vanilla backup + version detection ----------

def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def snapshot_vanilla(bins: list[Path]) -> dict:
    """Copy game bins to tool/data/vanilla + write manifest. Returns manifest."""
    VANILLA_DIR.mkdir(parents=True, exist_ok=True)
    old = load_json(VANILLA_MANIFEST)
    old_files = old.get("files", {})
    manifest = {
        "game_version": game_version(),
        "snapshot_time": datetime.now().isoformat(timespec="seconds"),
        "files": {},
    }
    for src in bins:
        digest = sha256_of(src)
        entry = old_files.get(src.name, {})
        if entry.get("sha256") == digest and (VANILLA_DIR / src.name).is_file():
            manifest["files"][src.name] = entry
            continue
        shutil.copy2(src, VANILLA_DIR / src.name)
        manifest["files"][src.name] = {
            "sha256": digest,
            "size": src.stat().st_size,
            "game_version": manifest["game_version"],
        }
    VANILLA_MANIFEST.write_text(json.dumps(manifest, indent=2))
    return manifest


def detect_version_changes(bins: list[Path]) -> list[str]:
    """Compare live game bins against stored vanilla manifest. Returns change lines."""
    old = load_json(VANILLA_MANIFEST)
    old_files = old.get("files", {})
    if not old_files:
        return ["no previous vanilla snapshot"]
    changes = []
    live = {p.name for p in bins}
    for name in sorted(set(old_files) - live):
        changes.append(f"removed from game: {name}")
    for p in bins:
        entry = old_files.get(p.name)
        if entry is None:
            changes.append(f"new in game: {p.name}")
        elif entry.get("sha256") != sha256_of(p):
            changes.append(f"modified in game: {p.name}")
    if old.get("game_version") != game_version():
        changes.append(f"game version: {old.get('game_version')} -> {game_version()}")
    return changes


# ---------- --extract ----------

def _pristine_guard(bins: list[Path]) -> None:
    """Refuse to serialize our own injected output as a vanilla base."""
    bad = []
    for b in bins:
        try:
            plats = material_platforms(b)
        except Exception as e:
            log(f"  skip {b.name}: unreadable ({e})")
            continue
        if not is_pristine(plats):
            bad.append(f"{b.name} [{','.join(sorted(plats))}]")
    if bad:
        log("Error: game folder looks INJECTED, refusing to serialize it as vanilla base:")
        for line in bad:
            log(f"  - {line}")
        log("Run `grafika.py --reset` first (needs tool/data/vanilla backup),")
        log("or repair/reinstall the game, then re-run --extract.")
        sys.exit(1)
    log("Pristine check passed (all Direct3D-only).")


def _serialize_bins(bins: list[Path]) -> None:
    MATERIALS_JSON_DIR.mkdir(parents=True, exist_ok=True)
    log(f"Serializing {len(bins)} materials...")
    try:
        import laz_compat
        laz_compat.serialize_bins(bins, MATERIALS_JSON_DIR)
    except Exception as e:
        log(f"Error: serialize failed: {e}")
        sys.exit(1)


def cmd_extract() -> None:
    bins = list_game_bins()
    log(f"Found {len(bins)} game .bin files (game v{game_version()}).")
    _pristine_guard(bins)

    changes = detect_version_changes(bins)
    if len(changes) == 1 and changes[0] == "no previous vanilla snapshot":
        log("No previous vanilla snapshot, creating one.")
    elif changes:
        log("Game files changed since last snapshot:")
        for line in changes:
            log(f"  - {line}")
    else:
        log("Game files match stored vanilla snapshot.")

    manifest = snapshot_vanilla(bins)
    log(f"Vanilla backup: {len(manifest['files'])} files -> {VANILLA_DIR}")

    _serialize_bins(bins)

    # prune stale outputs (bins removed by a game update)
    expected = {b.name.removesuffix(".material.bin") + ".material.json" for b in bins}
    pruned = 0
    for out in MATERIALS_JSON_DIR.glob("*.material.json"):
        if out.name not in expected:
            out.unlink()
            pruned += 1
    count = len(list(MATERIALS_JSON_DIR.glob("*.material.json")))
    log(f"Done: {count} base JSONs in {MATERIALS_JSON_DIR}" + (f" ({pruned} stale pruned)" if pruned else ""))


def cmd_serialize() -> None:
    """Re-serialize base JSONs from the game bins only (no backup, no diff)."""
    bins = list_game_bins()
    log(f"Found {len(bins)} game .bin files (game v{game_version()}).")
    _pristine_guard(bins)
    _serialize_bins(bins)
    count = len(list(MATERIALS_JSON_DIR.glob("*.material.json")))
    log(f"Done: {count} base JSONs in {MATERIALS_JSON_DIR}")


# ---------- --install ----------

def kill_game() -> None:
    if os.name != "nt":
        return
    r = subprocess.run(["taskkill", "/F", "/IM", GAME_PROCESS],
                       capture_output=True, text=True)
    if r.returncode == 0:
        log("Minecraft process terminated.")
        time.sleep(2.0)
    # else: not running, nothing to do


def copy_verified(src: Path, dst: Path) -> None:
    last: Exception | None = None
    for attempt in range(1, RETRIES + 1):
        try:
            shutil.copy2(src, dst)
            if sha256_of(dst) == sha256_of(src):
                return
            last = RuntimeError("hash mismatch after copy")
        except (PermissionError, OSError, RuntimeError) as e:
            last = e
        time.sleep(RETRY_DELAY)
    raise RuntimeError(f"copy failed after {RETRIES} tries: {src.name} ({last}). "
                       "Re-run with --elevate or from an elevated terminal.")


def cmd_install(lite: bool = False) -> None:
    if not MATERIALS_JSON_DIR.is_dir() or not list(MATERIALS_JSON_DIR.glob("*.material.json")):
        log("Error: no base JSONs. Run `grafika.py --extract` first.")
        sys.exit(1)
    if not SHADERC.is_file():
        log(f"Error: shaderc missing at {SHADERC}. Run build setup first.")
        sys.exit(1)

    if BUILD_MULTI.is_dir():
        shutil.rmtree(BUILD_MULTI)
    log("Compiling multiplatform mats...")
    mats_cmd = [sys.executable, "tool", "mats"]
    if lite:
        mats_cmd.append("--lite")
    r = subprocess.run(mats_cmd, cwd=str(ROOT))
    if r.returncode != 0:
        log("Error: compile failed.")
        sys.exit(1)

    produced = sorted(BUILD_MULTI.glob("*.material.bin"))
    if not produced:
        log("Error: compile produced no bins.")
        sys.exit(1)
    log(f"Compiled {len(produced)} bins.")

    # ensure vanilla backup covers everything we are about to replace
    game_bins = {p.name: p for p in list_game_bins()}
    VANILLA_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_json(VANILLA_MANIFEST)
    if not manifest.get("files"):
        manifest = {"game_version": game_version(),
                    "snapshot_time": datetime.now().isoformat(timespec="seconds"),
                    "files": {}}
    for src in produced:
        live = game_bins.get(src.name)
        if live is None:
            log(f"Warning: {src.name} not present in game dir, skipping.")
            continue
        if not is_pristine(material_platforms(live)):
            log(f"Error: {live.name} in game dir is not vanilla. Run `grafika.py --reset` first.")
            sys.exit(1)
        entry = manifest["files"].get(src.name)
        if entry is None or not (VANILLA_DIR / src.name).is_file():
            shutil.copy2(live, VANILLA_DIR / src.name)
            manifest["files"][src.name] = {"sha256": sha256_of(live),
                                           "size": live.stat().st_size,
                                           "game_version": manifest["game_version"]}
    MANIFEST_TMP = manifest
    VANILLA_MANIFEST.write_text(json.dumps(MANIFEST_TMP, indent=2))

    kill_game()

    install_manifest = {"install_time": datetime.now().isoformat(timespec="seconds"),
                        "game_version": game_version(), "files": {}}
    written: list[Path] = []
    try:
        for src in produced:
            dst = GAME_MATERIALS_DIR / src.name
            if dst.is_file():
                install_manifest["files"][src.name] = {"pre_sha256": sha256_of(dst)}
            else:
                install_manifest["files"][src.name] = {"pre_sha256": None}
            copy_verified(src, dst)
            written.append(dst)
            log(f"  injected {src.name}")
    except Exception as e:
        log(f"Error during injection: {e}")
        log("Rolling back written files from vanilla backup...")
        for dst in written:
            bak = VANILLA_DIR / dst.name
            if bak.is_file():
                try:
                    shutil.copy2(bak, dst)
                    log(f"  rolled back {dst.name}")
                except Exception as e2:
                    log(f"  FAILED to roll back {dst.name}: {e2}")
        sys.exit(1)

    INSTALL_MANIFEST.write_text(json.dumps(install_manifest, indent=2))
    log(f"Installed {len(written)} materials. Manifest -> {INSTALL_MANIFEST}")


# ---------- --reset ----------

def cmd_reset() -> None:
    manifest = load_json(INSTALL_MANIFEST)
    targets = sorted(manifest.get("files", {}))
    if not targets:
        # nothing recorded: fall back to restoring whatever vanilla backup covers
        # among currently non-pristine game files
        log("No install manifest, scanning game dir for injected files...")
        targets = []
        for b in list_game_bins():
            try:
                if not is_pristine(material_platforms(b)):
                    targets.append(b.name)
            except Exception:
                pass
        if not targets:
            log("Nothing to reset: all game materials look vanilla.")
            return
        manifest = {"files": {name: {} for name in targets}}

    kill_game()
    restored, missing = 0, []
    for name in targets:
        bak = VANILLA_DIR / name
        dst = GAME_MATERIALS_DIR / name
        if not bak.is_file():
            missing.append(name)
            continue
        try:
            copy_verified(bak, dst)
            restored += 1
            log(f"  restored {name}")
        except Exception as e:
            log(f"  FAILED {name}: {e}")
    if missing:
        log(f"Warning: no vanilla backup for: {', '.join(missing)}")
    if restored:
        INSTALL_MANIFEST.write_text(json.dumps(
            {"install_time": None, "game_version": game_version(), "files": {}}, indent=2))
    log(f"Reset done: {restored} restored." + (f" {len(missing)} missing backup." if missing else ""))


# ---------- --pack (.mcpack maker, mirrors `tool pack`) ----------

def cmd_pack(no_zip: bool = False, no_label: bool = False, version: str = "", lite: bool = False) -> None:
    if not MATERIALS_JSON_DIR.is_dir() or not list(MATERIALS_JSON_DIR.glob("*.material.json")):
        log("Error: no base JSONs. Run `grafika.py --extract` first.")
        sys.exit(1)
    if not SHADERC.is_file():
        log(f"Error: shaderc missing at {SHADERC}. Run build setup first.")
        sys.exit(1)

    cmd = [sys.executable, "tool", "pack"]
    if no_zip:
        cmd.append("--no-zip")
    if no_label:
        cmd.append("--no-label")
    if version:
        cmd += ["-v", version]
    if lite:
        cmd.append("--lite")
    log("Building .mcpack (multiplatform)...")
    r = subprocess.run(cmd, cwd=str(ROOT))
    if r.returncode != 0:
        log("Error: pack failed.")
        sys.exit(1)
    log("Pack done. Output in build/.")


# ---------- shared entry helper (used by grafika.py; TUI dispatches cmd_* directly) ----------

def run_cli_action(action: str, **kwargs) -> None:
    """Dispatch one CLI action by name. Used by grafika.py entry point."""
    if action == "extract":
        cmd_extract()
    elif action == "serialize":
        cmd_serialize()
    elif action == "install":
        cmd_install(kwargs.get("lite", False))
    elif action == "reset":
        cmd_reset()
    elif action == "pack":
        cmd_pack(kwargs.get("no_zip", False),
                 kwargs.get("no_label", False),
                 kwargs.get("version", ""),
                 kwargs.get("lite", False))
    else:
        raise ValueError(f"Unknown action: {action}")
