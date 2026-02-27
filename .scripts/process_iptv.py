import requests
import re

# Configuration
M3U_URL = "https://iptv-org.github.io/iptv/languages/ara.m3u"
EPG_URL = "https://iptv-org.github.io/epg/guides/ar/beiner-ar.xml"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# Keywords to exclude (Iran, Afghanistan, etc.)
BLACKLIST = r"Iran|Afghanistan|Persian|Farsi|Pashto"

def main():
    session = requests.Session()
    session.headers.update(HEADERS)

    print("Fetching and filtering M3U...")
    try:
        response = session.get(M3U_URL, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch M3U: {e}")
        return

    lines = response.text.splitlines()
    curated_channels = ["#EXTM3U"]
    current_info = ""

    for line in lines:
        if line.startswith("#EXTINF"):
            # Skip if blacklist keyword is found in the channel info
            if re.search(BLACKLIST, line, re.IGNORECASE):
                current_info = None
            else:
                current_info = line
        elif line.startswith("http") and current_info:
            print(f"Checking: {line[:50]}...")
            try:
                # Use stream=True to only pull headers and avoid downloading video data
                with session.get(line, timeout=5, stream=True) as r:
                    if r.status_code == 200:
                        curated_channels.append(current_info)
                        curated_channels.append(line)
            except:
                continue

    # Save Curated M3U
    with open("curated-live.m3u", "w", encoding='utf-8') as f:
        f.write("\n".join(curated_channels))
    
    print(f"Done! Saved {len(curated_channels)//2} live channels.")

    # Fetch EPG
    print("Updating EPG...")
    epg_res = session.get(EPG_URL)
    with open("arabic-epg-clean.xml", "wb") as f:
        f.write(epg_res.content)

if __name__ == "__main__":
    main()
