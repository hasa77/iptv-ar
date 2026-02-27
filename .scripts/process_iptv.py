import requests
import re
import os
import gzip
import xml.etree.ElementTree as ET
from datetime import datetime

# Configuration
M3U_URL = "https://iptv-org.github.io/iptv/languages/ara.m3u"
# Using the 1.6GB file as a secondary source, and adding the dedicated Arabic one if possible
EPG_URL = "https://epgshare01.online/epgshare01/epg_ripper_ALL_SOURCES1.xml.gz"

def clean_name(text):
    """Normalize text for better matching"""
    if not text: return ""
    text = text.lower()
    # Remove HD, SD, Arabic, and country codes in brackets
    text = re.sub(r'\(.*?\)|\[.*?\]|hd|sd|fhd|4k|arabic|uae', '', text)
    return re.sub(r'[^a-z0-9]', '', text)

def main():
    session = requests.Session()
    print(f"Sync started: {datetime.now()}")

    # 1. Map M3U Channels
    m3u_targets = {}
    r = session.get(M3U_URL)
    lines = r.text.splitlines()
    current_info = None
    for line in lines:
        if line.startswith("#EXTINF"):
            name = line.split(',')[-1].strip()
            norm = clean_name(name)
            current_info = {"line": line, "norm": norm, "name": name}
        elif line.startswith("http") and current_info:
            m3u_targets[current_info['norm']] = current_info
            m3u_targets[current_info['norm']]['url'] = line
            current_info = None

    # 2. Process EPG
    print("Processing 1.6GB EPG...")
    response = session.get(EPG_URL, stream=True)
    
    new_root = ET.Element("tv", {"generator": "Gemini-Final-V4"})
    matched_epg_ids = set()
    final_m3u = ["#EXTM3U"]
    
    # Track which M3U channels actually got an EPG match
    m3u_matched_norms = set()

    with gzip.open(response.raw, 'rb') as gz:
        context = ET.iterparse(gz, events=('end',))
        for event, elem in context:
            if elem.tag == 'channel':
                epg_id = elem.get('id')
                # Check all display names in EPG
                found_match = False
                for dn in elem.findall('display-name'):
                    epg_norm = clean_name(dn.text)
                    if epg_norm in m3u_targets:
                        found_match = True
                        m3u_matched_norms.add(epg_norm)
                        # Link this EPG ID to our M3U target
                        m3u_targets[epg_norm]['epg_id'] = epg_id
                        break
                
                if found_match:
                    new_root.append(elem)
                    matched_epg_ids.add(epg_id)
                else:
                    elem.clear()

            elif elem.tag == 'programme':
                chan_id = elem.get('channel')
                if chan_id in matched_epg_ids:
                    new_root.append(elem)
                else:
                    elem.clear()

    # 3. Build Final M3U (Injecting the correct tvg-id)
    for norm, data in m3u_targets.items():
        info_line = data['line']
        if 'epg_id' in data:
            # Replace existing tvg-id with the one we found in the big EPG
            if 'tvg-id="' in info_line:
                info_line = re.sub(r'tvg-id="[^"]*"', f'tvg-id="{data["epg_id"]}"', info_line)
            else:
                info_line = info_line.replace('#EXTINF:-1 ', f'#EXTINF:-1 tvg-id="{data["epg_id"]}" ')
        
        final_m3u.append(info_line)
        final_m3u.append(data['url'])

    # Save Results
    with open("curated-live.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(final_m3u))
    
    tree = ET.ElementTree(new_root)
    tree.write("arabic-epg-clean.xml", encoding="utf-8", xml_declaration=True)
    
    print(f"Matched {len(m3u_matched_norms)} out of {len(m3u_targets)} M3U channels.")

if __name__ == "__main__":
    main()
