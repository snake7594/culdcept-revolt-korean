"""
완성형(wansung) 방식 한글 인코딩.

게임 텍스트 렌더러는 Shift-JIS 코드를 폰트 CMAP으로 조회해 글리프를 그린다.
한글은 Shift-JIS에 없으므로, 필요한 한글 음절 각각을 폰트에 이미 글리프 슬롯이
있는 **JIS 제1수준 한자 코드(0x889f~)** 에 하나씩 배정한다. 그런 다음
  (1) 그 슬롯에 한글 글리프를 그려 넣고(font 모듈),
  (2) 번역문을 배정된 SJIS 코드로 인코딩한다.
이렇게 하면 게임은 코드→글리프 조회로 한글을 그려낸다.

한계: 재활용한 한자 코드가 **번역하지 않은** 다른 화면에서 쓰이면 그 자리에는
한글 글리프가 보인다(부분 패치의 알려진 특성).

배정은 결정적이다(음절 정렬 순 → 코드 정렬 순). 폰트 글리프 주입과 텍스트
인코딩이 반드시 같은 배정을 써야 하므로, 두 곳 모두 build_map()의 결과를 쓴다.
"""

# 제어 토큰(번역 데이터에서 사람이 읽기 쉬운 표기)
LINEBREAK = "⏎"     # ⏎  -> 0x0a
PAGEBREAK = "▼"     # ▼  -> 0x07
NAME = "{N}"             # 플레이어 이름 삽입 -> 0x03 0x30 0x2f

_FULLWIDTH = {"!": "！", "?": "？"}


def is_hangul(ch: str) -> bool:
    return 0xAC00 <= ord(ch) <= 0xD7A3


def kanji_slots(cmap) -> list:
    """폰트 CMAP에서 재활용 가능한 JIS 제1수준 한자 코드(정렬)."""
    return sorted(c for c in cmap if 0x889F <= c <= 0x9872)


def build_map(syllables, cmap) -> dict:
    """{음절: sjis_code} 결정적 배정. syllables는 임의 iterable."""
    sylls = sorted(set(syllables))
    slots = kanji_slots(cmap)
    if len(sylls) > len(slots):
        raise ValueError("한자 슬롯 부족: 필요 %d, 가용 %d" % (len(sylls), len(slots)))
    return {s: slots[i] for i, s in enumerate(sylls)}


def collect_syllables(*texts) -> set:
    """여러 텍스트에서 한글 음절 집합을 모은다."""
    out = set()
    for t in texts:
        for ch in t:
            if is_hangul(ch):
                out.add(ch)
    return out


def encode_char(ch: str, syll2code: dict) -> bytes:
    if is_hangul(ch):
        code = syll2code[ch]
        return bytes([code >> 8, code & 0xFF])
    return _FULLWIDTH.get(ch, ch).encode("shift_jis")


def encode(text: str, syll2code: dict) -> bytes:
    """제어 토큰(⏎ ▼ {N})을 포함한 번역문을 게임 바이트열로 인코딩."""
    out = bytearray()
    i = 0
    while i < len(text):
        if text[i] == LINEBREAK:
            out.append(0x0A); i += 1
        elif text[i] == PAGEBREAK:
            out.append(0x07); i += 1
        elif text[i:i + 3] == NAME:
            out += bytes([0x03, 0x30, 0x2F]); i += 3
        else:
            out += encode_char(text[i], syll2code); i += 1
    return bytes(out)


def page_count(text: str) -> int:
    return text.count(PAGEBREAK) + 1
