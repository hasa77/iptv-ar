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

# Manual mapping for common mismatches (M3U Name -> EPG ID fragment)
MANUAL_MAP = {
    "mbc1": "mbc1", "mbc2": "mbc2", "mbc3": "mbc3", "mbc4": "mbc4",
    "alarabiya": "arabiya", "aljazeera": "jazeera", "rotana": "rotana",
    "bein": "bein", "adnatgeo": "natgeo", "osn": "osn"
}

def aggressive_normalize(text):
    if not text: return ""
    text = text.lower()
    # Remove Arabic diacritics/tashkeel to standardize
    text = re.sub(r'[\u064B-\u0652]', '', text)
    # Remove technical noise
    text = re.sub(r'\s+(hd|sd|4k|fhd|hevc|vip|ar|en|fr|uae|arabic|tv)\b', '', text)
    # Strip non-alphanumeric (keeps Arabic letters and English)
    return re.sub(r'[^\w]', '', text)

def main():
    session = requests.Session()
    session.headers.update(HEADERS)
    print(f"Update started at: {datetime.now()}")

    # 1. Process M3U
    m3u_channels = {} 
    try:
        r = session.get(M3U_URL, timeout=30)
        lines = r.text.splitlines()
        current_info = None
        
        for line in lines:
            if line.startswith("#EXTINF"):
                if not re.search(BLACKLIST, line, re.IGNORECASE):
                    name = line.split(',')[-1].strip()
                    norm_name = aggressive_normalize(name)
                    # Extract original tvg-id if exists
                    id_match = re.search(r'tvg-id="([^"]+)"', line)
                    orig_id = id_match.group(1) if id_match else ""
                    current_info = (line, norm_name, orig_id)
                else:
                    current_info = None
            elif line.startswith("http") and current_info:
                info_line, norm_name, orig_id = current_info
                m3u_channels[norm_name] = {"info": info_line, "url": line, "orig_id": orig_id}
        
        print(f"M3U Processed: {len(m3u_channels)} channels ready for matching.")
    except Exception as e:
        print(f"M3U Error: {e}")

    # 2. Filter EPG
    try:
        print("Downloading and Filtering EPG (Deep Scan)...")
        response = session.get(EPG_URL, timeout=600, stream=True)
        
        if response.status_code == 200:
            new_root = ET.Element("tv", {"generator-info-name": "Gemini-Bilingual-V3"})
            found_epg_ids = set()
            norm_to_epg_id = {}

            with gzip.open(response.raw, 'rb') as gz:
                context = ET.iterparse(gz, events=('end',))
                
                for event, elem in context:
                    if elem.tag == 'channel':
                        epg_id = elem.get('id')
                        epg_id_norm = aggressive_normalize(epg_id)
                        
                        # Get all possible names for this channel in EPG
                        epg_names = [aggressive_normalize(n.text) for n in elem.findall('display-name')]
                        
                        match_found = False
                        # Strategy A: Match normalized names
                        for ename in epg_names:
                            if ename in m3u_channels:
                                match_found = True
                                norm_to_epg_id[ename] = epg_id
                                break
                        
                        # Strategy B: Manual Mapping/ID containment
                        if not match_found:
                            for m_key, m_val in MANUAL_MAP.items():
                                if m_key in epg_id_norm and any(m_key in name for name in m3u_channels.keys()):
                                    match_found = True
                                    break

                        if match_found:
                            new_root.append(elem)
                            found_epg_ids.add(epg_id)
                        else:
                            elem.clear()

                    elif elem.tag == 'programme':
                        prog_chan_id = elem.get('channel')
                        if prog_chan_id in found_epg_ids:
                            new_root.append(elem)
                        else:
                            elem.clear()

            # 3. Final M3U Rewrite (Critical for TiviMate)
            curated_m3u = ["#EXTM3U"]
            for norm_name, data in m3u_channels.items():
                info = data['info']
                # Link M3U to the EPG ID we found
                if norm_name in norm_to_epg_id:
                    real_id = norm_to_epg_id[norm_name]
                    info = re.sub(r'tvg-id="[^"]*"', f'tvg-id="{real_id}"', info)
                
                curated_m3u.append(info)
                curated_m3u.append(data['url'])

            with open("curated-live.m3u", "w", encoding='utf-8') as f:
                f.write("\n".join(curated_m3u))

            tree = ET.ElementTree(new_root)
            tree.write("arabic-epg-clean.xml", encoding="utf-8", xml_declaration=True)
            print(f"Success! Channels Matched: {len(found_epg_ids)}")
            
    except Exception as e:
        print(f"EPG Error: {e}")

if __name__ == "__main__":
    main()
