import requests

# Configuration
M3U_URL = "https://iptv-org.github.io/iptv/languages/ara.m3u"
EPG_URL = "https://raw.githubusercontent.com/iptv-org/epg/master/arabic.xml"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def check_live(url):
    try:
        # Some streams only respond to GET, so we use stream=True to avoid downloading the whole video
        r = requests.get(url, headers=HEADERS, timeout=10, stream=True)
        return r.status_code == 200
    except:
        return False

def main():
    print("Fetching M3U...")
    response = requests.get(M3U_URL, headers=HEADERS)
    lines = response.text.splitlines()

    curated_channels = ["#EXTM3U"]
    current_info = ""

    for line in lines:
        if line.startswith("#EXTINF"):
            current_info = line
        elif line.startswith("http"):
            print(f"Checking: {line[:50]}...")
            if check_live(line):
                curated_channels.append(current_info)
                curated_channels.append(line)

    # Save Curated M3U
    with open("curated-live.m3u", "w", encoding='utf-8') as f:
        f.write("\n".join(curated_channels))
    print(f"Saved {len(curated_channels)//2} live channels.")

    # Fetch EPG
    print("Fetching EPG...")
    epg_res = requests.get(EPG_URL, headers=HEADERS)
    with open("arabic-epg-clean.xml", "wb") as f:
        f.write(epg_res.content)
    print("EPG updated.")

if __name__ == "__main__":
    main()
