#!/usr/bin/env python3
"""
Apply the bsdiff4 delta patch (from Releases) to your own CULDCEPT.DAT.

    pip install bsdiff4
    python apply_patch.py CULDCEPT.DAT culdcept-korean-font-demo.bsdiff4 out/CULDCEPT.DAT

The patch is a binary diff; it is useless without your own original CULDCEPT.DAT.
Equivalently you can skip the patch entirely and run apply_korean_font.py, which
regenerates the same result from your file and a Korean TTF (no patch needed).
"""
import sys
import hashlib
import bsdiff4

# SHA-1 of the CULDCEPT.DAT this patch was built against (Japan, Rev 2 RomFS dump).
SRC_SHA1 = "87439b18719dcd835a253238c922f76df7c0a76e"  # Culdcept Revolt (JP, Rev2) RomFS CULDCEPT.DAT


def main():
    if len(sys.argv) != 4:
        sys.exit("usage: python apply_patch.py <CULDCEPT.DAT> <patch.bsdiff4> <out.DAT>")
    src, patch, out = sys.argv[1:4]
    data = open(src, "rb").read()
    got = hashlib.sha1(data).hexdigest()
    if SRC_SHA1 != "__FILL_SRC_SHA1__" and got != SRC_SHA1:
        print(f"warning: source SHA-1 {got} != expected {SRC_SHA1}; patch may not apply cleanly")
    bsdiff4.file_patch(src, out, patch)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
