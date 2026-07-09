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
  텍스트 영역은 null 종료 "이벤트" 문자열의 연속이다. 스크립트는 이벤트를 순차
  인덱스로 참조하므로(헤더에 텍스트 절대 오프셋이 나타나지 않음) 이벤트 개수와
  순서만 지키면 각 이벤트의 길이는 자유롭게 바꿀 수 있다.

  제어 코드:  0x00 = 이벤트 끝,  0x07 = 페이지 넘김(클릭 대기),
              0x0a = 줄바꿈,     0x03 0x30 0x2f = 플레이어 이름 삽입.

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
    """[헤더 그대로] + [새 이벤트들 + 각 null 종료]로 대사 섹션을 재조립."""
    out = bytearray(section_dec[:text_start])
    for ev in new_events:
        out += ev
        out.append(0x00)
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
