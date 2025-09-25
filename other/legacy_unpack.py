import mmap
from .binreader import read_int8

def unpack(fpath):
    print("Unpacking: {}".format(fpath))

    with open(fpath, 'rb') as f:
        mm = mmap.mmap(f.fileno(), length=0, access=mmap.ACCESS_READ)

    mm.seek(0x2, 1)     # sign
    outsz = mm.read(0x3)     # bufsz
    ebx = read_int8(mm)   # 0xE0
    bit_is_set = (ebx & 0x80) != 0

    mm.seek(0x4, 1)     # DB skip

    outsz = outsz[2] | outsz[1] << 8 | outsz[0] << 16

    outbuf = [0] * (outsz * 2)
    outbuf[0] = 0x44
    outbuf[1] = 0x42
    outbuf[2] = 0x0
    outbuf[3] = 0x8
    outbuf_cursor = 4

    pos = mm.tell()
    try:
        while True:
            mm.seek(pos)
            ebx = read_int8(mm)
            pos += 1
            # highest bit
            x80_is_set = (ebx & 0x80) != 0
            x40_is_set = (ebx & 0x40) != 0
            x20_is_set = (ebx & 0x20) != 0
            if not x80_is_set:
                edx = read_int8(mm)
                pos += 1
                eax = read_int8(mm)

                ecx = ebx & 3
                outbuf[outbuf_cursor] = eax
                outbuf[outbuf_cursor+1] = read_int8(mm)
                outbuf[outbuf_cursor+2] = read_int8(mm)

                eax = ecx
                outbuf_cursor += eax
                pos += eax
                mm.seek(pos)

                eax = ebx
                r8 = outbuf_cursor  # outbuf_cursor == r10
                eax = eax & 0x60
                ebx = ((ebx >> 2) & 7) + 3
                ecx = edx + (eax*8)
                eax = ebx
                r8 -= ecx
                outbuf_cursor += eax

                r8 -= 1
                r8 += eax
                ebx = ebx * -1
                edx = ebx
                if edx == 0:
                    continue

                r8 -= outbuf_cursor
                idx = edx + outbuf_cursor*1
                edx = edx * -1
                do_loop = True
                while do_loop:
                    eax = outbuf[r8+idx]
                    outbuf[idx] = eax
                    edx -= 1
                    idx += 1
                    do_loop = edx > 0

            elif not x40_is_set:
                edx = read_int8(mm)
                ebx = ebx & 0x3F

                r8 = edx
                edx = edx & 0x3F
                ebx += 4

                ecx = read_int8(mm)     # +1
                eax = read_int8(mm)     # +2

                outbuf[outbuf_cursor] = eax
                outbuf[outbuf_cursor+1] = read_int8(mm)    # +3
                outbuf[outbuf_cursor+2] = read_int8(mm)    # +4

                r8 = r8 >> 6
                eax = r8
                outbuf_cursor += eax
                edx = edx << 8

                r9 = outbuf_cursor  # ??
                eax = ecx + edx
                r9 -= eax
                ecx = r8 + 2
                eax = ebx
                r9 -= 1
                ebx = ebx * -1
                r9 += eax
                edx = ebx

                outbuf_cursor += eax
                pos += ecx
                mm.seek(pos)
                if edx <= -4:
                    rcx = outbuf_cursor + 1
                    r8 = r9
                    rcx += edx
                    rax = (-4 - edx) >> 2
                    # r8 -= outbuf_cursor
                    edx = rax + 1
                    ebx = ebx + (edx * 4)

                    idx = r8 - eax
                    do_loop = True
                    while do_loop:
                        outbuf[rcx-1] = outbuf[idx]
                        outbuf[rcx] = outbuf[idx+1]
                        outbuf[rcx+1] = outbuf[idx+2]
                        outbuf[rcx+2] = outbuf[idx+3]
                        rcx += 4
                        idx += 4
                        #outbuf_cursor = rcx
                        edx -= 1
                        do_loop = edx > 0
                edx = ebx
                if edx == 0:
                    continue
                r9 -= outbuf_cursor
                idx = edx + outbuf_cursor * 1
                edx = edx * -1
                do_loop = True
                while do_loop:
                    eax = outbuf[r9 + idx]
                    outbuf[idx] = eax
                    edx -= 1
                    idx += 1
                    do_loop = edx > 0

            elif not x20_is_set:
                r8 = ebx
                r8 = r8 & 3
                ecx = read_int8(mm)
                edx = read_int8(mm)
                r9 = read_int8(mm)
                eax = read_int8(mm)

                r9 += 5
                outbuf[outbuf_cursor] = eax
                outbuf[outbuf_cursor+1] = read_int8(mm)
                outbuf[outbuf_cursor+2] = read_int8(mm)

                eax = r8
                outbuf_cursor += eax
                eax = ebx
                eax = eax & 0x10
                ebx = ebx & 0xC
                eax = eax << 4

                rdi = outbuf_cursor

                eax += ecx
                ebx = ebx << 6
                eax = eax << 8

                ecx = r8 + 3

                eax += edx
                r9 += ebx

                rdi -= eax
                pos += ecx
                mm.seek(pos)
                eax = r9
                rdi -= 1
                r9 = r9 * -1
                rdi += eax
                edx = r9
                outbuf_cursor += eax
                # ttt = eax
                if edx <= -4:
                    rcx = outbuf_cursor + 1
                    r8 = rdi
                    rcx += edx
                    eax = -4
                    # r8 -= outbuf_cursor
                    eax = eax >> 2
                    edx = eax + 1
                    r9 = r9 + (edx*4)

                    # mm.seek(r8 - ttt)
                    idx = r8 - eax
                    do_loop = True
                    while do_loop:
                        outbuf[rcx-1] = outbuf[idx]
                        outbuf[rcx] = outbuf[idx+1]
                        outbuf[rcx+1] = outbuf[idx+2]
                        outbuf[rcx+2] = outbuf[idx+3]

                        rcx += 4
                        idx += 4
                        #outbuf_cursor = rcx
                        edx -= 1
                        do_loop = edx > 0
                edx = r9
                if edx == 0:
                    continue

                rdi -= outbuf_cursor
                idx = edx + outbuf_cursor * 1
                edx = edx * -1
                do_loop = True
                while do_loop:
                    eax = outbuf[rdi + idx]
                    outbuf[idx] = eax
                    edx -= 1
                    idx += 1
                    do_loop = edx > 0
            else:
                eax = ebx
                eax = eax & 0x1F
                edx = eax * 4 + 4

                if edx > 0x70:
                    break    # break

                eax = edx
                edx = edx * -1
                r8 = edx
                outbuf_cursor += eax
                pos += eax
                cps = outbuf_cursor

                mm.seek(pos)
                if edx <= -4:
                    rax = outbuf_cursor + 1
                    r9 = mm.tell()
                    rax += r8
                    rcx = (-4 - r8) >> 2
                    #r9 -= outbuf_cursor     # ??

                    r8 = rcx + 1
                    edx = edx + (r8 * 4)

                    mm.seek(r9 - eax)
                    do_loop = True
                    while do_loop:
                        outbuf[rax-1] = read_int8(mm)
                        outbuf[rax] = read_int8(mm)
                        outbuf[rax+1] = read_int8(mm)
                        outbuf[rax+2] = read_int8(mm)
                        rax += 4
                        #outbuf_cursor = rax
                        r8 -= 1
                        do_loop = r8 > 0
                if edx == 0:
                    continue
                cps -= outbuf_cursor
                idx = edx + outbuf_cursor * 1
                edx = edx * -1
                do_loop = True
                while do_loop:
                    eax = outbuf[cps + idx]
                    outbuf[idx] = eax
                    edx -= 1
                    idx += 1
                    do_loop = edx > 0

    except Exception as e:
        print(e)

    ebx = ebx & 3
    if ebx > 0:
        # Not Tested
        do_loop = True
        while do_loop:
            outbuf[outbuf_cursor] = read_int8(mm)
            ebx -= 1
            outbuf_cursor += 1
            do_loop = ebx > 0

    return outbuf, outsz