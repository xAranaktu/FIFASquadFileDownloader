import os
import urllib.request
import xml.etree.ElementTree as ET
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

# CONTENT_URL = "https://fifa21.content.easports.com/fifa/fltOnlineAssets/21D4F1AC-91A3-458D-A64E-895AA6D871D1/2021/"
# CONTENT_URL = "https://fifa22.content.easports.com/fifa/fltOnlineAssets/22747632-e3df-4904-b3f6-bb0035736505/2022/"
# CONTENT_URL = "https://fifa23.content.easports.com/fifa/fltOnlineAssets/23DF3AC5-9539-438B-8414-146FAFDE3FF2/2023/"
# CONTENT_URL = "https://eafc24.content.easports.com/fc/fltOnlineAssets/24B23FDE-7835-41C2-87A2-F453DFDB2E82/2024/"
# CONTENT_URL = "https://eafc25.content.easports.com/fc/fltOnlineAssets/25E4CDAE-799B-45BE-B257-667FDCDE8044/2025/"
CONTENT_URL = "https://eafc26.content.easports.com/fc/fltOnlineAssets/26E4D4D6-8DBB-4A9A-BD99-9C47D3AA341D/2026/"
ROSTERUPDATE_XML = "rosterupdate.xml"

# signs
T3DB = b"\x44\x42\x00\x08"
FBCHUNKS = b"\x46\x42\x43\x48\x55\x4E\x4B\x53\x01\x00"
BNRY = b"\x42\x4E\x52\x59\x00\x00\x00\x02\x4C\x54\x4C\x45\x01\x01\x03\x00" \
       b"\x00\x00\x63\x64\x73\x01\x00\x00\x00\x00\x01\x03\x00\x00\x00\x63\x64\x73"

RESULT_DIR = "result"


def download(fpath, url):
    print("Download: {}".format(url))
    with open(fpath, "wb") as f:
        try:
            response = urllib.request.urlopen(url)
            f.write(response.read())
        except Exception as e:
            print(e)

def download_rosterupdate():
    roster_update_url = "{}fc/fclive/genxtitle/rosterupdate.xml".format(CONTENT_URL)
    download(ROSTERUPDATE_XML, roster_update_url)

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
    except Exception as e:
        return result
    
    return result


def save_squads(buf, path, filename):
    fullpath = os.path.join(path, filename)
    is_fut = "Fut" in filename
    db_size = len(buf)
    
    # Save types
    save_type_squads = b"SaveType_Squads\x00"
    save_type_fut = b"SaveType_FUTSqu\x00"

    author_sign = b"Aranaktu"

    # FC26 chunk sizes
    prefix_header_size = 1126
    main_header_size = 48
    bnry_size = 45985

    # Calculate file size
    bnry_size = 0 if is_fut else bnry_size
    file_size = main_header_size + 4 + db_size + bnry_size
    
    # Build prefix header
    prefix_header = bytearray(prefix_header_size)
    pos = 0
    
    # FBCHUNKS sign
    prefix_header[pos:pos+len(FBCHUNKS)] = FBCHUNKS
    pos += len(FBCHUNKS)
    
    # Main header offset
    main_header_offset = prefix_header_size - pos - 8
    prefix_header[pos:pos+4] = main_header_offset.to_bytes(4, "little")
    pos += 4
    
    # File size excluding prefix header
    prefix_header[pos:pos+4] = file_size.to_bytes(4, "little")
    pos += 4
    
    # In-game name 
    ingame_name = "EA_{}".format(filename).encode()[:40] # max to 40 bytes
    prefix_header[pos:pos+len(ingame_name)] = ingame_name
    pos += len(ingame_name)

    # Author sign
    sign_size = 4 if is_fut else 7
    pos += sign_size
    prefix_header[pos:pos+len(author_sign)] = author_sign 
    
    # Build main header
    main_header = bytearray(main_header_size)

    # Save type
    save_type = save_type_fut if is_fut else save_type_squads
    main_header[:len(save_type)] = save_type
    
    # CRC32
    crc_pos = len(save_type)
    main_header[crc_pos:crc_pos+4] = (0).to_bytes(4, "little") 

    # Calculate data section size
    data_size = 0 if is_fut else db_size + bnry_size
    
    with open(fullpath, "wb") as f:
        # Write prefix header
        f.write(bytes(prefix_header))
        
        # Write main header
        f.write(bytes(main_header))
        
        # Write data section size
        f.write(data_size.to_bytes(4, "little"))
        
        # Write DB
        f.write(buf)
        
        # Write BNRY chunk only for Squads
        if not is_fut:
            f.write(BNRY)
            remaining_bnry = bnry_size - len(BNRY)
            f.write(b"\x00" * remaining_bnry)
    
    return filename

