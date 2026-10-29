"""TUI wrapper for vanilla restore. Delegates to core.cmd_reset."""
import core
import ui


def run():
    ui.header("Reset To Vanilla")
    ui.warn("This restores vanilla game materials from the backup.")
    print()
    if not ui.prompt_confirm("Restore vanilla materials?", default=False):
        ui.info("Reset cancelled.")
        return
    print()
    core.cmd_reset()
    print()
    ui.success("Reset finished.")
