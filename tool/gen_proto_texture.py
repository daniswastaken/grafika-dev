"""Generate a cloud texture statistically matching ``clouds.png``.

Reference analysis (assets/textures/environment/clouds.png, 256x256, palette
PNG carrying a tRNS chunk) gives **three** RGBA classes:

    (255, 255, 255,   1)  39885 px   60.86 %   background, near-transparent
    (255, 255, 255, 255)  13356 px   20.38 %   opaque white
    (255,  13, 255, 255)  12295 px   18.76 %   magenta

And this spatial structure:

* both coloured classes are fine-grained - autocorrelation 0.58 (white) and
  0.49 (magenta) at lag 1, falling to 0.23-0.37 at lag 2, i.e. blobs a few
  pixels across;
* density is clumped at 16 px (white 16x16 block density std 0.16) but flat
  from 64 px up: the white share of coloured pixels per 64x64 block varies by
  only 0.08, so no region is dominated by one colour;
* the two colours almost never touch - 0.4 % of magenta pixels have an opaque
  white neighbour, and 96 % of magenta pixels touch background;
* component sizes are broad - ~1200 white components, median 2 px, tail past
  64 px.

The reference therefore reads as two interleaved families of cloud masses,
each clumped at blob scale but evenly spread across the tile. The generator
builds each colour independently as a *speckled band*:

1. ``envelope`` - a domain-warped fBm field raised to a power, whose spectrum
   is capped at ~32 lattice cells (8-32 px features). Octaves any coarser than
   that would let one colour's masses claim a whole quadrant of the tile,
   which the reference never does;
2. ``band`` - a level-set band of that envelope, widened until it overfills
   the target pixel count;
3. ``fill`` - low-pass value noise, thinned per pixel by a local density so
   the mass keeps internal grain without breaking into isolated dots;
4. the fill level is scaled to land on the target count and the residual is
   corrected at the most marginal pixels, so the colour weights are exact
   rather than approximate.

The magenta band is additionally cut away from a 1 px dilation of the white
band, which reproduces the phase separation. Nothing is copied from the
reference - the output is a new texture with the same colour weights, alpha
values and spatial statistics.

Usage:
    python -m tool.gen_proto_texture [--seed N] [--out PATH] [--stats]

    # batch: 10 variants into assets/textures/environment/proto/
    python -m tool.gen_proto_texture --batch 10 --out-dir assets/textures/environment/proto
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image

SIZE = 256

# Exact reference pixel counts per class.
COUNT_BG = 39885
COUNT_WHITE = 13356
COUNT_MAGENTA = 12295

RGBA_BG = (255, 255, 255, 1)
RGBA_WHITE = (255, 255, 255, 255)
RGBA_MAGENTA = (255, 13, 255, 255)

# --- field parameters -----------------------------------------------------
# Envelope: fBm over the cells below, amplitude ~ 1/cells**FALLOFF. The
# coarsest octave (32 cells == 8 px) is deliberate: octaves at 2-4 cells
# (128-64 px features) produce large-scale zoning where one colour owns a
# whole region, which the reference does not have. Density is clumped at
# 16 px and flat from 64 px up, exactly like the reference.
ENVELOPE_CELLS = (6, 8, 12, 16, 24, 32, 48, 64)
FALLOFF_WHITE = -0.5
FALLOFF_MAGENTA = -1.0
# gamma skews the envelope towards 0, so masses are patchy rather than evenly
# spread. The reference's 16x16 block density reaches both ~0 and ~0.5, which
# a linear envelope cannot do.
GAMMA_WHITE = 4.0
GAMMA_MAGENTA = 2.0
# How much the fill's local density follows the envelope: 0 = uniform speckle
# inside the band, 1 = density fully modulated by the envelope.
DENSITY_WHITE = 0.75
DENSITY_MAGENTA = 0.5
# Fill noise: low-pass value noise, patchy enough to keep masses connected.
# FILL_CELLS are lattice cells, i.e. 256/64 == 4 px features at the finest.
FILL_CELLS = (160, 128, 96)
FILL_FALLOFF = 0.0
# Band area as a multiple of the target pixel count; the fill level then
# thins the band down to exactly the target.
BAND_OVERFILL = 2.0

# Domain warping bends the envelope so the masses curve instead of reading as
# straight contour lines.
WARP_CELLS = 8
WARP_STRENGTH = 0.55


# --------------------------------------------------------------------------
# periodic value noise
# --------------------------------------------------------------------------
def _lattice(rng: np.random.Generator, cells: int) -> np.ndarray:
    """Random lattice on a torus, so every field tiles seamlessly."""
    return rng.random((cells, cells)).astype(np.float32)


def _sample(lattice: np.ndarray, cells: int) -> np.ndarray:
    """Smoothstep-bilinear resample of a wrapped lattice to SIZE x SIZE."""
    t = np.arange(SIZE, dtype=np.float32) * (cells / SIZE)
    i = t.astype(np.int32)
    f = t - i
    u = f * f * (3.0 - 2.0 * f)
    i0, i1 = i % cells, (i + 1) % cells
    a = lattice[np.ix_(i0, i0)] * (1.0 - u) + lattice[np.ix_(i0, i1)] * u
    b = lattice[np.ix_(i1, i0)] * (1.0 - u) + lattice[np.ix_(i1, i1)] * u
    return a * (1.0 - u)[:, None] + b * u[:, None]


def noise_field(rng: np.random.Generator, falloff: float,
                cells: tuple[int, ...] = ENVELOPE_CELLS) -> np.ndarray:
    """Sum periodic value-noise octaves into a normalised [0, 1] field."""
    field = np.zeros((SIZE, SIZE), dtype=np.float32)
    norm = 0.0
    for c in cells:
        weight = c ** -falloff
        field += weight * _sample(_lattice(rng, c), c)
        norm += weight
    field /= norm
    lo, hi = float(field.min()), float(field.max())
    return (field - lo) / (hi - lo) if hi > lo else field


def envelope_field(rng: np.random.Generator, falloff: float,
                   gamma: float) -> np.ndarray:
    """Domain-warped fBm envelope, skewed towards 0.

    Warping bends the density masses the way the reference's curve; the gamma
    skew makes them patchy.
    """
    base = noise_field(rng, falloff)
    wx = noise_field(rng, 2.0, (WARP_CELLS, WARP_CELLS // 2)) - 0.5
    wy = noise_field(rng, 2.0, (WARP_CELLS, WARP_CELLS // 2)) - 0.5
    gy, gx = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32)
    sx = (gx + WARP_STRENGTH * SIZE * wx / WARP_CELLS) % SIZE
    sy = (gy + WARP_STRENGTH * SIZE * wy / WARP_CELLS) % SIZE
    x0 = sx.astype(np.int32)
    y0 = sy.astype(np.int32)
    ux = 0.5 - 0.5 * np.cos(np.pi * (sx - x0))
    uy = 0.5 - 0.5 * np.cos(np.pi * (sy - y0))

    def at(yy, xx):
        return base[yy % SIZE, xx % SIZE]

    top = at(y0, x0) * (1 - ux) + at(y0, x0 + 1) * ux
    bot = at(y0 + 1, x0) * (1 - ux) + at(y0 + 1, x0 + 1) * ux
    warped = np.clip(top * (1 - uy) + bot * uy, 0.0, None)
    lo, hi = float(warped.min()), float(warped.max())
    return ((warped - lo) / (hi - lo)) ** gamma


# --------------------------------------------------------------------------
# masks
# --------------------------------------------------------------------------
def _dilate(mask: np.ndarray) -> np.ndarray:
    """8-neighbour binary dilation (torus-wrapped)."""
    out = mask.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy or dx:
                out |= np.roll(np.roll(mask, dy, axis=0), dx, axis=1)
    return out


def _repair(mask: np.ndarray, target: int, coin: np.ndarray,
            threshold: np.ndarray, room: np.ndarray) -> None:
    """Nudge a stochastic mask to exactly ``target`` pixels, in place.

    Only pixels inside ``room`` may be promoted, so the repair can never leak
    colour outside the mass it belongs to.
    """
    n = int(mask.sum())
    if n > target:
        margin = np.where(mask, threshold - coin, np.inf)
        idx = np.argsort(margin.ravel(), kind="stable")[:n - target]
        mask.ravel()[idx] = False
    elif n < target:
        margin = np.where(room & ~mask, coin - threshold, np.inf)
        idx = np.argsort(margin.ravel(), kind="stable")[:target - n]
        mask.ravel()[idx] = True


def speckled_band(rng: np.random.Generator, falloff: float, gamma: float,
                  density_weight: float, target: int,
                  avoid: np.ndarray | None = None) -> np.ndarray:
    """Coherent band of the envelope, filled with modulated speckle.

    The reference's cloud masses have a long coherent outline but a
    fine-grained, density-modulated interior. A single threshold cannot do
    both - it either follows the envelope (smooth, no grain) or the noise
    (grain, no coherence) - so the band decides where the colour lives and the
    fill decides which pixels of the band it actually takes. P(coin < c *
    density) == c * density, hence the exact-count repair afterwards.
    """
    envelope = envelope_field(rng, falloff, gamma)
    keep_out = np.zeros((SIZE, SIZE), dtype=bool) if avoid is None else avoid
    free = ~keep_out

    # Widen the band until the pixels left after the keep-out zone overfill
    # the target, so the fill level always has room to work.
    room = int(free.sum())
    overfill = min(int(target * BAND_OVERFILL), room)
    lo, hi = 0.0, 0.5
    band = (np.abs(envelope - 0.5) < 0.2) & free
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        mask = (np.abs(envelope - 0.5) < mid) & free
        n = int(mask.sum())
        if n >= overfill:
            band = mask
        if n < overfill:
            lo = mid
        else:
            hi = mid
    if int(band.sum()) < target:  # degenerate envelope: widen until usable
        band = (np.abs(envelope - 0.5) < 0.45) & free

    dense = envelope_field(rng, falloff, 1.0)
    local_density = (1.0 - density_weight) * 0.5 + density_weight * dense
    coin = noise_field(rng, FILL_FALLOFF, FILL_CELLS)
    scale = min(target / max(local_density[band].sum(), 1e-6), 1.0)
    inside = band & (coin < scale * local_density)
    _repair(inside, target, coin, scale * local_density, band)
    return inside


def build(seed: int) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    white = speckled_band(rng, FALLOFF_WHITE, GAMMA_WHITE, DENSITY_WHITE,
                          COUNT_WHITE)
    magenta = speckled_band(rng, FALLOFF_MAGENTA, GAMMA_MAGENTA,
                            DENSITY_MAGENTA, COUNT_MAGENTA,
                            avoid=_dilate(white))
    return {"white": white, "magenta": magenta,
            "background": ~(white | magenta)}


def render(seed: int) -> Image.Image:
    parts = build(seed)
    out = np.empty((SIZE, SIZE, 4), dtype=np.uint8)
    out[parts["background"]] = RGBA_BG
    out[parts["white"]] = RGBA_WHITE
    out[parts["magenta"]] = RGBA_MAGENTA
    return Image.fromarray(out, "RGBA")


# --------------------------------------------------------------------------
# statistics
# --------------------------------------------------------------------------
def classify(img: Image.Image) -> dict[str, np.ndarray]:
    """Split an RGBA image into the three reference classes."""
    a = np.array(img.convert("RGBA"))
    rgb = a[:, :, :3].astype(int)
    al = a[:, :, 3].astype(int)
    magenta = (al == 255) & (rgb[:, :, 1] < 128)
    white = (al == 255) & (rgb[:, :, 0] == 255) & (rgb[:, :, 1] == 255)
    return {"magenta": magenta, "white": white,
            "background": ~(magenta | white), "solid": magenta | white}


def component_sizes(mask: np.ndarray) -> np.ndarray:
    """Sizes of 4-connected components, wrapping across the tile edges."""
    lab = np.zeros((SIZE, SIZE), np.int32)
    nxt = 1
    for y, x in np.argwhere(mask):
        if lab[y, x]:
            continue
        stack = [(y, x)]
        lab[y, x] = nxt
        size = 0
        while stack:
            cy, cx = stack.pop()
            size += 1
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = (cy + dy) % SIZE, (cx + dx) % SIZE
                if mask[ny, nx] and not lab[ny, nx]:
                    lab[ny, nx] = nxt
                    stack.append((ny, nx))
        nxt += 1
    return np.bincount(lab.ravel())[1:]


CS_BINS = (2, 5, 9, 17, 33, 65, 129)


def measure(img: Image.Image) -> dict:
    """Spatial statistics of the three classes, comparable across images."""
    cls = classify(img)
    magenta, white, bg, solid = (cls["magenta"], cls["white"],
                                 cls["background"], cls["solid"])

    def autocorr(mask):
        w = mask.astype(float)
        w -= w.mean()
        f = np.fft.rfft2(w)
        c = np.fft.irfft2(f * np.conj(f))
        return c / c[0, 0]

    def dist_from_bg():
        d = np.full((SIZE, SIZE), -1, np.int16)
        frontier = ~solid
        n = 0
        while (d < 0).any() and n < 64:
            n += 1
            cand = _dilate(frontier) & solid & (d < 0)
            d[cand] = n
            frontier = cand
        return d

    def ring_hist(mask):
        """Histogram of how many of a pixel's 8 neighbours share its class."""
        n = np.zeros((SIZE, SIZE), np.int8)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy or dx:
                    n += np.roll(np.roll(mask, dy, axis=0), dx, axis=1)
        h = np.bincount(n[mask], minlength=9)
        return h / h.sum()

    rows = {"count_bg": int(bg.sum()), "count_white": int(white.sum()),
            "count_magenta": int(magenta.sum())}
    dsolid = dist_from_bg()
    for name, mask in (("magenta", magenta), ("white", white)):
        c = autocorr(mask)
        for lag in (1, 2, 4, 8):
            rows[f"ac_{name}_{lag}"] = round(float(c[0, lag]), 3)
        hist = np.bincount(dsolid[mask], minlength=5)
        rows[f"d1_{name}"] = round(float(hist[1] / hist.sum()), 3)
        rows[f"d2_{name}"] = round(float(hist[2] / hist.sum()), 3)
        rows[f"d3_{name}"] = round(float(hist[3:].sum() / hist.sum()), 3)
        ring = ring_hist(mask)
        for k in range(5):
            rows[f"ring{k}_{name}"] = round(float(ring[k]), 3)
        # Large-scale density modulation: spread of 16x16 block densities.
        blocks = mask.reshape(16, 16, 16, 16).mean(axis=(1, 3))
        rows[f"blk_{name}"] = round(float(blocks.std()), 4)
        rows[f"blkmax_{name}"] = round(float(blocks.max()), 3)
        # Component-size distribution.
        sizes = component_sizes(mask)
        rows[f"ncomp_{name}"] = int(len(sizes))
        rows[f"medcomp_{name}"] = round(float(np.median(sizes)), 1)
        ch = np.histogram(sizes, bins=[0] + list(CS_BINS) + [10 ** 9])[0]
        for k, v in enumerate(ch):
            rows[f"cs{k}_{name}"] = round(float(v / max(len(sizes), 1)), 3)
        rows[f"touch_bg_{name}"] = round(float((mask & _dilate(bg)).mean() / mask.mean()), 3)
    rows["touch_cross"] = round(float((magenta & _dilate(white)).mean() / magenta.mean()), 3)

    # Colour balance: within any neighbourhood neither colour may dominate.
    # ratio_k is the spread of the white share across k x k blocks, corr_k
    # whether the two colours occupy the same regions (+1) or opposite ones
    # (-1). The large blocks are the ones that expose "zoning".
    wf, mf = white.astype(np.float32), magenta.astype(np.float32)
    for k in (16, 32, 64):
        n = SIZE // k
        bw = wf.reshape(n, k, n, k).mean(axis=(1, 3)).ravel()
        bm = mf.reshape(n, k, n, k).mean(axis=(1, 3)).ravel()
        rows[f"ratio{k}"] = round(float((bw / (bw + bm + 1e-9)).std()), 3)
        rows[f"corr{k}"] = round(float(np.corrcoef(bw, bm)[0, 1]), 3)
    rows["mass_blk"] = round(float((wf + mf).reshape(16, 16, 16, 16)
                                   .mean(axis=(1, 3)).std()), 4)
    return rows


