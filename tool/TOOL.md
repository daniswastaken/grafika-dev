# Grafika Toolset Documentation

Grafika uses custom Python scripts to wrap `lazurite` and manage RenderDragon material builds.

## Table of Contents
- [Entry Point: `__main__.py` & `cli.py`](#entry-point)
- [Setup: `setup.py`](#setup)
- [Compiler: `build.py`](#compiler)
- [Packer: `pack.py`](#packer)
- [Dev Tool: `grafika/`](#dev-tool)
- [Texture Generator: `gen_proto_texture.py`](#texture-generator)
- [Utilities: `util.py`](#utilities)

---

## Entry Point: `__main__.py` & `cli.py`

### `__main__.py`
- **Function**: Environment validator and launcher.
- **Logic**:
  - Check `requirements.txt` against installed packages using `importlib.metadata`.
  - Warn if versions mismatch or modules are missing.
  - Invoke `cli.main()`.

### `cli.py`
- **Function**: CLI Argument Parser.
- **Usage**: `python tool <subcommand> [args]`
- **Subcommands**:
  - `setup`: Init environment.
  - `mats`: Compile specific materials.
  - `pack`: Build full mcpack.
- **Profile**: Always `multiplatform` (ESSL_300 + Direct3D_SM50 + Metal in one bin set). No `-p` flag.

---

## Setup: `setup.py`

### Function
Initializes `tool/data/` with required binaries.

### Actions
1. **Download `shaderc`**: Fetch platform-specific BGFX shader compiler.
2. **Termux Fix**: Copy `libc++_shared.so` if running on Android Termux.
3. **Persistence**: Saves config to `tool/data/.builder.pkl`.

Note: base materials are **not** downloaded. Generate them from your own game with `python grafika/grafika.py --extract` (see [Dev Tool](#dev-tool)).

### Usage
```bash
python tool setup [--reset]
```
- `--reset`: Wipe `tool/data/` before downloading.

---

## Compiler: `build.py`

### Function
Wrapper for `lazurite.project.compile`. Targets `src/materials/`.

### Logic
- Reads `src/materials/project.json` for the `multiplatform` profile.
- Merges project shader code (`.sc`, `.def.sc`) with base material data from `tool/data/materials/`.
- Output: `.material.bin` files in `build/multiplatform/`.

### Usage
```bash
python tool mats [-m MaterialName] [-s SUBPACK_DEFINE] [--lite]
```
- `-m`: List of materials to build (e.g., `RenderChunk Sky`). If omitted, builds all.
- `-s`: Macro to define during compilation (e.g., `REALISTIC_CLOUDS`).
- `--lite`: Also defines `LITE_CONFIG`.

---

## Packer: `pack.py`

### Function
Orchestrates full build and packaging.

### Pipeline
1. **Clean**: Wipe `build/pack-multiplatform/`.
2. **Assets**: Copy `assets/` to build dir.
3. **Compile Default**: Build all materials with the `default` define.
4. **Compile Subpacks**: Iterates `[[subpack]]` entries in `src/grafika/pack_config.toml`, building each subpack's materials into `subpacks/<name>/renderer/materials/` with its define (e.g. `REALISTIC_CLOUDS`).
5. **Manifest**: Generate `manifest.json` with UUIDs, versioning and subpack list.
6. **Labeling**: Inject version strings into shader binary headers (if not `--no-label`).
7. **Archive**: Create `.mcpack`.

### Usage
```bash
python tool pack [-v version_number] [--lite] [--no-zip] [--no-label]
```

---

## Dev Tool: `grafika/`

Windows-only automation of the edit-compile-test loop: **extract → compile → inject → reset**, against the stable edition at `C:\XboxGames\Minecraft for Windows`.

```
grafika/
  grafika.py  # thin CLI entry (flags headless, no args = TUI)
  core.py     # extract / compile / inject / reset logic
  ui.py       # terminal UI (chatbox + plain fallback, --plain for dumb terminals)
  app.py      # TUI main loop
  commands/   # extract.py serialize.py install.py reset.py status.py pack.py alpha.py
```

### Commands
```bash
python grafika/grafika.py --extract   # serialize ALL vanilla game .bins -> tool/data/materials
python grafika/grafika.py --serialize # re-serialize base JSONs only (no vanilla backup/diff)
python grafika/grafika.py --install   # compile multiplatform mats + inject into game
python grafika/grafika.py --reset     # restore vanilla materials from backup
python grafika/grafika.py --pack      # build .mcpack (mirrors `tool pack`)
python grafika/grafika.py             # interactive TUI
```

### Safety model
- `--extract` refuses an injected game folder (checks that all bins are Direct3D-only) instead of baking your own output into the vanilla base.
- First run snapshots every vanilla bin into `tool/data/vanilla/` with SHA-256 hashes (`vanilla_manifest.json`).
- Every injection copies with hash verification + retry, records the installed set (`install_manifest.json`), kills the running Minecraft process first, and **rolls back automatically on failure**.
- `--reset` restores exactly the recorded install set; falls back to scanning for non-pristine bins if no manifest exists.
- Elevation is opt-in (`--elevate`; gsudo in-window when installed, otherwise a UAC popup).

### `alpha` command
TUI-only helper (`commands/alpha.py`): merges a glow mask PNG into a texture PNG in place. Mask colors:
- `FF0000` (red) → texture alpha becomes 253 (weak glow)
- `0000FF` (blue) → texture alpha becomes 252 (full glow)
- `000000` (black) → resets previously marked pixels back to 255
- any other color → pixel untouched

Requires Pillow; marks only apply to fully opaque pixels.

---

## Texture Generator: `gen_proto_texture.py`

Generates cloud textures statistically matching `assets/textures/environment/clouds.png` (same color weights, alpha classes and spatial statistics — nothing is copied from the reference). Requires `numpy` and `pillow`.

```bash
python -m tool.gen_proto_texture [--seed N] [--out PATH] [--stats]

# batch: 10 variants into assets/textures/environment/proto/
python -m tool.gen_proto_texture --batch 10 --out-dir assets/textures/environment/proto
```

---

## Utilities: `util.py`

- **`check_conf`**: Verifies `shaderc` is present and matches the current platform.
- **`create_pack_manifest`**: Template for `manifest.json`.
- **`SHADERC_PATH`**: Location of the downloaded compiler.
