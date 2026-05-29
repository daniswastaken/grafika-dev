# Grafika Toolset Documentation

Grafika uses custom Python scripts to wrap `lazurite` and manage RenderDragon material builds.

## Table of Contents
- [Entry Point: `__main__.py` & `cli.py`](#entry-point)
- [Setup: `setup.py`](#setup)
- [Compiler: `build.py`](#compiler)
- [Packer & Deployer: `pack.py`](#packer)
- [Material Updater: `update_mats.py`](#material-updater)
- [Batch Compiler: `batch_compile.py`](#batch-compiler)
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
  - `update`: Update material data from JSONs.
- **Global Args**:
  - `-p {android,windows,merged,ios}`: Build profile (Default: OS native).
  - `--lite`: Use `config_lite.h` (defines `LITE_CONFIG` macro).

---

## Setup: `setup.py`

### Function
Initializes `tool/data/` with required binaries and base data.

### Actions
1. **Download `shaderc`**: Fetch platform-specific BGFX shader compiler.
2. **Download Base Materials**: Fetch `materials.zip` containing vanilla material headers (JSON).
3. **Termux Fix**: Copy `libc++_shared.so` if running on Android Termux.
4. **Persistence**: Saves config to `tool/data/.builder.pkl`.

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
- Reads `src/materials/project.json` for base profile and platform targets.
- Merges project shader code (`.sc`, `.def.sc`) with base material data from `tool/data/materials/`.
- Output: `.material.bin` files in `build/<profile>/`.

### Usage
```bash
python tool mats [-m MaterialName] [-s SUBPACK_DEFINE]
```
- `-m`: List of materials to build (e.g., `RenderChunk Sky`). If omitted, builds all.
- `-s`: Macro to define during compilation (e.g., `NO_WAVE`).

---

## Packer & Deployer: `pack.py`

### Function
Orchestrates full build, packaging, and local deployment.

### Pipeline
1. **Clean**: Wipe `build/pack-<profile>/`.
2. **Assets**: Copy `assets/` to build dir.
3. **Compile Default**: Build all materials with `default` define.
4. **Compile Subpacks**: Iterates `src/newb/pack_config.toml` subpacks, building specific materials for each.
5. **Manifest**: Generate `manifest.json` with UUIDs and versioning.
6. **Labeling**: Inject version strings into shader binary headers (if not `--no-label`).
7. **Archive**: Create `.mcpack` (or `.zip` for iOS).
8. **Auto-Deploy**: If profile is `windows` and `GRAFIKA_DEPLOY_PATH` (in `util.py`) exists, copies `.bin` files directly to your Minecraft development pack.

### Usage
```bash
python tool pack [-v version_number] [--no-zip] [--no-label]
```

---

## Material Updater: `update_mats.py`

### Function
Critical tool for Minecraft version updates. Converts game-extracted JSONs into `lazurite` base materials.

### Input Format (Extracted JSON)
The script expects JSON files (e.g., from `MaterialBinTool`) containing:
- `version`: Material format version.
- `propertyFieldMap`: Uniform definitions.
- `samplerDefinitionMap`: Buffer/Texture sampler definitions.

#### Raw Data Handling
- **Vector Data**: Standard `[x, y, z, w]` arrays.
- **Matrix Data**: If `matrixData` is a byte array (integers), the script unpacks it into a list of floats using `struct.unpack("<f"...)`.

### Process
1. **Map Types**:
   - `Type2D` -> `0`, `Type2DArray` -> `1`, `TypeCube` -> `4`.
   - `Read` -> `1`, `Write` -> `2`, `ReadWrite` -> `3`.
2. **Merge/Create**:
   - If `.material.json` exists in `tool/data/materials`, it updates the version, parent, buffers, and uniforms.
   - If new, it creates a minimal `lazurite v0.8.3` material structure.

### Usage
```bash
python tool update --src "C:/Path/To/JSONs" [--dest "tool/data/materials"]
```

---

## Batch Compiler: `batch_compile.py`

### Function
Root script to automate compilation for all platforms and configurations (Full/Lite).

### Actions
1. **Clean**: Removes and recreates `build/` directory.
2. **Iterate Platforms**: Loops through `android`, `windows`, `merged`, `ios`.
3. **Double Build**: Compiles both `Full` and `Lite` versions for every platform.
4. **Organization**: Moves output to `build/<platform>_<config>/` (e.g., `build/windows_lite`).

### Usage
```bash
python batch_compile.py
```

---

## Utilities: `util.py`

- **`check_conf`**: Verifies `shaderc` and materials are present and match current platform.
- **`create_pack_manifest`**: Template for `manifest.json`.
- **`GRAFIKA_DEPLOY_PATH`**: Hardcoded path used by `pack.py` for direct shader hot-swapping during development.

## Hardcoded Paths (To be fixed)
- `util.py`: `GRAFIKA_DEPLOY_PATH`
