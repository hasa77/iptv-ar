import requests
import re
import os
import gzip
import io
from datetime import datetime

# Configuration
M3U_URL = "https://iptv-org.github.io/iptv/languages/ara.m3u"
# Using the specific Arabic guide from EPGShare01
EPG_URL = "https://epgshare01.online/epgshare01/epg_ripper_ARABIC1.xml.gz"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'}
BLACKLIST = r"Iran|Afghanistan|Persian|Farsi|Pashto|Tajikistan|Kurd|Kurdish|K24|Rudaw|NRT|Waala|Kurdsat"

def main():
    session = requests.Session()
    session.headers.update(HEADERS)
    print(f"Update started at: {datetime.now()}")

    # 1. Process M3U
    try:
        print(f"Fetching M3U from: {M3U_URL}")
        r = session.get(M3U_URL, timeout=30)
        r.raise_for_status()
        lines = r.text.splitlines()
        
        curated = ["#EXTM3U"]
        current_info = None
        
        for line in lines:
            if line.startswith("#EXTINF"):
                current_info = line if not re.search(BLACKLIST, line, re.IGNORECASE) else None
            elif line.startswith("http") and current_info:
                curated.append(current_info)
                curated.append(line)

        with open("curated-live.m3u", "w", encoding='utf-8') as f:
            f.write("\n".join(curated))
        print(f"M3U Saved. Channels: {len(curated)//2}")
    except Exception as e:
        print(f"M3U Error: {e}")

    # 2. Process EPG (Updated with GZIP support)
    try:
        print(f"Fetching EPG from: {EPG_URL}")
        epg_r = session.get(EPG_URL, timeout=180) # Large file, longer timeout
        
        if epg_r.status_code == 200 and len(epg_r.content) > 1000:
            # Check if the content is gzipped
            if EPG_URL.endswith(".gz"):
                print("Decompressing GZIP file...")
                with gzip.GzipFile(fileobj=io.BytesIO(epg_r.content)) as gz:
                    xml_data = gz.read()
            else:
                xml_data = epg_r.content

            with open("arabic-epg-clean.xml", "wb") as f:
                f.write(xml_data)
            print(f"EPG Saved. Final XML Size: {len(xml_data) / 1024 / 1024:.2f} MB")
        else:
            print(f"EPG Download failed. Status: {epg_r.status_code}")
            if not os.path.exists("arabic-epg-clean.xml"):
                with open("arabic-epg-clean.xml", "w") as f:
                    f.write('<?xml version="1.0" encoding="UTF-8"?><tv></tv>')
    except Exception as e:
        print(f"EPG Error: {e}")

if __name__ == "__main__":
    main()
