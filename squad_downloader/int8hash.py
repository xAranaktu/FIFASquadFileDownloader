import hashlib


# https://stackoverflow.com/questions/45279590/which-string-hashing-algorithm-produces-32-bit-or-64-bit-signed-integers
class Int8Hash:

    BYTES = 8
    BITS = BYTES * 8
    BITS_MINUS1 = BITS - 1
    MIN = -(2**BITS_MINUS1)
    MAX = 2**BITS_MINUS1 - 1
    @classmethod
    def as_int(cls, text: str) -> int:
        seed = text.encode()
        hash_digest = hashlib.shake_128(seed).digest(cls.BYTES)
        hash_int = int.from_bytes(hash_digest, byteorder='big', signed=True)
        assert cls.MIN <= hash_int <= cls.MAX
        return hash_int
