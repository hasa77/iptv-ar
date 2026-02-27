import requests
import os
import gzip
import xml.etree.ElementTree as ET
from datetime import datetime

EPG_URL = "https://epgshare01.online/epgshare01/epg_ripper_ALL_SOURCES1.xml.gz"

# Expanded Suffixes (Restored .ar but added safety)
AR_SUFFIXES = ('.ae', '.dz', '.eg', '.iq', '.jo', '.kw', '.lb', '.ly', '.ma', 
               '.om', '.ps', '.qa', '.sa', '.sd', '.sy', '.tn', '.ye', '.me', '.ar')

# Massive Keyword List (To match your 300 M3U channels)
AR_KEYWORDS = (
    'mbc', 'bein', 'osn', 'rotana', 'alkass', 'aljazeera', 'arabic', 'nilesat', 
    'sharjah', 'dubai', 'abu dhabi', 'alarabiya', 'hadath', 'cbc', 'dmc', 'on ent',
    'royal', 'art ', 'ssc ', 'syria', 'iraq', 'lebanon', 'al jadeed', 'lbc'
)

# Protect against the "Argentina Leak" and Radio
EXCLUDE_WORDS = ('radio', 'fm', 'chaine', 'distro.tv', 'argentina', 'colombia', 'telefe', 'eltrece')

def main():
    print(f"Filter started: {datetime.now()}")
    session = requests.Session()
    
    try:
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
                        display_name = ""
                        dn_elem = elem.find('display-name')
                        if dn_elem is not None:
                            display_name = dn_elem.text.lower() if dn_elem.text else ""

                        # Check for Arabic Script
                        has_arabic_script = any('\u0600' <= char <= '\u06FF' for char in display_name)
                        
                        # Match Logic
                        match_suffix = any(cid.endswith(s) for s in AR_SUFFIXES)
                        match_keyword = any(kw in cid for kw in AR_KEYWORDS) or any(kw in display_name for kw in AR_KEYWORDS)
                        
                        # Exclusion Logic
                        is_junk = any(x in cid for x in EXCLUDE_WORDS) or any(x in display_name for x in EXCLUDE_WORDS)

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
            
        print(f"Success! Found {len(kept_channel_ids)} channels. This should better match your M3U.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
