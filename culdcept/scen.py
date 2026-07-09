"""
컬드셉트 리볼트(3DS) 시나리오 컨테이너 + 대사 텍스트 코덱.

CULDCEPT.DAT 안에는 스토리 대사가 **코덱으로 압축된 최상위 엔트리가 아니라**
"시나리오 컨테이너"에 들어 있습니다. 이 컨테이너 엔트리는 코덱 타입 바이트가
아니라 자체 헤더로 시작하기 때문에(예: 0x30 / 0x48 / 0x68 / 0x80 …), 코덱
타입만 보는 스캐너는 이 엔트리를 통째로 지나치게 됩니다.

컨테이너 포맷
------------
  dword0(u32 LE) = 헤더 크기(바이트). 헤더는 (섹션 offset u32, 섹션 length u32)
                   쌍의 배열이며, 섹션 개수 = dword0 / 8.
  각 섹션        = 컨테이너 안의 [offset : offset+length] 조각. 대부분 0x08(간혹
                   0x0c) 코덱으로 압축된 데이터이고, 그 중 하나가 대사 스크립트다.

대사 스크립트 섹션(압축 해제 후)
-------------------------------
  [스크립트 바이트코드 / 헤더]  그 다음  [텍스트 영역]
  텍스트 영역은 null 종료 "이벤트" 문자열의 연속이고, 각 이벤트는 0x07로 나뉜
  "페이지"(대화창 하나)들로 이루어진다.

  제어 코드:  0x00 = 이벤트 끝,  0x07 = 페이지 넘김(클릭 대기),
              0x0a = 줄바꿈,     0x03 0x30 0x2f = 플레이어 이름 삽입.

  ★게임은 각 페이지/이벤트의 시작을 **텍스트 영역 내 절대 바이트 오프셋으로
  참조**한다(실기 확인). 따라서 텍스트 길이를 바꾸면 뒤 오프셋이 전부 어긋나
  대사가 밀리거나 뒤섞인다. **모든 0x07/0x00의 바이트 위치를 원본과 동일하게
  유지**해야 한다 = 각 페이지를 원본 페이지의 바이트 길이에 맞춰(부족분은 뒤에
  공백으로 패딩) 교체한다. rebuild_section_fit()가 이를 수행한다.

이 모듈은 포맷만 담을 뿐 게임 데이터를 포함하지 않는다.
"""
import struct

from . import huffman


