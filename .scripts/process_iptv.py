import requests
import re
import os
import gzip
import io
import xml.etree.ElementTree as ET
from datetime import datetime

# Configuration
M3U_URL = "https://iptv-org.github.io/iptv/languages/ara.m3u"
EPG_URL = "https://epgshare01.online/epgshare01/epg_ripper_ALL_SOURCES1.xml.gz"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/119.0.0.0'}
BLACKLIST = r"Iran|Afghanistan|Persian|Farsi|Pashto|Tajikistan|Kurd|Kurdish|K24|Rudaw|NRT|Waala|Kurdsat"

def normalize(text):
    """Helper to make matching easier: lowercase and remove symbols."""
    if not text: return ""
    return re.sub(r'[^a-z0-0]', '', text.lower())

def main():
    session = requests.Session()
    session.headers.update(HEADERS)
    print(f"Update started at: {datetime.now()}")

    # 1. Process M3U
    keep_ids = set()
    keep_names_norm = set()
    try:
        r = session.get(M3U_URL, timeout=30)
        lines = r.text.splitlines()
        curated = ["#EXTM3U"]
        current_info = None
        
        for line in lines:
            if line.startswith("#EXTINF"):
                if not re.search(BLACKLIST, line, re.IGNORECASE):
                    current_info = line
                    # Get ID
                    id_match = re.search(r'tvg-id="([^"]+)"', line)
                    if id_match: keep_ids.add(id_match.group(1))
                    # Get Name and Normalize it
                    name_match = line.split(',')[-1].strip()
                    keep_names_norm.add(normalize(name_match))
                else:
                    current_info = None
            elif line.startswith("http") and current_info:
                curated.append(current_info)
                curated.append(line)

        with open("curated-live.m3u", "w", encoding='utf-8') as f:
            f.write("\n".join(curated))
        print(f"M3U Processed. Filtered to {len(keep_ids)} potential IDs.")
    except Exception as e:
        print(f"M3U Error: {e}")

    # 2. Filter EPG
    try:
        print("Downloading EPG stream...")
        response = session.get(EPG_URL, timeout=600, stream=True)
        
        if response.status_code == 200:
            new_root = ET.Element("tv", {"generator-info-name": "Gemini-Filter"})
            # We need to track which IDs we actually found in the <channel> tags
            found_ids = set()

            with gzip.open(response.raw, 'rb') as gz:
                # Event 'start' is needed to prevent some elements from being cleared too early
                context = ET.iterparse(gz, events=('start', 'end'))
                
                for event, elem in context:
                    if event == 'end':
                        if elem.tag == 'channel':
                            chan_id = elem.get('id')
                            disp_name = elem.findtext('display-name')
                            
                            # Match if ID matches OR normalized name matches
                            if chan_id in keep_ids or normalize(disp_name) in keep_names_norm:
                                new_root.append(elem)
                                found_ids.add(chan_id)
                            else:
                                elem.clear()

                        elif elem.tag == 'programme':
                            prog_chan_id = elem.get('channel')
                            if prog_chan_id in found_ids or prog_chan_id in keep_ids:
                                new_root.append(elem)
                            else:
                                elem.clear()

            # Save the file
            tree = ET.ElementTree(new_root)
            tree.write("arabic-epg-clean.xml", encoding="utf-8", xml_declaration=True)
            print(f"EPG Saved. Size: {os.path.getsize('arabic-epg-clean.xml') / 1024 / 1024:.2f} MB")
            
    except Exception as e:
        print(f"EPG Error: {e}")

if __name__ == "__main__":
    main()
