"""Dual-layout tolerant serialization for lazurite.

Minecraft 1.26.60 ships material version 26 in TWO buffer layouts:

- new: 4-byte `unknown` field after `binding_slot` (most files; read
  stock by lazurite 0.11+)
- legacy: no `unknown` field (9 materials e.g. Actor, RenderChunk,
  untouched since 1.26.52; only lazurite <= 0.10 could read these)

Both claim version 26 in the header, so the layout cannot be told apart
beforehand: lazurite 0.12 fails on the 9 legacy files
(`UnicodeDecodeError` inside `Buffer.read`), lazurite 0.10 fails on the
rest (`BufferType` errors). serialize_bins reads every file with the
stock layout and retries each failure with the legacy reader, so one
lazurite version handles the whole game dir.
"""

from pathlib import Path

from lazurite import util
from lazurite.material import Material
from lazurite.material.buffer import (
    Buffer,
    BufferAccess,
    BufferType,
    Precision,
    SamplerState,
)

_ORIGINAL_READ = Buffer.read


def _read_legacy_layout(self, file, version):
    """Buffer.read for the pre-1.26.60 layout: no `unknown` field for v26."""
    self.name = util.read_string(file)
    self.register_slot = util.read_ushort(file)
    self.access = BufferAccess(util.read_ubyte(file))
    self.precision = Precision(util.read_ubyte(file))
    self.unordered_access = util.read_bool(file)
    self.type = BufferType(util.read_ubyte(file))
    self.texture_format = util.read_string(file)
    self.slot_count = util.read_ulong(file)
    self.binding_slot = util.read_ubyte(file)
    # legacy layout: sampler bool follows binding_slot directly (no unknown)
    if util.read_bool(file):
        self.sampler_state = SamplerState(util.read_ubyte(file))

    if util.read_bool(file):
        self.default_texture = util.read_string(file)
    else:
        self.default_texture = ""

    if util.read_bool(file):
        self.texture_path = util.read_string(file)

    if util.read_bool(file):  # CustomTypeInfo
        self.custom_type_info = self.CustomTypeInfo(
            util.read_string(file), util.read_ulong(file)
        )

    return self


def serialize_bins(bins: list[Path], out_dir: Path) -> None:
    """Serialize game material bins to minimal JSONs, replicating
    `python -m lazurite serialize` output exactly (post-run diff checked
    byte-for-byte in test)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for src in bins:
        name = src.name.removesuffix(Material.EXTENSION)
        try:
            material = Material.load_bin_file(str(src))
        except Exception:
            # legacy-layout file: retry with the pre-1.26.60 buffer reader
            Buffer.read = _read_legacy_layout
            try:
                material = Material.load_bin_file(str(src))
            finally:
                Buffer.read = _ORIGINAL_READ

        material.buffers.sort(key=lambda x: x.name)
        material.uniforms.sort(key=lambda x: x.name)
        material.passes.sort(key=lambda x: x.name)
        material.sort_variants()

        material.store_minimal(name, str(out_dir))
        print(name, flush=True)
