"""
CULDCEPT.DAT 타입 0x08 / 0x0c 코덱 -- 디컴프레서 + 컴프레서 (순수 파이썬).

컬드셉트 리볼트(3DS)의 "텍스트/폰트" 코덱입니다. DEFLATE 계열의 커스텀
canonical-Huffman + LZ 방식으로, 게임의 ARM 디코더에서 리버스 엔지니어링했습니다
(디스패처 guest 0x27f3f4 -> 핸들러 0x274b88 / 0x274b90, 비트 리더
0x275020/0x275028, 크기 varint 0x2747f8, 코드길이 리더 0x274e08 / 0x274d18).
게임 코드나 데이터는 포함하지 않으며, 포맷만 담고 있습니다.

  decompress(entry_bytes) -> bytes      # 타입/크기 헤더를 포함한 엔트리 전체
  compress(data, typ=0x0c) -> bytes     # 게임이 받아들이는 유효 엔트리 생성

타입 0x0d / 0x8d는 다른 (LZMA 계열) 레인지 코더를 쓰며 여기서 다루지 않습니다.
폰트와 대부분의 UI 텍스트는 0x08 / 0x0c 엔트리에 있습니다.
"""

MASK = 0xFFFFFFFF


def clz32(x):
    x &= MASK
    if x == 0:
        return 32
    n = 0
    while not (x & 0x80000000):
        x = (x << 1) & MASK
        n += 1
    return n


# ---------------------------------------------------------------- decoder ----
class _BR:
    """Bit reader matching the game's ARM routine (MSB-first, u16-LE refill)."""
    __slots__ = ('d', 'pos', 'acc', 'cnt')

    def __init__(self, d, pos):
        self.d = d
        self.pos = pos
        self.acc = 0
        self.cnt = 0

    def consume(self, n):
        self.cnt -= n
        self.acc = (self.acc << n) & MASK
        if self.cnt >= 0:
            return
        d = self.d
        p = self.pos
        h = d[p] | (d[p + 1] << 8)                      # little-endian halfword
        self.pos = p + 2
        r1 = (((h & 0xff) << 24) | (((h >> 8) & 0xff) << 16)) & MASK
        self.cnt += 16
        self.acc = (self.acc | (r1 >> self.cnt)) & MASK

    def getbits(self, n):
        if n == 0:
            self.consume(0)
            return 0
        v = self.acc >> (32 - n)
        self.consume(n)
        return v


def parse_varint(d, i):
    """Variable-length size (ARM 0x2747f8); continuation via the sign bit."""
    b1 = d[i]; i += 1
    r5 = b1 - 256 if b1 >= 128 else b1
    b2 = d[i]; i += 1
    r4 = (b2 | ((r5 << 8) & MASK)) & MASK
    if not (r4 & 0x80000000):
        return r4, i
    r4 &= 0x7FFF
    b3 = d[i]; i += 1
    r5 = b3 - 256 if b3 >= 128 else b3
    r4 = (r4 | ((r5 << 15) & MASK)) & MASK
    if not (r4 & 0x80000000):
        return r4, i
    r4 &= 0x3FFFFF
    b4 = d[i]; i += 1
    r4 = (r4 | (b4 << 22)) & MASK
    return r4, i


class _Huff:
    """Canonical (DEFLATE-order, MSB-first) Huffman decoder."""
    __slots__ = ('single', 'symtab', 'maxlen')

    def __init__(self, lengths=None, single=None):
        if single is not None:
            self.single = single
            return
        self.single = None
        maxlen = max(lengths) if lengths else 0
        self.maxlen = maxlen
        blcount = [0] * (maxlen + 1)
        for l in lengths:
            if l:
                blcount[l] += 1
        nextcode = [0] * (maxlen + 2)
        c = 0
        for l in range(1, maxlen + 1):
            c = (c + blcount[l - 1]) << 1
            nextcode[l] = c
        self.symtab = {}
        nc = nextcode[:]
        for sym, l in enumerate(lengths):
            if l:
                self.symtab[(l, nc[l])] = sym
                nc[l] += 1

    def decode(self, br):
        if self.single is not None:
            return self.single
        code = 0
        st = self.symtab
        for l in range(1, self.maxlen + 1):
            code = (code << 1) | ((br.acc >> 31) & 1)
            br.consume(1)
            s = st.get((l, code))
            if s is not None:
                return s
        raise ValueError("bad huffman code")


def _read_lengths_direct(br, nsym, nbits, special_pos):
    count = br.getbits(nbits)
    if count == 0:
        return None, br.getbits(nbits)
    codelen = [0] * max(nsym, count + 40)
    i = 0
    while i < count:
        t = br.acc >> 29
        if t < 7:
            length = t
            br.consume(3)
        else:
            k = clz32((~((br.acc << 3) & MASK)) & MASK)
            length = 7 + k
            br.consume(length - 3)
        codelen[i] = length
        i += 1
        if i == special_pos:
            r = br.getbits(2)
            if r != 0:
                end = r + i
                while i < end:
                    codelen[i] = 0
                    i += 1
    return codelen[:max(nsym, i)], None


def _make(lengths, single):
    return _Huff(single=single) if single is not None else _Huff(lengths)


