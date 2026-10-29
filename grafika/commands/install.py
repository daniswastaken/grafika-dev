"""TUI wrapper for compile + inject. Delegates to core.cmd_install."""
import core
import ui


def run():
    ui.header("Install Shader")
    ui.warn("This compiles multiplatform mats and REPLACES game files.")
    print()
    if not ui.prompt_confirm("Compile and inject into the game?", default=False):
        ui.info("Install cancelled.")
        return
    print()
    core.cmd_install()
    print()
    ui.success("Install finished.")
