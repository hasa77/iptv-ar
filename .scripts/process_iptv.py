import requests
import gzip
import xml.etree.ElementTree as ET
from datetime import datetime

# URLs
EPG_URL = "https://epgshare01.online/epg_ripper_ALL_SOURCES1.xml.gz"
M3U_URL = "https://iptv-org.github.io/iptv/languages/ara.m3u"

# Filters
AR_SUFFIXES = ('.ae', '.dz', '.eg', '.iq', '.jo', '.kw', '.lb', '.ly', '.ma', 
               '.om', '.ps', '.qa', '.sa', '.sd', '.sy', '.tn', '.ye', '.me', '.ar')

AR_KEYWORDS = ('mbc', 'bein', 'osn', 'rotana', 'alkass', 'aljazeera', 'arabic', 'nilesat', 
               'sharjah', 'dubai', 'abu dhabi', 'alarabiya', 'hadath', 'cbc', 'dmc', 'on ent',
               'royal', 'art ', 'ssc ', 'syria', 'iraq', 'lebanon', 'al jadeed', 'lbc')

# The "Purge" List (Kurdish + Redundant MBC)
EXCLUDE_WORDS = ('radio', 'fm', 'chaine', 'distro.tv', 'argentina', 'colombia', 'telefe', 
                 'eltrece', 'kurd', 'kurdistan', 'rudaw', 'waar', 'mbc 1', 'mbc 1 usa')

def process_m3u():
    print("Processing M3U...")
    response = requests.get(M3U_URL)
    lines = response.text.splitlines()
    filtered_m3u = ["#EXTM3U"]
    
    # Process in pairs (#EXTINF and URL)
    for i in range(len(lines)):
        if lines[i].startswith("#EXTINF"):
            info_line = lines[i]
            url_line = lines[i+1] if i+1 < len(lines) else ""
            
            # Logic: If name contains exclude words, skip it
            is_excluded = any(x in info_line.lower() for x in EXCLUDE_WORDS)
            
            # Specific logic: Ensure we keep MBC Masr while MBC 1 is excluded
            if "mbc 1" in info_line.lower() and "masr" not in info_line.lower():
                is_excluded = True

            if not is_excluded:
                filtered_m3u.append(info_line)
                filtered_m3u.append(url_line)
                
    with open("curated-live.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(filtered_m3u))
    print(f"M3U Complete. Saved curated-live.m3u")

def process_epg():
    print("Processing EPG...")
    response = requests.get(EPG_URL, stream=True, timeout=600)
    new_root = ET.Element("tv", {"generator-info-name": "Arabic-Automated-Cleaner"})
    kept_channel_ids = set()

    with gzip.open(response.raw, 'rb') as gz:
        context = ET.iterparse(gz, events=('start', 'end'))
        event, root = next(context) 
        for event, elem in context:
            if event == 'end':
                if elem.tag == 'channel':
                    cid = elem.get('id', '').lower()
                    dn = elem.find('display-name').text.lower() if elem.find('display-name') is not None else ""
                    
                    is_excluded = any(x in cid for x in EXCLUDE_WORDS) or any(x in dn for x in EXCLUDE_WORDS)
                    # Keep Masr, dump others
                    if "mbc 1" in dn and "masr" not in dn: is_excluded = True
                    
                    has_arabic = any('\u0600' <= char <= '\u06FF' for char in dn)
                    is_arabic = any(cid.endswith(s) for s in AR_SUFFIXES) or any(kw in cid for kw in AR_KEYWORDS) or has_arabic

                    if is_arabic and not is_excluded:
                        new_root.append(elem)
                        kept_channel_ids.add(elem.get('id'))
                elif elem.tag == 'programme' and elem.get('channel') in kept_channel_ids:
                    new_root.append(elem)
                if elem.tag in ['channel', 'programme']: root.clear()

    with gzip.open("arabic-epg.xml.gz", "wb") as f:
        ET.ElementTree(new_root).write(f, encoding="utf-8", xml_declaration=True)
    print("EPG Complete.")

if __name__ == "__main__":
    process_m3u()
    process_epg()
