#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
컬드셉트 리볼트(3DS, 일판) **전체 스토리 대사 + 카드 데이터베이스 + UI** 한국어 패치.

본인의 CULDCEPT.DAT 에서 시나리오 컨테이너(엔트리 1946~1958)의 모든 대사와,
카드 데이터베이스(엔트리 1190: 카드 능력·설명·플레이버 및 UI/시작설정 텍스트)를
찾아 한국어로 교체하고, 필요한 한글 글리프를 폰트(엔트리 1054)에 그려 넣어
패치된 CULDCEPT.DAT 를 씁니다.

게임은 대사 페이지를 텍스트 영역 내 절대 오프셋으로 참조하므로, 각 대화창의
한국어는 원문 페이지의 바이트 길이 이하로 넣고 부족분은 공백으로 채워 모든
오프셋을 보존합니다. 카드 텍스트(1190)도 포인터로 참조되므로 원문 문자열 길이
이하로 제자리 교체합니다(dialogue_ko.json / cards_ko.json 의 번역은 이 한도에
맞춰져 있습니다).

이 툴은 게임 데이터를 포함하지 않습니다 — 한글 글리프는 폰트에서 그려지고,
원문 바이트(아이콘·제어코드 포함)는 전부 본인의 파일에서 읽습니다.
dialogue_ko.json / cards_ko.json 은 한국어 번역만 담습니다(일본어 원문 없음).

사용법:
    python apply_korean_full.py <원본 CULDCEPT.DAT> <출력 CULDCEPT.DAT> [--font TTF]
