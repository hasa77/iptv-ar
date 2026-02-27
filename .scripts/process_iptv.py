import requests
import re

# Configuration
M3U_URL = "https://iptv-org.github.io/iptv/languages/ara.m3u"
EPG_URL = "https://iptv-org.github.io/epg/guides/ar.xml"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) VLC/3.0.18'}

# Keywords to exclude: Iran, Afghanistan, and Kurdish channels
BLACKLIST = r"Iran|Afghanistan|Persian|Farsi|Pashto|Tajikistan|Kurd|Kurdish|K24|Rudaw|NRT|Waala|Kurdsat"

def main():
    session = requests.Session()
    session.headers.update(HEADERS)

    print("Fetching and filtering M3U...")
    try:
        response = session.get(M3U_URL, timeout=15)
        lines = response.text.splitlines()
    except Exception as e:
        print(f"Error fetching M3U: {e}")
        return

    curated_channels = ["#EXTM3U"]
    current_info = ""

    for line in lines:
        if line.startswith("#EXTINF"):
            # If the channel name or info contains blacklisted keywords, we mark it to skip
            if re.search(BLACKLIST, line, re.IGNORECASE):
                current_info = None
            else:
                current_info = line
        elif line.startswith("http") and current_info:
            # Dead Stream Detection
            print(f"Checking: {line[:50]}...")
            try:
                # stream=True checks connectivity without downloading the file
                with session.get(line, timeout=5, stream=True) as r:
                    if r.status_code == 200:
                        curated_channels.append(current_info)
                        curated_channels.append(line)
            except:
                continue

    # Save Curated M3U
    with open("curated-live.m3u", "w", encoding='utf-8') as f:
        f.write("\n".join(curated_channels))
    
    print(f"Done! Saved {len(curated_channels)//2} live channels (Kurdish/Iran/Afghan removed).")

    # Fetch EPG
    print("Updating EPG...")
    epg_res = session.get(EPG_URL)
    if epg_res.status_code == 200 and b"xml" in epg_res.content[:100]:
        with open("arabic-epg-clean.xml", "wb") as f:
            f.write(epg_res.content)
        print("EPG updated successfully.")

if __name__ == "__main__":
    main()
