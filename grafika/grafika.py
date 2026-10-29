"""grafika.py - thin CLI entry. Flags run headless; no args launches the TUI.

Usage:
    python grafika/grafika.py --extract   # serialize ALL vanilla .bins -> tool/data/materials
    python grafika/grafika.py --serialize # re-serialize base JSONs only (no backup/diff)
    python grafika/grafika.py --install   # compile multiplatform mats + inject into game
    python grafika/grafika.py --reset     # restore vanilla .bins from backup
    python grafika/grafika.py --pack      # build .mcpack resource pack
    python grafika/grafika.py             # launch interactive TUI

Runs in the current terminal (Warp/bash/cmd). No forced popup window:
elevation only happens with --elevate (gsudo = same window, else UAC window)
or when you launch the terminal itself as admin.
Normal stable edition only (C:\\XboxGames\\Minecraft for Windows). No Preview.
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import core


def main() -> None:
    ap = argparse.ArgumentParser(
        prog="grafika",
        description="Dev tool: extract vanilla base, compile shader, inject/reset game materials. "
                    "No flags launches the interactive TUI.")
    g = ap.add_mutually_exclusive_group(required=False)
    g.add_argument("--extract", action="store_true",
                   help="serialize ALL game .bins to tool/data/materials (overwrites)")
    g.add_argument("--serialize", action="store_true",
                   help="re-serialize game .bins to base JSONs only (no vanilla backup/diff)")
    g.add_argument("--install", action="store_true",
                   help="compile multiplatform mats and inject produced bins into game")
    g.add_argument("--reset", action="store_true",
                   help="restore vanilla game materials from backup")
    g.add_argument("--pack", action="store_true",
                   help="build .mcpack resource pack (mirrors `tool pack`)")
    ap.add_argument("--no-zip", action="store_true",
                    help="pack: don't make archive")
    ap.add_argument("--no-label", action="store_true",
                    help="pack: don't label materials")
    ap.add_argument("--lite", action="store_true",
                    help="install/pack: use config_lite.h (Lite tier)")
    ap.add_argument("-v", default="",
                    help="pack: version number override eg: 46")
    ap.add_argument("--elevate", action="store_true",
                    help="re-launch elevated first (gsudo = same window, else UAC popup)")
    ap.add_argument("--plain", action="store_true",
                    help="force plain TUI (no ANSI chatbox, for dumb terminals)")
    args = ap.parse_args()

    if args.plain:
        os.environ["GRAFIKA_PLAIN"] = "1"

    if args.extract:
        if args.elevate:
            core.ensure_admin(["--extract"])
        else:
            core.note_admin()
        core.run_cli_action("extract")
    elif args.serialize:
        if args.elevate:
            core.ensure_admin(["--serialize"])
        else:
            core.note_admin()
        core.run_cli_action("serialize")
    elif args.install:
        if args.elevate:
            core.ensure_admin(["--install"] + (["--lite"] if args.lite else []))
        else:
            core.note_admin()
        core.run_cli_action("install", lite=args.lite)
    elif args.reset:
        if args.elevate:
            core.ensure_admin(["--reset"])
        else:
            core.note_admin()
        core.run_cli_action("reset")
    elif args.pack:
        if args.elevate:
            pack_argv = ["--pack"]
            if args.no_zip:
                pack_argv.append("--no-zip")
            if args.no_label:
                pack_argv.append("--no-label")
            if args.v:
                pack_argv += ["-v", args.v]
            if args.lite:
                pack_argv.append("--lite")
            core.ensure_admin(pack_argv)
        else:
            core.note_admin()
        core.run_cli_action("pack", no_zip=args.no_zip,
                            no_label=args.no_label, version=args.v, lite=args.lite)
    else:
        if args.elevate:
            core.ensure_admin([])
        else:
            core.note_admin()
        import ui
        if args.plain:
            ui.set_plain(True)
        from app import start
        start()


if __name__ == "__main__":
    main()