def _read_litlen(br):
    cl_len, cl_single = _read_lengths_direct(br, 19, 5, 3)
    cl = _make(cl_len, cl_single)
    count = br.getbits(9)
    if count == 0:
        return _Huff(single=br.getbits(9))
    out = []
    while len(out) < count:
        s = cl.decode(br)
        if s > 2:
            out.append(s - 2)
        elif s == 0:
            out.append(0)
        elif s == 1:
            out.extend([0] * (3 + br.getbits(4)))
        else:  # s == 2
            out.extend([0] * (0x14 + br.getbits(9)))
    return _Huff(out)


def decompress(entry_bytes):
    """Decompress a whole type-0x08/0x0c entry (including its 4-byte header)."""
    typ = entry_bytes[0]
    if typ not in (0x08, 0x0c):
        raise NotImplementedError("type %#x not supported (0x0d/0x8d = range coder)" % typ)
    d = bytes(entry_bytes) + b'\x00' * 8       # guard for the final halfword refill
    window = 0x10 if typ == 0x0c else 0x0d
    size, pos = parse_varint(d, 1)
    br = _BR(d, pos)
    if pos & 1:                                # address-parity pre-load
        br.acc = (d[pos] << 8) & MASK
        br.pos = pos + 1
        br.cnt = 8
    br.consume(16)                             # prime the accumulator

    out = bytearray()
    dist_nsym = window + 1
    dist_nbits = (window + 1 - 10) & 5
    while len(out) < size:
        r8 = br.getbits(16)
        litlen = _read_litlen(br)
        dl, ds = _read_lengths_direct(br, dist_nsym, dist_nbits, -1)
        dist = _make(dl, ds)
        for _ in range(r8):
            sym = litlen.decode(br)
            if sym < 0x100:
                out.append(sym)
            else:
                length = sym - 0xFD
                dsym = dist.decode(br)
                dd = 1 if dsym == 0 else (1 << (dsym - 1)) + 1 + br.getbits(dsym - 1)
                start = len(out) - dd
                for k in range(length):
                    out.append(out[start + k])
            if len(out) >= size:
                break
        if len(out) >= size:
            break
    return bytes(out[:size])


# ---------------------------------------------------------------- encoder ----
# All-literal, uniform 8-bit scheme: every block uses a degenerate CL table
# (single symbol 10, 0 bits), a 256-entry all-length-8 litlen table (so literal
# byte B is written as the raw 8-bit value B, MSB-first) and an unused degenerate
# distance table.  The payload is just the literal bytes.  It does not compress,
# but it is a valid stream the game decodes exactly, which is all patching needs.
_BLOCK_MAX = 0xFFFF


def _emit_varint(size):
    if size < 0:
        raise ValueError("size < 0")
    if size < 0x8000:
        return bytes([size >> 8, size & 0xFF])
    if size < 0x400000:
        return bytes([0x80 | ((size >> 8) & 0x7F), size & 0xFF, (size >> 15) & 0x7F])
    if size < 0x40000000:
        return bytes([0x80 | ((size >> 8) & 0x7F), size & 0xFF,
                      0x80 | ((size >> 15) & 0x7F), (size >> 22) & 0xFF])
    raise ValueError("size too large for varint (>= 2^30)")


class _BW:
    __slots__ = ("acc", "nbits", "out")

    def __init__(self):
        self.acc = 0
        self.nbits = 0
        self.out = bytearray()

    def write(self, val, n):
        if n == 0:
            return
        self.acc = (self.acc << n) | (val & ((1 << n) - 1))
        self.nbits += n
        while self.nbits >= 8:
            self.nbits -= 8
            self.out.append((self.acc >> self.nbits) & 0xFF)
        self.acc &= (1 << self.nbits) - 1

    def getbytes(self):
        if self.nbits > 0:
            self.out.append((self.acc << (8 - self.nbits)) & 0xFF)
            self.acc = 0
            self.nbits = 0
        return bytes(self.out)


def compress(data, typ=0x0c):
    """Produce a valid type-0x08/0x0c entry (header + stream) for `data`."""
    if typ not in (0x08, 0x0c):
        raise ValueError("typ must be 0x08 or 0x0c")
    data = bytes(data)
    window = 0x10 if typ == 0x0c else 0x0d
    dist_nbits = (window + 1 - 10) & 5
    header = bytes([typ]) + _emit_varint(len(data))
    bw = _BW()
    i = 0
    while i < len(data):
        chunk = data[i:i + _BLOCK_MAX]
        bw.write(len(chunk), 16)      # r8: symbol count
        bw.write(0, 5); bw.write(10, 5)          # CL: single = 10
        bw.write(256, 9)                          # litlen: 256 x length-8
        bw.write(0, dist_nbits); bw.write(0, dist_nbits)   # dist: degenerate
        for b in chunk:
            bw.write(b, 8)
        i += len(chunk)
    return header + bw.getbytes()


if __name__ == "__main__":
    import os
    for n in (0, 1, 1000, 70000, 300000):
        d = os.urandom(n)
        assert decompress(compress(d, 0x0c)) == d, n
        assert decompress(compress(d, 0x08)) == d, n
    print("round-trip OK")
