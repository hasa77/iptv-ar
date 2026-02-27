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

def aggressive_normalize(text):
    """Deep cleaning: remove HD, SD, 4K, symbols, and country codes."""
    if not text: return ""
    text = text.lower()
    # Remove common technical suffixes and country tags
    text = re.sub(r'\s+(hd|sd|4k|fhd|hevc|vip|ar|en|fr|uae|arabic)\b', '', text)
    # Remove everything that isn't a letter or a number
    return re.sub(r'[^a-z0-9]', '', text)

def main():
    session = requests.Session()
    session.headers.update(HEADERS)
    print(f"Update started at: {datetime.now()}")

    # 1. Process M3U: Build a dictionary of Name -> Original Info
    m3u_channels = {} # Key: normalized name, Value: { 'info': line, 'url': line }
    try:
        r = session.get(M3U_URL, timeout=30)
        lines = r.text.splitlines()
        current_info = None
        
        for line in lines:
            if line.startswith("#EXTINF"):
                if not re.search(BLACKLIST, line, re.IGNORECASE):
                    name = line.split(',')[-1].strip()
                    norm_name = aggressive_normalize(name)
                    current_info = (line, norm_name)
                else:
                    current_info = None
            elif line.startswith("http") and current_info:
                info_line, norm_name = current_info
                m3u_channels[norm_name] = {"info": info_line, "url": line}
        
        print(f"M3U Processed: {len(m3u_channels)} unique channels found.")
    except Exception as e:
        print(f"M3U Error: {e}")

    # 2. Filter EPG
    try:
        print("Downloading and Filtering 1.6GB EPG (Aggressive Mode)...")
        response = session.get(EPG_URL, timeout=600, stream=True)
        
        if response.status_code == 200:
            new_root = ET.Element("tv", {"generator-info-name": "Gemini-MaxMatch-2026"})
            found_epg_ids = set()
            normalized_to_real_id = {} # Map norm_name -> EPG_ID for programme matching

            with gzip.open(response.raw, 'rb') as gz:
                context = ET.iterparse(gz, events=('end',))
                
                for event, elem in context:
                    if elem.tag == 'channel':
                        epg_id = elem.get('id')
                        # Check every display-name tag (some channels have multiple)
                        names = [n.text for n in elem.findall('display-name')]
                        
                        is_match = False
                        for n in names:
                            norm_n = aggressive_normalize(n)
                            if norm_n in m3u_channels:
                                is_match = True
                                normalized_to_real_id[norm_n] = epg_id
                                break
                        
                        if is_match:
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

            # 3. Final M3U Rewrite (Optional: Fixes tvg-id to match EPG exactly)
            curated_m3u = ["#EXTM3U"]
            for norm_name, data in m3u_channels.items():
                info = data['info']
                # If we found this channel in EPG, update its tvg-id in the M3U
                if norm_name in normalized_to_real_id:
                    real_id = normalized_to_real_id[norm_name]
                    info = re.sub(r'tvg-id="[^"]*"', f'tvg-id="{real_id}"', info)
                
                curated_m3u.append(info)
                curated_m3u.append(data['url'])

            with open("curated-live.m3u", "w", encoding='utf-8') as f:
                f.write("\n".join(curated_m3u))

            # Save XML
            tree = ET.ElementTree(new_root)
            tree.write("arabic-epg-clean.xml", encoding="utf-8", xml_declaration=True)
            
            size_mb = os.path.getsize('arabic-epg-clean.xml') / (1024 * 1024)
            print(f"Success! EPG Size: {size_mb:.2f} MB")
            print(f"Channels Matched: {len(found_epg_ids)}")
            
    except Exception as e:
        print(f"EPG Error: {e}")

if __name__ == "__main__":
    main()
