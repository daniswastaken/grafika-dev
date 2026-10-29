"""
Main interactive shell - the core loop of grafika TUI.
"""
import shutil

import ui
from commands import extract, install, reset, status, pack, alpha, serialize


COMMANDS = [
    ("extract", "Serialize ALL vanilla game bins to base JSONs"),
    ("serialize", "Re-serialize game bins to base JSONs (no backup/diff)"),
    ("install", "Compile multiplatform mats + inject into game"),
    ("pack",    "Build .mcpack resource pack"),
    ("reset",   "Restore vanilla game materials from backup"),
    ("alpha",   "Merge glow mask into a texture PNG (marks emissive alpha)"),
    ("status",  "Show game / base / backup / install state"),
    ("clear",   "Clear the terminal screen"),
    ("help",    "Show this help message"),
    ("exit",    "Exit grafika"),
]


def _show_help():
    """
    Renders the dynamic help table using the TUI grid system.
    Relies on pre-defined COMMANDS tuple to maintain order and consistent
    formatting without hardcoding spacing logic.
    """
    ui.header("Available Commands")
    ui.show_command_table(COMMANDS)
    print()


def _show_shortcuts():
    """
    Exposes supported keyboard intercepts.
    Standard Windows CMD/PS buffers cannot easily trap Esc or arrow keys
    without extra modules, so we stick to native signals like SIGINT (Ctrl+C).
    """
    shortcuts = [
        ("?", "Show this shortcuts message"),
        ("Ctrl+C", "Cancel the current command"),
    ]
    ui.header("Keyboard Shortcuts")
    ui.show_command_table(shortcuts)
    print()


def _check_status():
    """Validates environment dependencies (Python, lazurite, shaderc)."""
    ui.header("System Status")

    if shutil.which("python") or shutil.which("python3"):
        ui.success("Python - found")
    else:
        ui.error("Python - not found!")

    try:
        import lazurite  # noqa: F401
        ui.success("lazurite - found")
    except ImportError:
        ui.error("lazurite - not found! (pip install -r requirements.txt)")

    try:
        import core
        if core.SHADERC.is_file():
            ui.success(f"shaderc - found ({core.SHADERC})")
        else:
            ui.warn("shaderc - missing (run build setup first)")
    except Exception as e:
        ui.error(f"shaderc check failed: {e}")

    print()


def start():
    """
    Main REPL loop. Dispatches commands while maintaining the TUI layout.
    Core routines call sys.exit() on fatal errors - SystemExit is caught here
    so a failed command returns to the prompt instead of killing the session.
    """
    ui.setup_tui()

    while True:
        cmd = ui.prompt_shell().lower()

        if not cmd:
            continue

        try:
            if cmd in ("exit", "quit", "q"):
                ui.info("Goodbye!")
                ui.reset_tui()
                break
            elif cmd == "?":
                _show_shortcuts()
            elif cmd == "help":
                _show_help()
            elif cmd == "extract":
                extract.run()
            elif cmd == "serialize":
                serialize.run()
            elif cmd == "install":
                install.run()
            elif cmd == "reset":
                reset.run()
            elif cmd == "pack":
                pack.run()
            elif cmd == "alpha":
                alpha.run()
            elif cmd == "status":
                status.run()
            elif cmd == "sysstatus":
                _check_status()
            elif cmd in ("clear", "cls"):
                ui.setup_tui()
            else:
                ui.warn(f"Unknown command: '{cmd}'. Type 'help' for available commands.")
        except SystemExit as e:
            # core.cmd_* exits non-zero on fatal errors; stay in the loop.
            if e.code not in (None, 0):
                ui.error(f"Command failed (exit {e.code}). See output above.")
        except (ui.CancelCommand, KeyboardInterrupt):
            print()
            ui.warn("Command cancelled.")
