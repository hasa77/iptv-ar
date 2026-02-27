import requests
import re

# CORRECTED CONFIGURATION
M3U_URL = "https://iptv-org.github.io/iptv/languages/ara.m3u"
# This is the updated, direct URL for the Arabic guide
EPG_URL = "https://iptv-org.github.io/epg/guides/ar.xml"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) VLC/3.0.18'}

# Keywords to exclude (Iran, Afghanistan, Kurdish)
BLACKLIST = r"Iran|Afghanistan|Persian|Farsi|Pashto|Tajikistan|Kurd|Kurdish|K24|Rudaw|NRT|Waala|Kurdsat"

def main():
    session = requests.Session()
    session.headers.update(HEADERS)

    print("--- Starting Playlist Update ---")
    try:
        response = session.get(M3U_URL, timeout=15)
        response.raise_for_status()
        lines = response.text.splitlines()
    except Exception as e:
        print(f"Error fetching M3U: {e}")
        return

    curated_channels = ["#EXTM3U"]
    current_info = ""

    for line in lines:
        if line.startswith("#EXTINF"):
            if re.search(BLACKLIST, line, re.IGNORECASE):
                current_info = None
            else:
                current_info = line
        elif line.startswith("http") and current_info:
            try:
                # Ping the stream to ensure it is alive
                with session.get(line, timeout=5, stream=True) as r:
                    if r.status_code == 200:
                        curated_channels.append(current_info)
                        curated_channels.append(line)
            except:
                continue

    with open("curated-live.m3u", "w", encoding='utf-8') as f:
        f.write("\n".join(curated_channels))
    print(f"Playlist saved: {len(curated_channels)//2} live channels.")

    print("--- Starting EPG Update ---")
    try:
        epg_res = session.get(EPG_URL, timeout=30)
        # GUARD: Only save if response is OK and looks like XML
        if epg_res.status_code == 200 and b"<?xml" in epg_res.content[:100]:
            with open("arabic-epg-clean.xml", "wb") as f:
                f.write(epg_res.content)
            print("EPG updated successfully.")
        else:
            print(f"EPG Error: Received status {epg_res.status_code} or invalid content.")
    except Exception as e:
        print(f"EPG Download failed: {e}")

if __name__ == "__main__":
    main()
