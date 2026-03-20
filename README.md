# Grafika

**Grafika** is a high-performance, anime-style shader pack for Minecraft Bedrock (RenderDragon), built upon the solid foundation of **Newb Shaders**. It focuses on delivering a "next-gen" visual experience while maintaining the lightweight spirit of its predecessor.

## 🎨 Why Anime-Style?
The "anime-style" aesthetic is defined by its clean, sharp visual separation. By implementing a dedicated **Stencil Outline System**, Grafika gives every entity a distinct border—much like the hand-drawn lines found in traditional anime art. This ensures that characters and mobs stand out vividly against the environment, creating a stylized, high-fidelity look.

## ✨ Key Modifications & Features

### 🌌 The Singularity (End Sky)
The highlight of Grafika is a completely custom, procedurally rendered **Black Hole** in the End dimension.
- **Gravitational Lensing**: Light from the background stars and nebulae bends realistically around the event horizon.
- **Accretion Disk**: A multi-layered, swirling plasma disk with "white-hot" heat falloff and turbulent noise.
- **Photon Rings**: Layered cinematic rings (inner and outer) that create a high-fidelity "Gargantua" style aesthetic.
- **Dynamic Animation**: The disk and lensing effects are fully animated for a living, breathing void.

### 💡 Advanced Lighting & Atmosphere
- **Glowing Ores**: Implements high-intensity emissive textures with a subtle shimmering effect for all ore types.
- **Fluorescent End Stone**: End Stone features a vibrant, multi-layered purple glow that pulses with the dimension's energy.
- **Cinematic Overworld**: Tuned sun/moon paths, custom fog densities, and a refined color palette for a more immersive experience.
- **Enhanced Lava**: A custom noise-based "lava bump" effect that adds depth and movement to lava surfaces.
- **Optimized Performance**: Despite the advanced effects, Grafika remains highly optimized for mobile and desktop devices.

## 📥 Installation & Usage
For installation instructions, please refer to the [Resource Pack README](https://github.com/daniswastaken/grafika).


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

## 📜 Credits & License
- **Base Shader**: [Newb Shaders](https://github.com/devendrn/newb-shader-mcbe) by devendrn.
- **Modifications**: daniswastaken.
- **License**: The "Newb Shader" source code is licensed under the **MIT License**. You are free to modify, distribute, and create derivative works based on the source code.