def parse_sections(entry: bytes):
    """(offset, length) 섹션 리스트를 반환. 컨테이너가 아니면 None."""
    if len(entry) < 8:
        return None
    d0 = struct.unpack_from("<I", entry, 0)[0]
    if d0 == 0 or d0 % 8 or d0 > len(entry) or d0 > 0x4000:
        return None
    secs = []
    for k in range(d0 // 8):
        off = struct.unpack_from("<I", entry, k * 8)[0]
        ln = struct.unpack_from("<I", entry, k * 8 + 4)[0]
        if ln and (off < d0 or off + ln > len(entry)):   # 빈(len==0) 슬롯은 허용
            return None
        secs.append((off, ln))
    return secs


def is_scenario(entry: bytes) -> bool:
    """섹션들이 모두 컨테이너 범위 안에 놓이고 0x08/0x0c 압축 섹션을 가지면 True."""
    secs = parse_sections(entry)
    if not secs:
        return False
    return any(entry[o] in (0x08, 0x0c) for o, l in secs if l)


def text_start_for(section_dec: bytes, n_events: int):
    """텍스트 영역(마지막 n_events개 이벤트)의 시작 오프셋을 반환.

    이벤트는 내부에 null(0x00)을 포함하지 않으므로, 섹션을 null로 분할하면 각
    이벤트가 하나의 세그먼트가 된다. 섹션은 마지막 이벤트의 종료 null로 끝나므로
    분할 결과의 맨 끝 빈 조각 하나(그 종료 null 뒤)만 제거하면, 뒤쪽 **n_events개
    세그먼트가 곧 텍스트 이벤트들**이다(split_events와 동일한 규칙). 그 첫 이벤트의
    시작 오프셋을 돌려준다. 세그먼트가 부족하면 None.

    전제: 텍스트 영역 직전(=이벤트0 앞) 바이트는 null이어야 한다. 스크립트 헤더가
    null로 끝나지 않으면 헤더 꼬리가 이벤트0에 병합될 수 있다(현재 판본은 성립).
    호출부(find_opening)는 `dec[text_start-1]==0x00` 인지 확인해 전제 위반 후보를
    건너뛴다.
    """
    parts = section_dec.split(b"\x00")
    if parts and parts[-1] == b"":          # 마지막 종료 null 뒤의 빈 조각만 제거
        parts = parts[:-1]
    if len(parts) < n_events:
        return None
    idx = len(parts) - n_events             # 이벤트0에 해당하는 조각 인덱스
    off = 0
    for k in range(idx):
        off += len(parts[k]) + 1            # +1: 각 조각의 종료 null
    return off


def find_text_start(section_dec: bytes) -> int:
    """(구버전 휴리스틱) 첫 SJIS 텍스트 세그먼트 시작 — 스크립트 헤더 오탐 주의."""
    n = len(section_dec)
    p = 0
    while p < n:
        q = section_dec.find(b"\x00", p)
        if q < 0:
            break
        seg = section_dec[p:q]
        if len(seg) >= 6 and _looks_text(seg):
            return p
        p = q + 1
    raise ValueError("텍스트 영역을 찾지 못했습니다")


def _looks_text(seg: bytes) -> bool:
    i = 0
    n = len(seg)
    printable = 0
    while i < n:
        b = seg[i]
        if b in (0x07, 0x0a):
            i += 1
            continue
        if b == 0x03:
            i += 3
            continue
        if 0x81 <= b <= 0xFC and i + 1 < n:      # SJIS 더블바이트
            i += 2
            printable += 1
            continue
        if 0x20 <= b < 0x7F:
            i += 1
            printable += 1
            continue
        return False
    return printable >= 3


def split_events(text_region: bytes):
    """텍스트 영역을 null 종료 이벤트 바이트열 리스트로 분리(마지막 빈 조각 제외)."""
    parts = text_region.split(b"\x00")
    if parts and parts[-1] == b"":
        parts = parts[:-1]
    return parts


def rebuild_section(section_dec: bytes, text_start: int, new_events: list) -> bytes:
    """[헤더 그대로] + [새 이벤트들 + 각 null 종료]로 대사 섹션을 재조립(가변 길이).

    주의: 이 게임은 오프셋 기반이므로 가변 길이 교체는 대사를 어긋나게 한다.
    실제 패치에는 rebuild_section_fit()를 쓸 것. 이 함수는 순차 접근 포맷을 위한
    일반 도구로 남겨 둔다.
    """
    out = bytearray(section_dec[:text_start])
    for ev in new_events:
        out += ev
        out.append(0x00)
    return bytes(out)


def rebuild_section_fit(section_dec: bytes, text_start: int, ko_events: list,
                        encode_fn, pad: int = 0x20) -> bytes:
    """페이지 단위 길이 보존 재빌드 — 모든 0x07/0x00 오프셋을 원본과 동일 유지.

    ko_events[i]는 이벤트 i의 번역 문자열이며 '▼'로 페이지가 나뉜다. 각 페이지는
    encode_fn(page_text)->bytes 로 게임 바이트열로 인코딩되고, 원본 같은 페이지의
    바이트 길이에 맞춰 뒤를 `pad`(기본 0x20 공백; 화면엔 안 보임)로 채운다. 이벤트
    개수·페이지 개수는 원본과 같아야 하고, 어떤 페이지도 원본보다 길면 ValueError.
    반환 섹션은 원본과 바이트 길이가 완전히 같다.
    """
    region = section_dec[text_start:]
    events = region.split(b"\x00")
    if events and events[-1] == b"":
        events = events[:-1]
    if len(events) != len(ko_events):
        raise ValueError("이벤트 개수 불일치: 원본 %d != 번역 %d" % (len(events), len(ko_events)))
    out = bytearray(section_dec[:text_start])
    over = []
    for i, (oev, ko) in enumerate(zip(events, ko_events)):
        opages = oev.split(b"\x07")
        kpages = ko.split("▼")            # '▼'
        if len(opages) != len(kpages):
            raise ValueError("이벤트 %d 페이지 수 불일치: 원본 %d != 번역 %d"
                             % (i, len(opages), len(kpages)))
        for p, opage in enumerate(opages):
            enc = encode_fn(kpages[p])
            if len(enc) > len(opage):
                over.append((i, p, len(enc), len(opage)))
                enc = enc[:len(opage)]
            out += enc + bytes([pad]) * (len(opage) - len(enc))
            if p < len(opages) - 1:
                out += b"\x07"
        out += b"\x00"
    if over:
        raise ValueError("원본 페이지 길이 초과(줄여야 함): %r" % (over,))
    if len(out) != len(section_dec):
        raise ValueError("길이 보존 실패: %d != %d" % (len(out), len(section_dec)))
    return bytes(out)


def rebuild_container(entry: bytes, sec_index: int, new_section_compressed: bytes) -> bytes:
    """섹션 하나를 교체하고 (offset,length) 헤더를 갱신해 컨테이너를 재조립."""
    secs = parse_sections(entry)
    d0 = struct.unpack_from("<I", entry, 0)[0]
    npairs = d0 // 8
    datas = []
    cur = d0
    pairs = []
    for k, (off, ln) in enumerate(secs):
        data = new_section_compressed if k == sec_index else entry[off:off + ln]
        pairs.append((cur, len(data)))
        datas.append(data)
        cur += len(data)
    out = bytearray(b"\x00" * d0)
    for k, (off, ln) in enumerate(pairs):
        struct.pack_into("<II", out, k * 8, off, ln)
    out[npairs * 8:d0] = entry[npairs * 8:d0]         # 헤더 여분 바이트 보존
    for data in datas:
        out += data
    return bytes(out)
