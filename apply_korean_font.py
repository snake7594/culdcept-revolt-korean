#!/usr/bin/env python3
"""
본인의 CULDCEPT.DAT(컬드셉트 리볼트, 3DS)에 한글 폰트 데모를 적용한다.

본인의 CULDCEPT.DAT에서 폰트 리소스를 읽어, 모든 비트맵 크기의 각 가나 글리프를
한글 TTF로 렌더링한 발음 한글 글리프로 교체하고, 다시 압축해서 패치된 CULDCEPT.DAT를
씁니다. 이 툴은 게임 데이터를 포함하지 않습니다 -- 글리프는 시스템 폰트에서 그려지고
바이트는 본인의 파일에서 옵니다.

사용법:
    python apply_korean_font.py <원본 CULDCEPT.DAT> <출력 CULDCEPT.DAT> [--font malgun.ttf]

그 다음 결과물을 Azahar/Lime3DS LayeredFS로 사용:
    load/mods/00040000000F5700/romfs/CULDCEPT.DAT
또는 이것으로 ROM/CIA를 재빌드하세요.

필요: 파이썬 3, Pillow. 한글 TTF(예: 윈도우 "malgun.ttf"(맑은 고딕) 또는 나눔고딕)가
있어야 합니다.
"""
import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFont

from culdcept import huffman, dat, font as fontmod, kana_map

DEFAULT_FONTS = [
    r"C:\Windows\Fonts\malgun.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
]


def pick_font():
    for p in DEFAULT_FONTS:
        if os.path.exists(p):
            return p
    return None


def find_font_entry(d: dat.Dat):
    """Return (index, decompressed_bytes) of the main bitmap-font resource."""
    best = None
    for i in range(d.count):
        if d.entry_type(i) not in (0x08, 0x0c):
            continue
        try:
            blob = huffman.decompress(d.entry(i))
        except Exception:
            continue
        cmap = fontmod.parse_cmap(blob)
        secs = fontmod.find_sections(blob)
        if len(cmap) > 1000 and len(secs) >= 2:
            score = len(blob)
            if best is None or score > best[0]:
                best = (score, i, blob)
    if best is None:
        raise SystemExit("could not locate the font resource in this CULDCEPT.DAT")
    return best[1], best[2]


def hangul_glyph(ch, w, h, ttf_cache, ttf_path):
    px = ttf_cache.get(h)
    if px is None:
        px = ImageFont.truetype(ttf_path, h)     # pixel size == cell height
        ttf_cache[h] = px
    img = Image.new("L", (w, h), 0)
    dr = ImageDraw.Draw(img)
    bb = dr.textbbox((0, 0), ch, font=px)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    dr.text(((w - tw) // 2 - bb[0], (h - th) // 2 - bb[1]), ch, fill=255, font=px)
    return fontmod.render_a4(img, w, h)


def main():
    ap = argparse.ArgumentParser(description="Apply the Korean-font demo to CULDCEPT.DAT")
    ap.add_argument("infile")
    ap.add_argument("outfile")
    ap.add_argument("--font", default=None, help="path to a Korean TTF/TTC")
    args = ap.parse_args()

    ttf = args.font or pick_font()
    if not ttf or not os.path.exists(ttf):
        sys.exit("no Korean font found; pass one with --font <path-to-ttf>")

    d = dat.Dat(open(args.infile, "rb").read())
    idx, blob = find_font_entry(d)
    blob = bytearray(blob)
    print(f"font resource: entry {idx}, {len(blob)} bytes decompressed")

    cmap = fontmod.parse_cmap(blob)
    sections = fontmod.find_sections(blob)
    kmap = kana_map.build()
    cache = {}
    total = 0
    for (soff, bpg, w, h) in sections:
        n = 0
        for code, kr in kmap.items():
            gi = cmap.get(code)
            if gi is None:
                continue
            fontmod.write_glyph(blob, soff, bpg, gi, hangul_glyph(kr, w, h, cache, ttf))
            n += 1
        print(f"  {w}x{h} section @0x{soff:x}: replaced {n} kana glyphs")
        total += n

    new_entry = huffman.compress(bytes(blob), typ=d.entry_type(idx))
    if huffman.decompress(new_entry) != bytes(blob):
        sys.exit("internal error: re-compression round-trip failed")

    d.replace_entry(idx, new_entry)
    open(args.outfile, "wb").write(d.build())
    print(f"replaced {total} glyphs across {len(sections)} sizes")
    print(f"wrote {args.outfile}")


if __name__ == "__main__":
    main()
