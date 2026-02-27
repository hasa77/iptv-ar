import requests
import re

# 1. Download and Filter M3U
m3u_url = "https://iptv-org.github.io/iptv/languages/ara.m3u"
response = requests.get(m3u_url)
lines = response.text.splitlines()

curated_channels = []
current_channel = ""

# Simple logic: Keep everything (Arabic list), but check for live status
for line in lines:
    if line.startswith("#EXTINF"):
        current_channel = line
    elif line.startswith("http"):
        # Dead Stream Detection (Status 200 check)
        try:
            r = requests.head(line, timeout=5)
            if r.status_code == 200:
                curated_channels.append(current_channel)
                curated_channels.append(line)
        except:
            continue

# Save M3U
with open("curated-live.m3u", "w") as f:
    f.write("#EXTM3U\n" + "\n".join(curated_channels))

# 2. Download EPG (Simple passthrough for now)
epg_url = "https://raw.githubusercontent.com/iptv-org/epg/master/arabic.xml"
epg_res = requests.get(epg_url)
with open("arabic-epg-clean.xml", "wb") as f:
    f.write(epg_res.content)
