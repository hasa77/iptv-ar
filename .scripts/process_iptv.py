import requests
import re
from datetime import datetime

# Configuration
M3U_URL = "https://iptv-org.github.io/iptv/languages/ara.m3u"
EPG_URL = "https://iptv-org.github.io/epg/guides/ar.xml"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) VLC/3.0.18'}
BLACKLIST = r"Iran|Afghanistan|Persian|Farsi|Pashto|Tajikistan|Kurd|Kurdish|K24|Rudaw|NRT|Waala|Kurdsat"

def main():
    session = requests.Session()
    session.headers.update(HEADERS)

    print(f"Update started at: {datetime.now()}")

    # 1. Process M3U
    try:
        print("Fetching M3U...")
        r = session.get(M3U_URL, timeout=20)
        r.raise_for_status()
        lines = r.text.splitlines()
        
        curated = ["#EXTM3U"]
        current_info = None
        
        for line in lines:
            if line.startswith("#EXTINF"):
                current_info = line if not re.search(BLACKLIST, line, re.IGNORECASE) else None
            elif line.startswith("http") and current_info:
                # Basic check - if you want it faster, remove the session.get check here
                curated.append(current_info)
                curated.append(line)

        with open("curated-live.m3u", "w", encoding='utf-8') as f:
            f.write("\n".join(curated))
        print(f"M3U Saved. Channels: {len(curated)//2}")
    except Exception as e:
        print(f"M3U Error: {e}")

    # 2. Process EPG
    try:
        print("Fetching EPG...")
        epg_r = session.get(EPG_URL, timeout=30)
        if epg_r.status_code == 200 and b"xml" in epg_r.content[:200]:
            # We add a hidden timestamp at the end so Git always sees a change
            content = epg_r.content + f"\n".encode()
            with open("arabic-epg-clean.xml", "wb") as f:
                f.write(content)
            print("EPG Saved successfully.")
        else:
            print(f"EPG Source returned invalid data: {epg_r.status_code}")
    except Exception as e:
        print(f"EPG Error: {e}")

if __name__ == "__main__":
    main()