def unpack(fpath):
    print("Unpacking: {}".format(fpath))
    
    # Control masks
    SHORT_COPY = 0x80
    MEDIUM_COPY = 0x40
    LONG_COPY = 0x20
    
    # Read input file
    with open(fpath, "rb") as f:
        data = f.read()
    
    # Initialize output buffer
    size = int.from_bytes(data[2:5], "big")
    outbuf = bytearray(size)
    outbuf[:len(T3DB)] = T3DB
    
    ipos = 10  # start pos
    opos = len(T3DB)
    in_len, out_len = len(data), len(outbuf)
    last_control = 0
    
    while ipos < in_len and opos < out_len:
        control = data[ipos]
        last_control = control
        ipos += 1
        
        if not (control & SHORT_COPY):
            b1 = data[ipos]
            ipos += 1
            lit = control & 3
            if lit:
                outbuf[opos:opos+lit] = data[ipos:ipos+lit]
                ipos += lit
                opos += lit
            length = ((control >> 2) & 7) + 3
            offset = b1 + ((control & 0x60) << 3) + 1
            src = opos - offset
            for _ in range(length):
                outbuf[opos] = outbuf[src]
                opos += 1
                src += 1
        
        elif not (control & MEDIUM_COPY):
            b2, b3 = data[ipos:ipos+2]
            ipos += 2
            lit = b2 >> 6
            if lit:
                outbuf[opos:opos+lit] = data[ipos:ipos+lit]
                ipos += lit
                opos += lit
            length = (control & 0x3F) + 4
            offset = ((b2 & 0x3F) << 8 | b3) + 1
            src = opos - offset
            for _ in range(length):
                outbuf[opos] = outbuf[src]
                opos += 1
                src += 1
        
        elif not (control & LONG_COPY):
            b2, b3, b4 = data[ipos:ipos+3]
            ipos += 3
            lit = control & 3
            if lit:
                outbuf[opos:opos+lit] = data[ipos:ipos+lit]
                ipos += lit
                opos += lit
            length = b4 + ((control & 0x0C) << 6) + 5
            offset = (((control & 0x10) << 12) | (b2 << 8) | b3) + 1
            src = opos - offset
            for _ in range(length):
                outbuf[opos] = outbuf[src]
                opos += 1
                src += 1
        
        else:  # literal copy
            lit = (control & 0x1F) * 4 + 4
            if lit > 0x70:
                break
            outbuf[opos:opos+lit] = data[ipos:ipos+lit]
            ipos += lit
            opos += lit
    
    # handle trailing bytes
    trailing = last_control & 3
    if trailing and opos < out_len:
        end_pos = min(opos + trailing, out_len)
        outbuf[opos:end_pos] = data[ipos:ipos + (end_pos - opos)]
    
    return bytes(outbuf), size


if __name__ == "__main__":
    if not os.path.isdir(RESULT_DIR):
        os.mkdir(RESULT_DIR)
    
    result = process_rosterupdate()
    
    for platform in result["platforms"]:
        # Ignore Stadia. Stadia was shut down on January 18, 2023.
        if platform["name"] == "sta":
            continue
        
        platform_path = os.path.join(RESULT_DIR, platform["name"])
        if not os.path.isdir(platform_path):
            os.mkdir(platform_path)
        
        tags = platform["tags"]
        
        # Process Squads
        ver = tags["dbMajor"]
        ver_path = os.path.join(platform_path, "squads", ver)
        if not os.path.isdir(ver_path):
            os.makedirs(ver_path)
            loc = tags["dbMajorLoc"]
            bin_fname = os.path.basename(loc)
            bin_path = os.path.join(ver_path, bin_fname)
            download(bin_path, "{}{}".format(CONTENT_URL, loc))
            fdate = bin_fname.split("_")[1]
            
            buf, sz = unpack(bin_path)
            save_squads(buf, ver_path, "Squads{}000000".format(fdate))
        
        # Process FUT
        ver = tags["dbFUTVer"]
        ver_path = os.path.join(platform_path, "FUT", ver)
        if not os.path.isdir(ver_path):
            os.makedirs(ver_path)
            loc = tags["dbFUTLoc"]
            bin_fname = os.path.basename(loc)
            bin_path = os.path.join(ver_path, bin_fname)
            download(bin_path, "{}{}".format(CONTENT_URL, loc))
            fdate = bin_fname.split("_")[1]
            
            buf, sz = unpack(bin_path)
            save_squads(buf, ver_path, "FutSquads{}000000".format(fdate))