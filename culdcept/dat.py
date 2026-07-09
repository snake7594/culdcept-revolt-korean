"""
CULDCEPT.DAT archive container (Culdcept Revolt, 3DS).

Layout
------
  header : an array of 8-byte records (u32 LE offset, u32 LE size), one per entry.
           The number of entries is (first entry's offset) / 8, because the entry
           data begins immediately after the record table.
  entry  : DAT[offset : offset+size].  The first byte of an entry is the codec
           type (see huffman.py / the range-coder types 0x0d/0x8d); type 0x00 is a
           raw/nested container.

This module only parses the table and rebuilds the file.  It does not ship any
game data.
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
        """Append `new_entry` at end of file and point record i at it.

        Appending (rather than rewriting in place) keeps every other entry's
        offset unchanged, so only 8 bytes of the table move.  The old bytes are
        left orphaned but harmless.
        """
        new_off = len(self.data)
        self.data.extend(new_entry)
        struct.pack_into("<II", self.data, i * 8, new_off, len(new_entry))

    def build(self) -> bytes:
        return bytes(self.data)
