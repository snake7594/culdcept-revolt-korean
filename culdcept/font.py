"""
컬드셉트 리볼트 비트맵 폰트 (압축 해제된 CULDCEPT.DAT 엔트리 내부).

압축 해제된 폰트 리소스의 구조
-----------------------------
  오프셋 0x30 (48):  CMAP -- u16 LE 문자 코드 배열. glyph_index i는 CMAP[i]에
                     대응. 코드는 ASCII(0x20-0x7e), 반각 카타카나(0xa1-0xdf),
                     Shift-JIS 더블바이트(0x8140+).
  크기 섹션:         각각 8바이트 헤더로 시작
                         14 00 | bpg(u16 LE) | b4 | w | h | bpp
                     4bpp 텍스트 폰트는 b4 == 0xCE, bpp == 4이고 글리프 비트맵은
                     section + 0xCE에서 시작. 글리프 i는 고정 w x h, 4비트 알파
                     (A4) 셀로 `bpg` 바이트(bpg == ceil(w/2)*h), 상위 니블 우선,
                     위치는
                         section + 0xCE + i * bpg
                     게임은 10px, 12px, 14px 텍스트 크기를 탑재합니다.

4bpp 텍스트 섹션만 다룹니다(화면 텍스트가 이걸 씀). 12x12 16bpp "아웃라인"
섹션도 있으나 여기서는 필요 없습니다.
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


def find_all_sections(font: bytes):
    """Return [(section_offset, bpg, w, h, bpp)] for every glyph section.

    엔트리 1054 에는 4bpp(안티에일리어스, 대사·카드 패널용) 섹션 3개(10/12/14px)와
    1bpp(크리스프, 소형 UI/HUD·스톡정보·카드상세 헤더용) 섹션 2개(10/12px)가 있습니다.
    소형 UI 는 1bpp 로 렌더되므로 이 섹션도 함께 한글로 그려야 합니다.
    """
    out = []
    p = 0
    n = len(font)
    while p < n - 8:
        if font[p] == 0x14 and font[p + 1] == 0x00:
            bpg = struct.unpack_from("<H", font, p + 2)[0]
            b4 = font[p + 4]; w = font[p + 5]; h = font[p + 6]; bpp = font[p + 7]
            if b4 == 0xCE and 6 <= w <= 40 and w == h:
                if bpp == 4 and bpg == ((w + 1) // 2) * h:
                    out.append((p, bpg, w, h, 4))
                elif bpp == 1 and bpg == (w * h + 7) // 8:
                    out.append((p, bpg, w, h, 1))
        p += 2
    return out


def render_1bpp(pil_image, w, h, threshold=110) -> bytes:
    """Pack a w x h grayscale PIL image into 1bpp (MSB-first packed bitstream).

    1bpp 글리프는 행우선 w*h 비트를 바이트 패딩 없이 연속 패킹(비트당 픽셀,
    MSB 우선)하며 bpg == ceil(w*h/8) 바이트입니다. 안티에일리어스 렌더를
    threshold 로 이진화합니다.
    """
    a = pil_image.load()
    total = w * h
    out = bytearray((total + 7) // 8)
    bit = 0
    for y in range(h):
        for x in range(w):
            if a[x, y] >= threshold:
                out[bit >> 3] |= 0x80 >> (bit & 7)
            bit += 1
    return bytes(out)


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
