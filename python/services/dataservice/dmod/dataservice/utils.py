import sys
import hashlib

from .reader import Reader

# size of page in most x86 unix systems
FOUR_K = 4096


def buffered_md5(r: Reader, block_size: int = FOUR_K) -> str:
    if sys.version_info >= (3, 9):
        h = hashlib.md5(usedforsecurity=False)
    else:
        h = hashlib.md5()
    chunk = r.read(block_size)
    while chunk:
        h.update(chunk)
        chunk = r.read(block_size)

    return h.hexdigest()
