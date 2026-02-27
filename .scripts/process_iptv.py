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

def main():
    session = requests.Session()
    session.headers.update(HEADERS)
    print(f"Update started at: {datetime.now()}")

    # 1. Process M3U & Identify which channels we need
    keep_ids = set()
    keep_names = set()
    try:
        print("Fetching and filtering M3U...")
        r = session.get(M3U_URL, timeout=30)
        r.raise_for_status()
        lines = r.text.splitlines()
        
        curated = ["#EXTM3U"]
        current_info = None
        
        for line in lines:
            if line.startswith("#EXTINF"):
                if not re.search(BLACKLIST, line, re.IGNORECASE):
                    current_info = line
                    # Grab ID
                    id_match = re.search(r'tvg-id="([^"]+)"', line)
                    if id_match: keep_ids.add(id_match.group(1))
                    # Grab Name (everything after the last comma)
                    name_parts = line.split(',')
                    if len(name_parts) > 1: keep_names.add(name_parts[-1].strip())
                else:
                    current_info = None
            elif line.startswith("http") and current_info:
                curated.append(current_info)
                curated.append(line)

        with open("curated-live.m3u", "w", encoding='utf-8') as f:
            f.write("\n".join(curated))
        print(f"M3U Saved. Channels: {len(curated)//2}")
    except Exception as e:
        print(f"M3U Error: {e}")

    # 2. Download, Stream, and Filter the Giant EPG
    try:
        print("Downloading massive EPG... this takes time...")
        response = session.get(EPG_URL, timeout=600, stream=True)
        
        if response.status_code == 200:
            print("Filtering 1.6GB EPG into a smaller file...")
            
            # Using gzip to decompress the stream on the fly
            with gzip.open(response.raw, 'rb') as gz:
                # We build a new smaller XML structure
                new_root = ET.Element("tv", {"generator-info-name": "Gemini-Filter"})
                
                # iterparse is memory efficient
                context = ET.iterparse(gz, events=('end',))
                
                for event, elem in context:
                    if elem.tag == 'channel':
                        channel_id = elem.get('id')
                        # Check if display-name matches any of our kept channel names
                        disp_name = elem.findtext('display-name')
                        if channel_id in keep_ids or disp_name in keep_names:
                            new_root.append(elem)
                        else:
                            elem.clear() # Free memory
                            
                    elif elem.tag == 'programme':
                        if elem.get('channel') in keep_ids:
                            new_root.append(elem)
                        else:
                            elem.clear() # Free memory
                
                # Save final tiny XML
                tree = ET.ElementTree(new_root)
                tree.write("arabic-epg-clean.xml", encoding="utf-8", xml_declaration=True)
                
                final_size = os.path.getsize("arabic-epg-clean.xml") / (1024 * 1024)
                print(f"EPG Saved. Filtered Size: {final_size:.2f} MB")
        else:
            print(f"EPG Download failed. Status: {response.status_code}")
    except Exception as e:
        print(f"EPG Filtering Error: {e}")

if __name__ == "__main__":
    main()
