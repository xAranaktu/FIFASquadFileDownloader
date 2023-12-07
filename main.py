import mmap
import os
import ssl
import xml.etree.ElementTree as ET

from requests import get

from squad_downloader.binreader import read_int8

ssl._create_default_https_context = ssl._create_unverified_context

RESULT_DIR = "result"
# CONTENT_URL = "https://fifa21.content.easports.com/fifa/fltOnlineAssets/21D4F1AC-91A3-458D-A64E-895AA6D871D1/2021/"
# CONTENT_URL = "https://fifa22.content.easports.com/fifa/fltOnlineAssets/22747632-e3df-4904-b3f6-bb0035736505/2022/"
# CONTENT_URL = "https://fifa23.content.easports.com/fifa/fltOnlineAssets/23DF3AC5-9539-438B-8414-146FAFDE3FF2/2023/"
CONTENT_URL = "https://eafc24.content.easports.com/fc/fltOnlineAssets/24B23FDE-7835-41C2-87A2-F453DFDB2E82/2024/"
ROSTERUPDATE_XML = "rosterupdate.xml"
FIFA = "24"


def download(fpath, url):
    print(f"Download: {url}")
    with open(fpath, "wb") as f:
        try:
            response = get(url=url)
            content = response.content
            f.write(content)
        except Exception as e:
            print(e)

def download_rosterupdate():
    roster_update_url = f"{CONTENT_URL}fc/fclive/genxtitle/rosterupdate.xml"
    download(ROSTERUPDATE_XML, roster_update_url)


def save_squads(buf, outsz, path, filename):
    fullpath = os.path.join(path, filename)
    # SAVE
    ingame_name = f"EA_{filename}"

    headersz = 52
    totalsz = outsz + headersz
    fheader = []

    # FBCHUNKS
    fheader.append(b"\x46\x42\x43\x48\x55\x4E\x4B\x53\x01\x00\xB8\x00\x00\x00")

    # Filesize
    fheader.append(totalsz.to_bytes(4, 'little'))

    # Name of the squadfile visible in game
    fheader.append(ingame_name.encode())

    # mySign
    if "Fut" in filename:
        fheader.append(b"\x00" * 4)
    else:
        fheader.append(b"\x00" * 7)

    fheader.append("Aranaktu".encode())
    fheader.append(b"\x00" * 8)

    # nullbyte padding
    fheader.append(b"\x00" * 0x12)
    fheader.append(b"\x00" * 0x64)


    #Unknown
    fheader.append(b"\x00\x07\x5C\xB7\xEE\xFF\xFF\xFF\xFF\xFF\xFF\xF9\xC3\x6B\x0C\x00\x00\x00\x00\x00")
    # SaveType
    if "Fut" in filename:
        fheader.append(b"\x53\x61\x76\x65\x54\x79\x70\x65\x5F\x46\x55\x54\x53\x71\x75\x00")
    else:
        fheader.append(b"\x53\x61\x76\x65\x54\x79\x70\x65\x5F\x53\x71\x75\x61\x64\x73\x00")

    # CRC32 of DB
    fheader.append(b"\x00" * 4)

    #Unknown
    fheader.append(
        b"\xD2\x00\x00\x00"
        b"\x72\xB7\x97\x00"
        b"\x40\x32\xA7\x46"
        b"\x87\x10\x16\x6A"
        b"\xFC\xD8\x1D\x23"
        b"\x1C\xE6\x89\x95"
        b"\x00\x00\x00\x00"
    )

    if "Fut" not in filename:
        fheader.append(b"\x28\x6F\xA0\x00")

    with open(fullpath, 'wb') as f:
        for b in fheader:
            f.write(b)

        for i in range(outsz):
            f.write(buf[i].to_bytes(1, 'little'))

    return filename

def process_rosterupdate():
    result = dict()
    to_collect = [
        "dbMajor", "dbFUTVer", "dbMajorLoc", "dbFUTLoc"
    ]

    download_rosterupdate()
    tree = ET.parse(ROSTERUPDATE_XML)
    root = tree.getroot()

    try:
        squadinfoset = root[0]
        result["platforms"] = list()
        for child in squadinfoset:
            platform = dict()
            platform_name = child.attrib["platform"]
            platform["name"] = platform_name
            platform["tags"] = dict()
            for node in list(child.iter()):
                if node.tag in to_collect:
                    platform["tags"][node.tag] = node.text

            result["platforms"].append(platform)
    except Exception:
        return result

    return result


# def extract(filename):
#     result_dir = "extracted"
#     if not os.path.isdir(result_dir):
#         os.mkdir(result_dir)
#     xml_meta_path = os.path.join("Data", FIFA, "XML", "fifa_ng_db-meta.xml")
#
#     fp = FIFAFileParser(result_dir, xml_meta_path, filename)
#     fp.unpack_files()
#     fp.process_all([])
#     fp.export_all()


def unpack(fpath):
    print(f"Unpacking: {fpath}")

    with open(fpath, 'rb') as f:
        mm = mmap.mmap(f.fileno(), length=0, access=mmap.ACCESS_READ)

    mm.seek(0x2, 1)     # sign
    outsz = mm.read(0x3)     # bufsz
    ebx = read_int8(mm)   # 0xE0
    # bit_is_set = (ebx & 0x80) != 0

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


if __name__ == '__main__':
    if not os.path.isdir(RESULT_DIR):
        os.mkdir(RESULT_DIR)

    result = process_rosterupdate()

    for platform in result["platforms"]:
        platform_path = os.path.join(RESULT_DIR, platform["name"])
        if not os.path.isdir(platform_path):
            os.mkdir(platform_path)

        tags = platform["tags"]

        ver = tags["dbMajor"]
        ver_path = os.path.join(platform_path, "squads", ver)
        if not os.path.isdir(ver_path):
            os.makedirs(ver_path)
            loc = tags["dbMajorLoc"]
            bin_fname = os.path.basename(loc)
            bin_path = os.path.join(ver_path, bin_fname)
            download(bin_path, f"{CONTENT_URL}{loc}")
            fdate = bin_fname.split("_")[1]

            buf, sz = unpack(bin_path)
            save_squads(buf, sz, ver_path, f"Squads{fdate}000000")

        ver = tags["dbFUTVer"]
        ver_path = os.path.join(platform_path, "FUT", ver)
        if not os.path.isdir(ver_path):
            os.makedirs(ver_path)
            loc = tags["dbFUTLoc"]
            bin_fname = os.path.basename(loc)
            bin_path = os.path.join(ver_path, bin_fname)
            download(bin_path, f"{CONTENT_URL}{loc}")
            fdate = bin_fname.split("_")[1]

            buf, sz = unpack(bin_path)
            save_squads(buf, sz, ver_path, f"FutSquads{fdate}000000")
