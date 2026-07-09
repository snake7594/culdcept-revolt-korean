"""
Demo mapping: Japanese kana -> phonetic Hangul.

This is a PROOF-OF-CONCEPT only.  It does not translate anything; it simply
replaces each kana glyph in the game's font with a Hangul syllable that sounds
similar, so you can visually confirm that the Korean glyphs render in-game at
every font size.  A real translation replaces the *text* (see docs/FORMAT.md),
not just the glyphs.
"""

_HIRA = {
    'あ': '아', 'い': '이', 'う': '우', 'え': '에', 'お': '오',
    'か': '카', 'き': '키', 'く': '쿠', 'け': '케', 'こ': '코',
    'が': '가', 'ぎ': '기', 'ぐ': '구', 'げ': '게', 'ご': '고',
    'さ': '사', 'し': '시', 'す': '스', 'せ': '세', 'そ': '소',
    'ざ': '자', 'じ': '지', 'ず': '즈', 'ぜ': '제', 'ぞ': '조',
    'た': '타', 'ち': '치', 'つ': '츠', 'て': '테', 'と': '토',
    'だ': '다', 'ぢ': '지', 'づ': '즈', 'で': '데', 'ど': '도',
    'な': '나', 'に': '니', 'ぬ': '누', 'ね': '네', 'の': '노',
    'は': '하', 'ひ': '히', 'ふ': '후', 'へ': '헤', 'ほ': '호',
    'ば': '바', 'び': '비', 'ぶ': '부', 'べ': '베', 'ぼ': '보',
    'ぱ': '파', 'ぴ': '피', 'ぷ': '푸', 'ぺ': '페', 'ぽ': '포',
    'ま': '마', 'み': '미', 'む': '무', 'め': '메', 'も': '모',
    'や': '야', 'ゆ': '유', 'よ': '요',
    'ら': '라', 'り': '리', 'る': '루', 'れ': '레', 'ろ': '로',
    'わ': '와', 'を': '오', 'ん': 'ㄴ',
    'ぁ': '아', 'ぃ': '이', 'ぅ': '우', 'ぇ': '에', 'ぉ': '오',
    'っ': 'ㅅ', 'ゃ': '야', 'ゅ': '유', 'ょ': '요',
}


def build():
    """Return {shift_jis_code: hangul} for hiragana and katakana."""
    m = {}
    for hira, kr in _HIRA.items():
        for ch in (hira, chr(ord(hira) + 0x60)):     # hiragana + its katakana
            try:
                m[int.from_bytes(ch.encode("shift_jis"), "big")] = kr
            except UnicodeEncodeError:
                pass
    return m
