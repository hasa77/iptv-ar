import requests
import re
import os
from datetime import datetime

# Configuration
M3U_URL = "https://iptv-org.github.io/iptv/languages/ara.m3u"
# Switching to the main broad Arabic EPG source
EPG_URL = "https://iptv-org.github.io/epg/guides/ar/beiner-ar.xml"
# Using a standard Chrome User-Agent to prevent 403 blocks
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

    # 2. Process EPG
    try:
        print(f"Fetching EPG from: {EPG_URL}")
        epg_r = session.get(EPG_URL, timeout=60)
        
        # Check if we actually got XML data
        if epg_r.status_code == 200 and (b"xml" in epg_r.content[:200] or b"tv" in epg_r.content[:200]):
            with open("arabic-epg-clean.xml", "wb") as f:
                f.write(epg_r.content)
            print("EPG Saved successfully.")
        else:
            print(f"EPG Source error. Status: {epg_r.status_code}. Data starts with: {epg_r.content[:50]}")
            # Create a blank valid XML so the Git command doesn't crash
            with open("arabic-epg-clean.xml", "w") as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?><tv></tv>')
    except Exception as e:
        print(f"EPG Error: {e}")
        with open("arabic-epg-clean.xml", "w") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?><tv></tv>')

if __name__ == "__main__":
    main()
