import ctypes
import uuid

"""
le == little endian
"""


def _read8(mm, le=True):
    x = mm.read(8)
    if le:
        n = x[0] | x[1] << 8 | x[2] << 16 | x[3] << 24 | x[4] << 32 | x[5] << 40 | x[6] << 48 | x[7] << 56
    else:
        n = x[7] | x[6] << 8 | x[5] << 16 | x[4] << 24 | x[3] << 32 | x[2] << 40 | x[1] << 48 | x[0] << 56
    return n


def _read4(mm, le=True):
    x = mm.read(4)
    if le:
        n = x[0] | x[1] << 8 | x[2] << 16 | x[3] << 24
    else:
        n = x[3] | x[2] << 8 | x[1] << 16 | x[0] << 24
    return n


def read_int64(mm, le=True, signed=True):
    n = _read8(mm, le)

    if not signed:
        n = ctypes.c_ulonglong(n).value
    # else:
    #     n = ctypes.c_longlong(n).value

    return n


def read_int32(mm, le=True, signed=True):
    n = _read4(mm, le)

    if not signed:
        n = ctypes.c_uint(n).value
    # else:
    #     n = ctypes.c_int(n).value

    return n


def read_int16(mm, le=True, signed=True):
    x = mm.read(2)
    if le:
        n = x[0] | x[1] << 8
    else:
        n = x[1] | x[0] << 8

    if not signed:
        n = ctypes.c_ushort(n).value
    # else:
    #     n = ctypes.c_short(n).value

    return n


def read_int8(mm, le=True, signed=True):
    n = mm.read(1)[0]

    if signed:
        n = ctypes.c_ubyte(n).value
    # else:
    #     n = ctypes.c_byte(n).value

    return n


def read_float(mm, le=True):
    n = _read4(mm, le)
    n = ctypes.c_float(n).value
    return n


def read_double(mm, le=True):
    n = _read8(mm, le)
    n = ctypes.c_double(n).value
    return n


def read_guid(mm, le=True):
    buf = mm.read(16)
    if le:
        return str(uuid.UUID(bytes_le=buf))
    else:
        return str(uuid.UUID(bytes=buf))


def read_sha1(mm):
    return mm.read(20)


def read_nullbyte_str(mm, str_len):
    start = mm.tell()
    ret = mm.read(mm.find(b'\x00') - start)  # Read only from start to null byte
    mm.seek(start + str_len)

    try:
        ret = ret.decode('utf-8', 'ignore')
        # replace unallowed characters
        unallowed_characters = (
            '"',
            ',',
            '\a',
            '\b',
            '\f',
            '\r',
            '\t',
        )

        for x in range(len(unallowed_characters)):
            ret = ret.replace(unallowed_characters[x], "")

        # escape new line
        ret = ret.replace('\n', '\\n')
        return ret
    except Exception:
        return ""