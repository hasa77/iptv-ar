import requests
import os
import gzip
import xml.etree.ElementTree as ET
from datetime import datetime

# URLs
EPG_URL = "https://epgshare01.online/epgshare01/epg_ripper_ALL_SOURCES1.xml.gz"
M3U_URL = "https://iptv-org.github.io/iptv/languages/ara.m3u"

# Target Suffixes for Arabic EPG
AR_SUFFIXES = ('.ae', '.dz', '.eg', '.iq', '.jo', '.kw', '.lb', '.ly', '.ma', 
               '.om', '.ps', '.qa', '.sa', '.sd', '.sy', '.tn', '.ye', '.me', '.ar')

# Keywords to keep
AR_KEYWORDS = (
    'mbc', 'bein', 'osn', 'rotana', 'alkass', 'aljazeera', 'arabic', 'nilesat', 
    'sharjah', 'dubai', 'abu dhabi', 'alarabiya', 'hadath', 'cbc', 'dmc', 'on ent',
    'royal', 'art ', 'ssc ', 'syria', 'iraq', 'lebanon', 'al jadeed', 'lbc'
)

# REJECTION LIST (Added your new requests)
EXCLUDE_WORDS = (
    'radio', 'fm', 'chaine', 'distro.tv', 'argentina', 'colombia', 'telefe', 'eltrece', 
    'kurd', 'kurdistan', 'rudaw', 'waar',                # Kurdish
    'mbc 1', 'mbc 1 usa',                                # Redundant MBC
    'morocco', 'maroc', 'maghreb',                       # Morocco
    'tunisia', 'tunisie', 'ttv',                         # Tunisia
    'libya', 'libye',                                    # Libya
    'iran', 'persian', 'farsi',                          # Iran
    'afghanistan', 'afghan', 'pashto'                    # Afghanistan
)

def filter_m3u(exclude_list):
    print("Filtering M3U playlist...")
    response = requests.get(M3U_URL)
    lines = response.text.splitlines()
    filtered_m3u = ["#EXTM3U"]
    
    current_header = ""
    for line in lines:
        if line.startswith("#EXTINF"):
            # Check if line contains any excluded words
            is_junk = any(word in line.lower() for word in exclude_list)
            if not is_junk:
                current_header = line
            else:
                current_header = ""
        elif line.startswith("http") and current_header:
            filtered_m3u.append(current_header)
            filtered_m3u.append(line)
            current_header = ""
            
    with open("curated-live.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(filtered_m3u))
    print(f"M3U filtered! Saved to curated-live.m3u")

def filter_epg(exclude_list):
    print(f"Filtering EPG: {datetime.now()}")
    session = requests.Session()
    response = session.get(EPG_URL, stream=True, timeout=600)
    new_root = ET.Element("tv", {"generator-info-name": "Arabic-300-Optimizer"})
    kept_channel_ids = set()

    with gzip.open(response.raw, 'rb') as gz:
        context = ET.iterparse(gz, events=('start', 'end'))
        event, root = next(context) 

        for event, elem in context:
            if event == 'end':
                if elem.tag == 'channel':
                    cid = elem.get('id', '').lower()
                    dn_elem = elem.find('display-name')
                    display_name = dn_elem.text.lower() if (dn_elem is not None and dn_elem.text) else ""

                    has_arabic_script = any('\u0600' <= char <= '\u06FF' for char in display_name)
                    match_suffix = any(cid.endswith(s) for s in AR_SUFFIXES)
                    match_keyword = any(kw in cid for kw in AR_KEYWORDS) or any(kw in display_name for kw in AR_KEYWORDS)
                    
                    is_junk = any(x in cid for x in exclude_list) or any(x in display_name for x in exclude_list)

                    if (match_suffix or match_keyword or has_arabic_script) and not is_junk:
                        new_root.append(elem)
                        kept_channel_ids.add(elem.get('id'))
                
                elif elem.tag == 'programme':
                    if elem.get('channel') in kept_channel_ids:
                        new_root.append(elem)
                
                if elem.tag in ['channel', 'programme']:
                    root.clear()

    output_file = "arabic-epg.xml.gz"
    with gzip.open(output_file, "wb") as f:
        ET.ElementTree(new_root).write(f, encoding="utf-8", xml_declaration=True)
    print(f"EPG filtered! Found {len(kept_channel_ids)} channels.")

if __name__ == "__main__":
    # 1. Filter the M3U first
    filter_m3u(EXCLUDE_WORDS)
    # 2. Filter the EPG
    filter_epg(EXCLUDE_WORDS)
