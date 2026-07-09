# CULDCEPT.DAT format (Culdcept Revolt, 3DS)

Everything below was reverse-engineered from the game; no official docs.
Offsets/handler addresses refer to the decompressed ARM executable (ExeFS `.code`,
which is BLZ-compressed on disk).

## 1. Archive container

```
offset 0:  record table -- N entries of 8 bytes each:
             u32 LE  offset      (into the file)
             u32 LE  size        (bytes of this entry)
           N = table[0].offset / 8   (data starts right after the table)
entry i:   DAT[offset : offset+size]
```

Entry byte 0 is the codec type. Observed types: `0x08`, `0x0c`, `0x0d`, `0x8d`
(compressed); `0x00` (raw / nested container using 24-bit big-endian offset
tables); `0x05` (raw CWAV audio).

To resize an entry, append the new bytes at the end of the file and rewrite that
one 8-byte record — every other entry keeps its offset.

## 2. Codec dispatch

A single dispatcher (guest `0x27f3f4`) reads the type byte and selects a handler
from a table (`0x39bb58`, indexed `type & 0x3f`) plus a post-processor
(`0x39bb90`, indexed `type >> 6`):

| type | handler | scheme |
|------|---------|--------|
| 0x08 | 0x274b90 | canonical Huffman + LZ (window 0x0d) |
| 0x0c | 0x274b88 | canonical Huffman + LZ (window 0x10) |
| 0x0d | 0x275080 | LZMA-family range coder |
| 0x8d | 0x275080 | same range coder, different post-processor |

## 3. Type 0x08 / 0x0c — Huffman + LZ (implemented in `culdcept/huffman.py`)

```
entry = [type u8] [varint size] [bitstream]
```

- **size** is a continuation-bit **varint** (handler `0x2747f8`), NOT `size>>8`.
  Note the archive record’s size field and this varint are read from overlapping
  bytes; the varint is the true decompressed length.
- **Bit reader** (`0x275020/0x275028`): MSB-first over a 32-bit accumulator; refill
  reads a little-endian `u16` and byte-reverses it into the top of the accumulator.
  After the varint, if `pos` is odd one byte is pre-loaded, then `consume(16)` primes.
  Net effect: a plain MSB-first bit stream over the entry bytes from `pos`.
- **Blocks** repeat until `size` bytes are produced:
  - `r8 = getbits(16)` — number of symbols in the block.
  - **litlen** table (`0x274d18`): a 19-symbol code-length (CL) table read by
    `read_lengths_direct(19, 5, special_pos=3)`, then `count = getbits(9)` code
    lengths RLE-coded through CL (`s>2 → len s-2`, `s==0 → 0`, `s==1 → 3+getbits(4)`
    zeros, `s==2 → 0x14+getbits(9)` zeros).
  - **dist** table: `read_lengths_direct(window+1, (window+1-10)&5, -1)`.
  - `r8` symbols: `sym<0x100` literal; else `length=sym-0xFD`, distance code
    `dsym → dd = (dsym==0?1:(1<<(dsym-1))+1+getbits(dsym-1))`, copy match.
- **`read_lengths_direct(nsym,nbits,special)`**: `count=getbits(nbits)`; if 0 →
  single symbol `= getbits(nbits)`. Else per length: top 3 bits `t`; `t<7 → len t`
  (consume 3) else `len = 7 + clz32(~(acc<<3))` (consume len-3). At `i==special`,
  `r=getbits(2)`; if `r`, skip `r` zeros.

A minimal valid encoder emits, per block: `r8`, a degenerate CL table (single
symbol 10 → 0 bits), `count=256` (yielding a 256-entry all-length-8 litlen table,
so literal byte B is the raw 8-bit value B), a degenerate dist table, then the raw
literal bytes. See `compress()`.

## 4. Bitmap font (decompressed resource, `culdcept/font.py`)

```
offset 0x30: CMAP -- u16 LE character codes; glyph_index i -> CMAP[i].
             ASCII 0x20-0x7e, half-width 0xa1-0xdf, Shift-JIS 0x8140+, gaiji 0xf9xx.
size section header (8 bytes): 14 00 | bpg(u16) | b4 | w | h | bpp
```

For the 4bpp text sizes (`bpp==4`, `b4==0xCE`), glyph bitmaps start at
`section + 0xCE`; glyph `i` is a fixed `w×h` **A4** (4-bit alpha, MSB nibble first)
cell of `bpg = ceil(w/2)*h` bytes at `section + 0xCE + i*bpg`.
Sizes shipped: **10 px** (bpg 50), **12 px** (bpg 72), **14 px** (bpg 98).
A 12×12 16bpp "outline" section (`b4==0x10`, `bpg 288`) also exists; it holds only
~160 glyphs (no kanji) and is not used for body text.

The game renders text by converting Shift-JIS → glyph index via the CMAP, blitting
glyphs into A4 textures. Rendering pipeline verified in-game via Azahar LayeredFS.
