"""TUI wrapper for .mcpack build. Delegates to core.cmd_pack."""
import core
import ui


def run():
    ui.header("Build Resource Pack")
    ui.info("Compiles multiplatform mats + assembles the .mcpack (mirrors `tool pack`).")
    ui.info("Output lands in build/. Non-destructive (game files untouched).")
    print()
    version = ui.prompt("Version override (eg: 46, empty = pack_config.toml)", default="")
    output = ui.prompt_choice("Pack output", ["Archive (.mcpack)", "Folder only (no zip)"])
    print()
    core.cmd_pack(no_zip=(output != "Archive (.mcpack)"), version=version)
    print()
    ui.success("Pack finished.")
