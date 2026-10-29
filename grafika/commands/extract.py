"""TUI wrapper for vanilla base extraction. Delegates to core.cmd_extract."""
import core
import ui


def run():
    ui.header("Extract Vanilla Base")
    ui.info("Serializes ALL game .bins to tool/data/materials (overwrites).")
    ui.info("Refuses automatically if the game folder looks injected.")
    print()
    core.cmd_extract()
    print()
    ui.success("Extract finished.")
