## Building

### Install dependencies
- [Git](https://git-scm.com/)
- [Python](https://www.python.org/) 3.11 or higher required
- Python packages:
  - [lazurite](https://veka0.github.io/lazurite/#installation) (Must be `v0.8.3`. Newer or older version may not be supported)
  - [rich](https://rich.readthedocs.io/en/stable/introduction.html#installation) (Must be `v14.x.x`)

### Get source code
```
git clone https://github.com/devendrn/newb-x-mcbe/
cd newb-x-mcbe
```

### Install dependencies from requirements.txt
*Skip if you already have installed those versions.*
```
python -m pip install -r requirements.txt
```

### Setup build environment
> [!NOTE]
> On Windows, run `.\build.bat` instead of `./build.sh` for all following commands.
```
./build.sh setup
```
This will download shaderc binary and material data required to build shader.

<br>

### Compile specific shader materials
```
./build.sh mats
```
Compiled material.bin files will be inside `build/<platform>/`

**Command usage:**
```
usage: build mats [-h] [-p {android,windows,merged,ios}] [-m M [M ...]] [-s S]

options:
  -h, --help            show this help message and exit
  -p {android,windows,merged,ios}
                        build profile
  -m M [M ...]          build materials (eg: Sky)
  -s S                  subpack config to use (eg: NO_WAVE)
```

### Compile and build full shader pack
```
./build.sh pack
```

The final mcpack will be inside `build/`.

**Command usage:**
```
usage: build pack [-h] [-p {android,windows,merged,ios}] [--no-zip] [--no-label] [-v V]

options:
  -h, --help            show this help message and exit
  -p {android,windows,merged,ios}
                        build profile
  --no-zip              don't make archive
  --no-label            don't label materials
  -v V                  version number eg: 17
```

> [!TIP]
> If you want to customize pack name, author, version and other details, you can do so in `src/newb/pack_config.toml`.

<br>

## Development

Clangd can be used to get code completion and error checks for source files inside include/newb. Fake bgfx header and clangd config are provided for the same.
- **Neovim**: Install clangd LSP.
- **VSCode**: Install [vscode-clangd](https://marketplace.visualstudio.com/items?itemName=llvm-vs-code-extensions.vscode-clangd) extension.

## Updating for New Minecraft Versions

When a new Minecraft update (e.g., 1.26.20) releases, it often changes the underlying material structure, which can break the shader compilation. To fix this, you must update the "source materials" in `tool/data/materials` using the latest game data.

### 1. Extract latest materials
Use a tool like **MaterialBinTool** to unpack the latest `.material.bin` files from the game into `.json` headers.

### 2. Update tool data
Run the provided update script to merge the new game data into the build system:
```powershell
python tool/update_mats.py --src "C:\Path\To\Your\Unpacked\JSONs"
```
This script will:
- Repair old material formats to match `lazurite v0.8.3`.
- Merge latest `version`, `uniforms`, and `buffers` from your JSON files.
- Preserve project-specific shader passes and attributes.

### 3. Rebuild
After updating, run the build command as usual:
```powershell
python tool mats -p windows
```

<br>

## Troubleshooting

### "Unclosed b'NumericLiteral' starting near 1"
This error usually means that the `material.json` or `uniforms` files in `src/materials/` are acting as "pointers" (plain text files containing a path like `../../common/material.json`) but `lazurite` expects valid JSON.
- **Fix**: Replace the pointer files with the actual content of the files they point to.

### "IndexError: list index out of range" during build
This happens when the base materials in `tool/data/materials` are in an older format than what your `lazurite` version expects.
- **Fix**: Run `python tool/update_mats.py` with the `--src` of your latest game JSONs to repair and upgrade the base materials.

<br>

## Credits & License
- **Base Shader**: [Newb Shaders](https://github.com/devendrn/newb-shader-mcbe) by devendrn.
- **Modifications**: daniswastaken.
- **License**: The "Newb Shader" source code is licensed under the **MIT License**. You are free to modify, distribute, and create derivative works based on the source code.
