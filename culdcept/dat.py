"""
CULDCEPT.DAT 아카이브 컨테이너 (컬드셉트 리볼트, 3DS).

구조
----
  헤더   : 엔트리마다 8바이트 레코드(u32 LE offset, u32 LE size)의 배열.
           엔트리 개수 = (첫 엔트리의 offset) / 8. 엔트리 데이터가 레코드 테이블
           바로 뒤에서 시작하기 때문입니다.
  엔트리 : DAT[offset : offset+size]. 엔트리의 첫 바이트는 코덱 타입입니다
           (huffman.py 참고 / 레인지 코더 타입 0x0d,0x8d). 타입 0x00은
           원시/중첩 컨테이너입니다.

이 모듈은 테이블을 파싱하고 파일을 재빌드할 뿐, 게임 데이터를 포함하지 않습니다.
"""
import struct


class Dat:
    def __init__(self, data: bytes):
        self.data = bytearray(data)
        first = struct.unpack_from("<I", self.data, 0)[0]
        self.count = first // 8
        self.table = [struct.unpack_from("<II", self.data, i * 8) for i in range(self.count)]

    def entry(self, i: int) -> bytes:
        off, size = self.table[i]
        return bytes(self.data[off:off + size])

    def entry_type(self, i: int) -> int:
        off, size = self.table[i]
        return self.data[off] if size else -1

    def replace_entry(self, i: int, new_entry: bytes) -> None:
        """`new_entry`를 파일 끝에 추가하고 레코드 i가 그것을 가리키게 한다.

        제자리에서 다시 쓰지 않고 뒤에 추가하므로 다른 엔트리의 offset은 그대로
        유지되고, 테이블에서 8바이트만 바뀝니다. 기존 바이트는 참조되지 않은 채
        남지만 무해합니다.
        """
        new_off = len(self.data)
        self.data.extend(new_entry)
        struct.pack_into("<II", self.data, i * 8, new_off, len(new_entry))

    def build(self) -> bytes:
        return bytes(self.data)
