import hashlib

from .reader import Reader

# size of page in most x86 unix systems
FOUR_K = 4096


def buffered_md5(r: Reader, block_size: int = FOUR_K) -> str:
    h = hashlib.md5(usedforsecurity=False)
    chunk = r.read(block_size)
    while chunk:
        h.update(chunk)
        chunk = r.read(block_size)

    return h.hexdigest()
