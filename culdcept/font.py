"""
Culdcept Revolt bitmap font (inside a decompressed CULDCEPT.DAT entry).

Structure of the decompressed font resource
-------------------------------------------
  offset 0x30 (48):  CMAP -- an array of u16 LE character codes.  glyph_index i
                     maps to CMAP[i].  Codes are ASCII (0x20-0x7e), half-width
                     katakana (0xa1-0xdf) and Shift-JIS double-byte (0x8140+).
  size sections:     each begins with an 8-byte header
                         14 00 | bpg(u16 LE) | b4 | w | h | bpp
                     For the 4bpp text fonts b4 == 0xCE, bpp == 4 and the glyph
                     bitmaps start at  section + 0xCE.  Glyph i is a fixed
                     w x h, 4-bit-alpha (A4) cell of `bpg` bytes
                     (bpg == ceil(w/2)*h), MSB nibble first, at
                         section + 0xCE + i * bpg
                     The game ships 10 px, 12 px and 14 px text sizes.

Only the 4bpp text sections are handled (that is what on-screen text uses).  A
12x12 16bpp "outline" section also exists but is not needed here.
"""
import struct

GLYPH_DATA_OFFSET = 0xCE     # glyph bitmaps start this far into a 4bpp section


def parse_cmap(font: bytes):
    """Return {char_code: glyph_index} parsed from the CMAP at offset 0x30."""
    cmap = {}
    p = 0x30
    i = 0
    while p + 2 <= len(font):
        v = font[p] | (font[p + 1] << 8)
        ok = (0x20 <= v <= 0x7e) or (0xa1 <= v <= 0xdf) or (0x8140 <= v <= 0xfcff)
        if not ok:
            break
        cmap.setdefault(v, i)
        i += 1
        p += 2
    return cmap


def find_sections(font: bytes):
    """Return [(section_offset, bpg, w, h)] for every 4bpp text size section."""
    out = []
    p = 0
    n = len(font)
    while p < n - 8:
        if font[p] == 0x14 and font[p + 1] == 0x00:
            bpg = struct.unpack_from("<H", font, p + 2)[0]
            b4 = font[p + 4]; w = font[p + 5]; h = font[p + 6]; bpp = font[p + 7]
            if bpp == 4 and b4 == 0xCE and 6 <= w <= 40 and w == h \
                    and bpg == ((w + 1) // 2) * h:
                out.append((p, bpg, w, h))
        p += 2
    return out


def sjis_code(ch: str):
    """Shift-JIS code (int) for a single character, or None."""
    try:
        b = ch.encode("shift_jis")
    except UnicodeEncodeError:
        return None
    return int.from_bytes(b, "big")


def render_a4(pil_image, w, h) -> bytes:
    """Pack a w x h grayscale PIL image into A4 (4bpp, MSB nibble first)."""
    a = pil_image.load()
    bpr = (w + 1) // 2
    out = bytearray(bpr * h)
    for y in range(h):
        for x in range(w):
            v = a[x, y] >> 4                       # 8bpp -> 4bpp
            bi = y * bpr + x // 2
            if x % 2 == 0:
                out[bi] = (out[bi] & 0x0F) | (v << 4)
            else:
                out[bi] = (out[bi] & 0xF0) | v
    return bytes(out)


def write_glyph(font: bytearray, section_off, bpg, glyph_index, glyph_bytes):
    off = section_off + GLYPH_DATA_OFFSET + glyph_index * bpg
    font[off:off + bpg] = glyph_bytes
