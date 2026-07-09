# Culdcept Revolt (3DS) — CULDCEPT.DAT tools & Korean-font demo

Reverse-engineering tools for **Culdcept Revolt** (カルドセプト リボルト, Nintendo 3DS,
title ID `00040000000F5700`) and a proof-of-concept that renders **Korean (Hangul)**
in the game's own bitmap font.

The whole point of this repo is to open up `CULDCEPT.DAT` — the game's monolithic
archive whose custom compression has no public tools — so the text and font can be
edited toward a full Korean translation.

## ⚠️ Read this first

- **No game data is included.** No ROM, no `CULDCEPT.DAT`, no executable. You must
  own the game and supply your own files. The tools operate on *your* copy.
- **This is a proof of concept, not a translation.** The demo only swaps each *kana
  glyph* for a phonetic Hangul syllable (e.g. `の → 노`, `カ → 카`) so you can confirm
  Korean renders in-game at every font size. It does **not** translate any text yet.
- For research / personal use. Respect the game's copyright.

## What was reverse-engineered

- **`CULDCEPT.DAT` container** — a table of `(u32 offset, u32 size)` records followed
  by the entry data; entry count = `first_offset / 8`.
- **The codec.** Entries are compressed with two custom schemes chosen by a type byte:
  - `0x08` / `0x0c` — a DEFLATE-flavoured **canonical Huffman + LZ** (the text/font path);
    decompressor **and** compressor are implemented here in pure Python.
  - `0x0d` / `0x8d` — a custom-framed **LZMA range coder** (not needed for the font).
- **The bitmap font** (resource `e1054`): a CMAP (glyph index → Shift-JIS / ASCII code)
  plus several fixed-cell **A4 (4-bit alpha)** size sections (10 px, 12 px, 14 px), each
  a `w×h` cell of `ceil(w/2)*h` bytes at `section + 0xCE + index*bpg`.

See [`docs/FORMAT.md`](docs/FORMAT.md) for the full description.

## Usage

Requirements: Python 3, [Pillow](https://pypi.org/project/Pillow/), and a Korean TTF
(Windows `malgun.ttf` / Malgun Gothic, or NanumGothic).

```bash
pip install pillow
python apply_korean_font.py path/to/CULDCEPT.DAT out/CULDCEPT.DAT --font malgun.ttf
```

Then load the patched file with **Azahar / Lime3DS / Citra LayeredFS**:

```
<emulator user dir>/load/mods/00040000000F5700/romfs/CULDCEPT.DAT
```

(confirmed working — the log prints `LayeredFS replacement file in use for /CULDCEPT.DAT`),
or rebuild your ROM/CIA with the patched `CULDCEPT.DAT` in its RomFS.

A ready-made **delta patch** (bsdiff4) of the demo is attached to the
[Releases](../../releases) page for convenience — apply it to your own
`CULDCEPT.DAT` with `python apply_patch.py`.

## Library

```python
from culdcept import huffman, dat, font
d = dat.Dat(open("CULDCEPT.DAT", "rb").read())
raw = huffman.decompress(d.entry(1054))     # -> decompressed font resource
entry = huffman.compress(raw, typ=0x0c)     # -> a valid entry the game decodes
```

## Credits

Format reverse-engineered from scratch (container, codec, font). Tools are original
work and MIT-licensed (see `LICENSE`). Culdcept Revolt is © Omiya Soft / Nintendo.