SKIP = {"count_bg", "count_white", "count_magenta"}


def score(got: dict, want: dict) -> float:
    """Scaled mean absolute difference over all compared metrics."""
    keys = [k for k in want if k not in SKIP and got.get(k) is not None]
    tot = 0.0
    for k in keys:
        r, g = float(want[k]), float(got[k])
        tot += abs(g - r) / (abs(r) if abs(r) > 1.0 else 1.0)
    return tot / len(keys)


def compare(generated: Image.Image, reference: Image.Image) -> tuple[str, float]:
    ref_cls, gen_cls = classify(reference), classify(generated)
    union = (ref_cls["magenta"] | gen_cls["magenta"]).sum()
    iou = float((ref_cls["magenta"] & gen_cls["magenta"]).sum() / union) if union else 0.0
    got, want = measure(generated), measure(reference)
    lines = [f"{'metric':<18}{'reference':>11}{'proto':>11}{'delta':>9}"]
    for k in want:
        if k in SKIP:
            continue
        lines.append(f"{k:<18}{want[k]:>11}{got[k]:>11}"
                     f"{float(got[k]) - float(want[k]):>+9.3f}")
    lines.append(f"{'iou_magenta':<18}{1.0:>11}{iou:>11.3f}")
    return "\n".join(lines), score(got, want)


