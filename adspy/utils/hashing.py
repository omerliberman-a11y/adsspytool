"""Media hashing — SHA-256 for exact dedup, pHash for near-dup across advertisers.

pHash on an image of two ads that share the same hero asset cross-advertiser
returns the same 64-bit fingerprint, even when one party cropped or re-encoded.
"""
from __future__ import annotations

import hashlib
import io
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def phash_bytes(data: bytes) -> str | None:
    """Return a 64-bit perceptual hash as hex, or None if input isn't an image."""
    try:
        import imagehash
        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(io.BytesIO(data)) as img:
            return str(imagehash.phash(img))
    except Exception:
        return None


def hamming_hex(a: str, b: str) -> int:
    """Hamming distance between two hex-encoded hashes of equal length."""
    if len(a) != len(b):
        raise ValueError("hash length mismatch")
    return bin(int(a, 16) ^ int(b, 16)).count("1")
