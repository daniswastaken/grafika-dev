"""Read-only overview: game / base / backup / install state."""
import core
import ui


def run():
    ui.header("State Overview")

    # game
    try:
        bins = core.list_game_bins()
        ui.info(f"Game v{core.game_version()} - {len(bins)} .bin files")
    except SystemExit:
        ui.error("Game materials dir not found.")
        print()
        return

    # game dir state: vanilla vs injected (names only, capped)
    injected = []
    for b in bins:
        try:
            if not core.is_pristine(core.material_platforms(b)):
                injected.append(b.name)
        except Exception:
            injected.append(f"{b.name} (unreadable)")
    if injected:
        ui.warn(f"Game dir: INJECTED ({len(injected)} files)")
        for name in injected[:15]:
            print(f"      - {name}")
        if len(injected) > 15:
            print(f"      ... and {len(injected) - 15} more")
    else:
        ui.success("Game dir: vanilla")

    # base JSONs
    if core.MATERIALS_JSON_DIR.is_dir():
        n = len(list(core.MATERIALS_JSON_DIR.glob("*.material.json")))
        ui.info(f"Base JSONs: {n} in tool/data/materials")
    else:
        ui.warn("Base JSONs: none (run extract)")

    # vanilla backup
    snap = core.load_json(core.VANILLA_MANIFEST)
    if snap.get("files"):
        ui.info(f"Vanilla backup: {len(snap['files'])} files "
                f"(game v{snap.get('game_version')}, {snap.get('snapshot_time')})")
    else:
        ui.warn("Vanilla backup: none")

    # install record
    inst = core.load_json(core.INSTALL_MANIFEST)
    if inst.get("files"):
        ui.info(f"Installed: {len(inst['files'])} files ({inst.get('install_time')})")
    else:
        ui.info("Installed: nothing recorded")

    print()