"""
import argparse
import json
import os
import struct
import sys

from PIL import Image, ImageDraw, ImageFont

from culdcept import dat as datmod, huffman, font as fontmod, scen, wansung, cardtext
from opening_ko import UI_KO, SETUP_KO

FONT_ENTRY, UI_ENTRY = 1054, 1190
CONTAINERS = list(range(1946, 1959))
PAD = 0x20
_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_FONTS = [
    os.path.join(_HERE, "fonts", "NanumSquareNeo-cBd.ttf"),
    r"C:\Windows\Fonts\malgun.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
]
_FW = {'!': '！', '?': '？'}


def is_h(c): return 0xAC00 <= ord(c) <= 0xD7A3


def pick_font(explicit):
    if explicit:
        return explicit
    for p in DEFAULT_FONTS:
        if os.path.exists(p):
            return p
    return None


def main():
    ap = argparse.ArgumentParser(description="컬드셉트 리볼트 전체 대사 한국어 패치")
    ap.add_argument("infile")
    ap.add_argument("outfile")
    ap.add_argument("--font", default=None)
    args = ap.parse_args()

    ttf = pick_font(args.font)
    if not ttf or not os.path.exists(ttf):
        sys.exit("한글 폰트를 찾지 못했습니다. --font <TTF 경로> 로 지정하세요")

    ko = json.load(open(os.path.join(_HERE, "dialogue_ko.json"), encoding="utf-8"))
    cards_path = os.path.join(_HERE, "cards_ko.json")
    cards_ko = json.load(open(cards_path, encoding="utf-8")) if os.path.exists(cards_path) else {}
    block_path = os.path.join(_HERE, "block_ko.json")
    block_ko = json.load(open(block_path, encoding="utf-8")) if os.path.exists(block_path) else {}
    d = datmod.Dat(open(args.infile, "rb").read())
    cmap = fontmod.parse_cmap(huffman.decompress(d.entry(FONT_ENTRY)))

    # 폰트: 완성형 2350 + 번역/카드/블록대사/UI/설정에 쓰인 2350 밖 음절
    used = {c for ev in ko.values() for pages in ev.values() for p in pages for c in p if is_h(c)}
    used |= {c for t in list(UI_KO.values()) + list(SETUP_KO.values()) for c in t if is_h(c)}
    used |= {c for v in cards_ko.values() for c in v if is_h(c)}
    used |= {c for evs in block_ko.values() for pages in evs.values() for p in pages for c in p if is_h(c)}
    extra = [c for c in sorted(used) if c not in set(wansung.WANSUNG_2350)]
    syll2code = wansung.build_fixed_map(cmap, extra=extra)
    print("한글 %d자(완성형 2350%s) 폰트 주입" % (len(syll2code), (" + %d" % len(extra)) if extra else ""))

    def encp(text):
        out = bytearray(); i = 0
        while i < len(text):
            if text[i] == "\n": out.append(0x0a); i += 1
            elif text[i:i+3] == "{N}": out += bytes([0x03, 0x30, 0x2f]); i += 3
            else:
                out += wansung.encode_char(text[i], syll2code); i += 1
        return bytes(out)

    def trunc(bs, limit):
        if len(bs) <= limit: return bs
        out = bytearray(); i = 0
        while i < len(bs):
            step = 3 if bs[i] == 0x03 else (2 if 0x81 <= bs[i] <= 0xfc and i+1 < len(bs) else 1)
            if len(out)+step > limit: break
            out += bs[i:i+step]; i += step
        return bytes(out)

    def fit_page(view, tokens, budget):
        """예산 초과 시: 끝쪽 공백부터 제거 → 그래도 넘으면 안전 절단(문자경계 보존)."""
        enc = cardtext.encode(view, tokens, syll2code)
        if len(enc) <= budget:
            return enc
        s = list(view)
        while len(cardtext.encode("".join(s), tokens, syll2code)) > budget:
            pos = -1
            for j in range(len(s) - 1, -1, -1):
                if s[j] == " ": pos = j; break
            if pos < 0: break
            del s[pos]
        enc = cardtext.encode("".join(s), tokens, syll2code)
        return enc if len(enc) <= budget else trunc(enc, budget)

    # 폰트 주입
    fontbuf = bytearray(huffman.decompress(d.entry(FONT_ENTRY)))
    sizes = fontmod.find_sections(fontbuf)
    cache = {}
    for (soff, bpg, w, h) in sizes:
        for s, code in syll2code.items():
            px = cache.get(h) or ImageFont.truetype(ttf, h); cache[h] = px
            img = Image.new("L", (w, h), 0); dr = ImageDraw.Draw(img)
            bb = dr.textbbox((0, 0), s, font=px); tw, th = bb[2]-bb[0], bb[3]-bb[1]
            dr.text(((w-tw)//2-bb[0], (h-th)//2-bb[1]), s, fill=255, font=px)
            fontmod.write_glyph(fontbuf, soff, bpg, cmap[code], fontmod.render_a4(img, w, h))
    new_font = huffman.compress(bytes(fontbuf), typ=d.entry_type(FONT_ENTRY))
    assert huffman.decompress(new_font) == bytes(fontbuf)

    # 대사 주입(컨테이너 1946~1958, 페이지 길이보존)
    n_ev = 0
    for idx in CONTAINERS:
        ent = d.entry(idx)
        secs = scen.parse_sections(ent)
        if not secs:
            continue
        cont = ent
        for k, (off, ln) in enumerate(secs):
            if not ln or ent[off] not in (0x08, 0x0c):
                continue
            try:
                dec = huffman.decompress(ent[off:off+ln])
            except Exception:
                continue
            ts, events = scen.find_text_region(dec)
            if ts is None:
                continue
            evmap = ko.get(f"e{idx}_s{k}", {})
            region = bytearray()
            for ei, ev in enumerate(events):
                opages = ev.split(b"\x07")
                kp = evmap.get(str(ei))
                for pi, opage in enumerate(opages):
                    if kp is not None and pi < len(kp) and kp[pi] != "":
                        enc = encp(kp[pi])
                        if len(enc) > len(opage):
                            enc = trunc(enc, len(opage))
                        region += enc + bytes([PAD]) * (len(opage) - len(enc))
                    else:
                        region += opage
                    if pi < len(opages) - 1:
                        region += b"\x07"
                region += b"\x00"
                n_ev += 1
            if len(region) != len(dec) - ts:
                continue                      # 길이 불일치 섹션은 건너뜀(안전)
            new_dec = dec[:ts] + bytes(region)
            new_sec = huffman.compress(new_dec, typ=ent[off])
            assert huffman.decompress(new_sec) == new_dec
            cont = scen.rebuild_container(cont, k, new_sec)
        d.replace_entry(idx, cont)

    # 카드 데이터베이스 + UI + 시작설정(엔트리 1190)
    ui = bytearray(huffman.decompress(d.entry(UI_ENTRY)))
    # 카드 텍스트: 본인 파일에서 문자열을 열거·중복제거한 순서(=인덱스)로 제자리 교체
    n_card = 0
    if cards_ko:
        uniq = cardtext.enum_unique(ui)
        for idx, (raw, offs) in enumerate(uniq.items()):
            view = cards_ko.get(str(idx))
            if view is None:
                continue
            _, tokens = cardtext.tokenize(raw)
            enc = cardtext.encode(view, tokens, syll2code)
            if len(enc) > len(raw):
                enc = trunc(enc, len(raw))
            body = enc + bytes([PAD]) * (len(raw) - len(enc))
            for off in offs:
                ui[off:off+len(raw)] = body
                n_card += 1
    def kob(t): return b"".join(wansung.encode_char(c, syll2code) for c in t)
    for jp, k in UI_KO.items():
        nb = jp.encode("shift_jis"); kb = kob(k); p = 0
        while True:
            i = ui.find(nb, p)
            if i < 0: break
            if (i == 0 or ui[i-1] == 0) and (i+len(nb) >= len(ui) or ui[i+len(nb)] == 0):
                ui[i:i+len(nb)] = kb + b"\x00"*(len(nb)-len(kb))
            p = i + 1
    for jp, k in SETUP_KO.items():
        nb = jp.encode("shift_jis"); kb = kob(k); p = 0
        while True:
            i = ui.find(nb, p)
            if i < 0: break
            if i == 0 or ui[i-1] in (0, 0x0c):
                en = ui.find(b"\x00", i)
                if en < 0: en = len(ui)
                if len(kb) <= en - i:
                    ui[i:en] = kb + b"\x00"*(en-i-len(kb))
            p = i + 1
    new_ui = huffman.compress(bytes(ui), typ=d.entry_type(UI_ENTRY))
    assert huffman.decompress(new_ui) == bytes(ui)

    # 캐릭터/전투 대사 블록(엔트리 1849~1945, 직접압축 블롭, 페이지 길이보존)
    n_blk = 0
    for entry_s, evs in block_ko.items():
        idx = int(entry_s)
        ent = d.entry(idx)
        if not ent or ent[0] not in (0x08, 0x0c):
            continue
        try:
            dec = huffman.decompress(ent)
        except Exception:
            continue
        ts, events = scen.find_text_region(dec)
        if ts is None:
            continue
        region = bytearray()
        for ei, ev in enumerate(events):
            opages = ev.split(b"\x07")
            kp = evs.get(str(ei))
            for pi, opage in enumerate(opages):
                if kp is not None and pi < len(kp) and kp[pi] != "":
                    _, tokens = cardtext.tokenize(opage)
                    enc = fit_page(kp[pi], tokens, len(opage))
                    region += enc + bytes([PAD]) * (len(opage) - len(enc))
                else:
                    region += opage
                if pi < len(opages) - 1:
                    region += b"\x07"
            region += b"\x00"
            if kp is not None:
                n_blk += 1
        if len(region) != len(dec) - ts:
            continue
        new_dec = dec[:ts] + bytes(region)
        new_sec = huffman.compress(new_dec, typ=ent[0])
        assert huffman.decompress(new_sec) == new_dec
        d.replace_entry(idx, new_sec)

    d.replace_entry(FONT_ENTRY, new_font)
    d.replace_entry(UI_ENTRY, new_ui)
    open(args.outfile, "wb").write(d.build())
    print("스토리대사 %d + 카드 %d + 캐릭터대사 %d + UI/설정 교체 완료 -> %s"
          % (n_ev, n_card, n_blk, args.outfile))


if __name__ == "__main__":
    main()
