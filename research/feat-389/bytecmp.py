"""Byte comparison of two pack folders, per top-level entry (folder or file)."""
import hashlib, os, sys
a, b = sys.argv[1], sys.argv[2]
def files(root):
    out = {}
    for d, _, fs in os.walk(root):
        for f in fs:
            p = os.path.join(d, f); out[os.path.relpath(p, root).replace("\\", "/")] = p
    return out
A, B = files(a), files(b)
groups = sorted({k.split("/")[0] for k in A} | {k.split("/")[0] for k in B})
for g in groups:
    ka = {k for k in A if k.split("/")[0] == g}; kb = {k for k in B if k.split("/")[0] == g}
    diff = [k for k in sorted(ka & kb) if open(A[k], "rb").read() != open(B[k], "rb").read()]
    n = len(ka | kb); size = sum(os.path.getsize(A[k]) for k in ka)
    st = "IDENTICAL" if not diff and ka == kb else f"DIFFERS: {len(diff)} changed, {len(ka - kb)} only in A, {len(kb - ka)} only in B"
    print(f"{g:16s} {n:5d} files {size / 1e6:8.1f} MB  {st}")