def reference_image() -> Image.Image:
    here = Path(__file__).resolve().parent.parent
    return Image.open(here / "assets" / "textures" / "environment" / "clouds.png")


def _write(img: Image.Image, path: Path, seed: int) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    got = measure(img)
    print(f"wrote {path}  {img.size[0]}x{img.size[1]}  seed={seed}")
    print(f"  bg      {RGBA_BG} {got['count_bg']:6d}")
    print(f"  white   {RGBA_WHITE} {got['count_white']:6d}")
    print(f"  magenta {RGBA_MAGENTA} {got['count_magenta']:6d}")
    return got


def main() -> None:
    here = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser(description="Generate a clouds-like texture.")
    ap.add_argument("--out", type=Path,
                    default=here / "assets" / "textures" / "environment" / "proto.png")
    ap.add_argument("--seed", type=int, default=20261011)
    ap.add_argument("--stats", action="store_true",
                    help="print reference-vs-generated statistics")
    ap.add_argument("--batch", type=int, default=1, metavar="N",
                    help="write N variants, named <stem>_001..N, into --out-dir")
    ap.add_argument("--out-dir", type=Path, default=None,
                    help="destination directory for a batch (default: --out's dir)")
    args = ap.parse_args()

    if args.batch > 1:
        out_dir = args.out_dir or args.out.parent
        stem, suffix = args.out.stem, args.out.suffix or ".png"
        for i in range(1, args.batch + 1):
            seed = args.seed + i
            _write(render(seed), out_dir / f"{stem}_{i:03d}{suffix}", seed)
        return

    img = render(args.seed)
    _write(img, args.out, args.seed)
    if args.stats:
        table, err = compare(img, reference_image())
        print(table)
        print(f"scaled mean |delta| over compared metrics: {err:.4f}")


if __name__ == "__main__":
    main()
