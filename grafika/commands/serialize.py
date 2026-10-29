"""TUI wrapper for base JSON re-serialization. Delegates to core.cmd_serialize."""
import core
import ui


def run():
    ui.header("Serialize Base JSONs")
    ui.info("Re-serializes game .bins to tool/data/materials only.")
    ui.info("No vanilla backup/diff ceremony (use Extract for that).")
    print()
    core.cmd_serialize()
    print()
    ui.success("Serialize finished.")
