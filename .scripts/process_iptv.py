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
    """Lowercase, remove symbols, and strip country suffixes like .ae, .fr, .ar"""
    if not text: return ""
    text = text.lower()
    # Remove common country suffixes at the end of IDs
    text = re.sub(r'\.(ae|ar|qa|sa|eg|jo|lb|fr|ch|cz|hu|ro|pl|pt|mn|ph|lu|be|distro)$', '', text)
    # Remove all non-alphanumeric characters
    return re.sub(r'[^a-z0-9]', '', text)

def main():
    session = requests.Session()
    session.headers.update(HEADERS)
    print(f"Update started at: {datetime.now()}")

    # 1. Process M3U
    keep_ids_norm = set()
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
                    # Store normalized ID
                    id_match = re.search(r'tvg-id="([^"]+)"', line)
                    if id_match:
                        keep_ids_norm.add(normalize(id_match.group(1)))
                    # Store normalized Name
                    name_match = line.split(',')[-1].strip()
                    keep_names_norm.add(normalize(name_match))
                else:
                    current_info = None
            elif line.startswith("http") and current_info:
                curated.append(current_info)
                curated.append(line)

        with open("curated-live.m3u", "w", encoding='utf-8') as f:
            f.write("\n".join(curated))
        print(f"M3U Processed. Looking for {len(keep_names_norm)} unique channels.")
    except Exception as e:
        print(f"M3U Error: {e}")

    # 2. Filter EPG
    try:
        print("Downloading EPG stream...")
        response = session.get(EPG_URL, timeout=600, stream=True)
        
        if response.status_code == 200:
            new_root = ET.Element("tv", {"generator-info-name": "Gemini-Filter-V2"})
            found_epg_ids = set()

            with gzip.open(response.raw, 'rb') as gz:
                context = ET.iterparse(gz, events=('end',))
                
                for event, elem in context:
                    if elem.tag == 'channel':
                        chan_id = elem.get('id')
                        chan_id_norm = normalize(chan_id)
                        disp_name = normalize(elem.findtext('display-name'))
                        
                        # MATCH LOGIC: Check normalized ID or normalized Display Name
                        if chan_id_norm in keep_ids_norm or disp_name in keep_names_norm:
                            new_root.append(elem)
                            found_epg_ids.add(chan_id)
                        else:
                            elem.clear()

                    elif elem.tag == 'programme':
                        prog_chan_id = elem.get('channel')
                        # If this programme belongs to a channel we just kept
                        if prog_chan_id in found_epg_ids:
                            new_root.append(elem)
                        else:
                            elem.clear()

            # Save the file
            tree = ET.ElementTree(new_root)
            tree.write("arabic-epg-clean.xml", encoding="utf-8", xml_declaration=True)
            
            size_mb = os.path.getsize('arabic-epg-clean.xml') / (1024 * 1024)
            print(f"EPG Saved. Filtered Size: {size_mb:.2f} MB")
            print(f"Channels with EPG data: {len(found_epg_ids)}")
            
    except Exception as e:
        print(f"EPG Error: {e}")

if __name__ == "__main__":
    main()
