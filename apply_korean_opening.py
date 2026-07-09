#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
컬드셉트 리볼트(3DS, 일본판)의 오프닝(스테이지1)을 한국어로 패치한다.

본인의 CULDCEPT.DAT에서 (1) 비트맵 폰트, (2) 오프닝 시나리오 스크립트,
(3) UI/HUD 텍스트를 찾아, 필요한 한글 음절 글리프를 폰트에 그려 넣고 대사와
UI 라벨을 한국어로 교체한 뒤 패치된 CULDCEPT.DAT를 씁니다.

이 툴은 게임 데이터를 포함하지 않습니다 — 한글 글리프는 시스템 폰트에서
그려지고, 원문 바이트는 전부 본인의 파일에서 읽어옵니다.

사용법:
    python apply_korean_opening.py <원본 CULDCEPT.DAT> <출력 CULDCEPT.DAT> [--font malgun.ttf]

그 다음 결과물을 Azahar/Lime3DS LayeredFS로 사용:
    load/mods/00040000000F5700/romfs/CULDCEPT.DAT

필요: 파이썬 3, Pillow, 한글 TTF(예: 윈도우 malgun.ttf(맑은 고딕)).
"""
import argparse
import os
import struct
import sys

from PIL import Image, ImageDraw, ImageFont

from culdcept import dat as datmod, huffman, font as fontmod, scen, wansung
from opening_ko import EVENTS_KO, ORIG_PAGES, UI_KO

# 릴리즈 패치는 '나눔스퀘어 네오 Bold'로 렌더링합니다. 그 폰트를 fonts/ 폴더에
# NanumSquareNeo-cBd.ttf 로 두면(fonts/README.md 참고) 릴리즈와 동일하게 나옵니다.
# 없으면 시스템 한글 폰트(맑은 고딕 등)로 대체합니다.
_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_FONTS = [
    os.path.join(_HERE, "fonts", "NanumSquareNeo-cBd.ttf"),
    r"C:\Windows\Fonts\malgun.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
]


def pick_font(explicit):
    if explicit:
        return explicit
    for p in DEFAULT_FONTS:
        if os.path.exists(p):
            return p
    return None


# ---------------------------------------------------------------- detection ---
def find_font_and_ui(d):
    """0x08/0x0c 엔트리를 한 번씩만 해제하며 폰트와 UI 엔트리를 동시에 탐지."""
    labels = [jp.encode("shift_jis") for jp in UI_KO]
    font_best = None
    ui_best = None
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
            if font_best is None or len(blob) > font_best[0]:
                font_best = (len(blob), i, blob, cmap, secs)
        score = 0
        for nb in labels:
            p = blob.find(nb)
            while p >= 0:
                if (p == 0 or blob[p - 1] == 0) and \
                   (p + len(nb) >= len(blob) or blob[p + len(nb)] == 0):
                    score += 1
                    break
                p = blob.find(nb, p + 1)
        if score >= 3 and (ui_best is None or score > ui_best[0]):
            ui_best = (score, i, blob)
    if font_best is None:
        raise SystemExit("폰트 리소스를 찾지 못했습니다")
    if ui_best is None:
        raise SystemExit("UI 텍스트 엔트리를 찾지 못했습니다")
    return (font_best[1], font_best[2], font_best[3], font_best[4]), (ui_best[1], ui_best[2])


def find_opening(d):
    """오프닝 대사 섹션을 (entry_index, sec_index, section_dec, text_start) 로 반환.

    시나리오 컨테이너 중 어떤 섹션이 정확히 25개 이벤트를 갖고 각 이벤트의
    페이지 수가 ORIG_PAGES와 일치하는 것을 찾는다.
    """
    want = ORIG_PAGES
    n = len(want)
    for i in range(d.count):
        ent = d.entry(i)
        secs = scen.parse_sections(ent)
        if not secs:
            continue
        for k, (off, ln) in enumerate(secs):
            if not ln or ent[off] not in (0x08, 0x0c):
                continue
            try:
                dec = huffman.decompress(ent[off:off + ln])
            except Exception:
                continue
            ts = scen.text_start_for(dec, n)
            if ts is None:
                continue
            if ts and dec[ts - 1] != 0x00:      # 텍스트 직전은 null이어야 함(전제 위반 스킵)
                continue
            evs = scen.split_events(dec[ts:])
            if len(evs) != n:
                continue
            pages = {j: evs[j].count(b"\x07") + 1 for j in range(n)}
            if pages != want:
                continue
            if all(scen._looks_text(e) or e == b"" for e in evs):
                return i, k, dec, ts
    raise SystemExit("오프닝 시나리오 섹션을 찾지 못했습니다(게임 버전이 다를 수 있음)")


# ------------------------------------------------------------------ glyphs ----
def make_renderer(ttf_path):
    cache = {}

    def render(ch, w, h):
        px = cache.get(h)
        if px is None:
            px = ImageFont.truetype(ttf_path, h)
            cache[h] = px
        img = Image.new("L", (w, h), 0)
        dr = ImageDraw.Draw(img)
        bb = dr.textbbox((0, 0), ch, font=px)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        dr.text(((w - tw) // 2 - bb[0], (h - th) // 2 - bb[1]), ch, fill=255, font=px)
        return fontmod.render_a4(img, w, h)

    return render


# -------------------------------------------------------------------- main ----
def main():
    ap = argparse.ArgumentParser(description="컬드셉트 리볼트 오프닝 한국어 패치")
    ap.add_argument("infile")
    ap.add_argument("outfile")
    ap.add_argument("--font", default=None, help="한글 TTF/TTC 경로")
    args = ap.parse_args()

    ttf = pick_font(args.font)
    if not ttf or not os.path.exists(ttf):
        sys.exit("한글 폰트를 찾지 못했습니다. --font <malgun.ttf 경로> 로 지정하세요")

    d = datmod.Dat(open(args.infile, "rb").read())

    (font_idx, fontbuf, cmap, sections), (ui_idx, ui_blob) = find_font_and_ui(d)
    fontbuf = bytearray(fontbuf)
    open_idx, sec_idx, sec_dec, text_start = find_opening(d)
    if len({font_idx, open_idx, ui_idx}) != 3:
        sys.exit("탐지 오류: 폰트/오프닝/UI 엔트리가 서로 겹칩니다(%d/%d/%d)"
                 % (font_idx, open_idx, ui_idx))
    print("폰트 엔트리 %d, 오프닝 엔트리 %d(섹션 %d), UI 엔트리 %d"
          % (font_idx, open_idx, sec_idx, ui_idx))

    # 페이지 수 검증
    for i in range(25):
        assert wansung.page_count(EVENTS_KO[i]) == ORIG_PAGES[i], \
            "이벤트 %d 페이지 수 불일치(번역 데이터 오류)" % i

    # 매핑: 대사 + UI 음절 전부
    sylls = wansung.collect_syllables(*EVENTS_KO.values(), *UI_KO.values())
    syll2code = wansung.build_map(sylls, cmap)
    print("한글 음절 %d개 -> 한자 슬롯 배정" % len(syll2code))

    # 폰트 글리프 주입(모든 4bpp 크기)
    render = make_renderer(ttf)
    for (soff, bpg, w, h) in sections:
        for s, code in syll2code.items():
            fontmod.write_glyph(fontbuf, soff, bpg, cmap[code], render(s, w, h))
    new_font = huffman.compress(bytes(fontbuf), typ=d.entry_type(font_idx))
    assert huffman.decompress(new_font) == bytes(fontbuf), "폰트 재압축 왕복 실패"

    # 대사 교체 (★페이지 단위 길이 보존: 게임이 절대 오프셋으로 참조하므로 필수)
    orig_secs = scen.parse_sections(d.entry(open_idx))
    sec_type = d.entry(open_idx)[orig_secs[sec_idx][0]]
    ko_events = [EVENTS_KO[i] for i in range(len(EVENTS_KO))]
    new_sec_dec = scen.rebuild_section_fit(
        sec_dec, text_start, ko_events,
        lambda page: wansung.encode(page, syll2code))
    assert len(new_sec_dec) == len(sec_dec), "길이 보존 실패"
    new_sec = huffman.compress(new_sec_dec, typ=sec_type)
    assert huffman.decompress(new_sec) == new_sec_dec, "대사 섹션 왕복 실패"
    new_container = scen.rebuild_container(d.entry(open_idx), sec_idx, new_sec)

    # UI 제자리 교체(원문 길이 이하, null 유지)
    ui = bytearray(ui_blob)
    n_ui = 0
    missing = []
    for jp, ko in UI_KO.items():
        nb = jp.encode("shift_jis")
        ko_bytes = b"".join(wansung.encode_char(c, syll2code) for c in ko)
        if len(ko_bytes) > len(nb):
            sys.exit("UI '%s'->'%s' 가 원문보다 깁니다" % (jp, ko))
        hit = 0
        p = 0
        while True:
            i = ui.find(nb, p)
            if i < 0:
                break
            before = i == 0 or ui[i - 1] == 0
            after = i + len(nb) >= len(ui) or ui[i + len(nb)] == 0
            if before and after:
                ui[i:i + len(nb)] = ko_bytes + b"\x00" * (len(nb) - len(ko_bytes))
                n_ui += 1
                hit += 1
            p = i + 1
        if hit == 0:
            missing.append(jp)
    assert len(ui) == len(ui_blob), "UI 길이 변경됨(버그)"
    if missing:
        print("경고: 이 판본에서 찾지 못해 미교체된 UI 라벨: " + ", ".join(missing))
    new_ui = huffman.compress(bytes(ui), typ=d.entry_type(ui_idx))
    assert huffman.decompress(new_ui) == bytes(ui), "UI 재압축 왕복 실패"

    d.replace_entry(font_idx, new_font)
    d.replace_entry(open_idx, new_container)
    d.replace_entry(ui_idx, new_ui)
    open(args.outfile, "wb").write(d.build())
    print("대사 25개 이벤트, UI %d개 라벨 교체 완료" % n_ui)
    print("완료: %s" % args.outfile)


if __name__ == "__main__":
    main()
