import requests
import os
import gzip
import xml.etree.ElementTree as ET
from datetime import datetime

EPG_URL = "https://epgshare01.online/epgshare01/epg_ripper_ALL_SOURCES1.xml.gz"

# Primary Country Suffixes
AR_SUFFIXES = ('.ae', '.ar', '.dz', '.eg', '.iq', '.jo', '.kw', '.lb', '.ly', 
               '.ma', '.om', '.ps', '.qa', '.sa', '.sd', '.sy', '.tn', '.ye', '.me')

# High-Value Arabic Keywords
AR_KEYWORDS = ('mbc', 'bein', 'osn', 'rotana', 'alkass', 'aljazeera', 'arabic', 'nilesat', 'sharjah', 'dubai', 'abu dhabi')

# Strict Exclusions
EXCLUDE = ('.radio.', 'radio ', 'france 24 english', 'bbc world news')

def main():
    print(f"Filter started: {datetime.now()}")
    session = requests.Session()
    
    try:
        response = session.get(EPG_URL, stream=True, timeout=600)
        new_root = ET.Element("tv", {"generator-info-name": "Premium-Arabic-EPG-Optimizer"})
        kept_channel_ids = set()

        with gzip.open(response.raw, 'rb') as gz:
            context = ET.iterparse(gz, events=('start', 'end'))
            event, root = next(context) 

            for event, elem in context:
                if event == 'end':
                    if elem.tag == 'channel':
                        cid = elem.get('id', '').lower()
                        # Get display name to check for "Radio" there too
                        display_name = ""
                        dn_elem = elem.find('display-name')
                        if dn_elem is not None:
                            display_name = dn_elem.text.lower() if dn_elem.text else ""

                        # 1. Check for Radio/Exclusions first
                        is_excluded = any(x in cid for x in EXCLUDE) or any(x in display_name for x in EXCLUDE)
                        
                        # 2. Match Logic
                        is_arabic = (
                            any(cid.endswith(s) for s in AR_SUFFIXES) or 
                            any(kw in cid for kw in AR_KEYWORDS) or
                            any(kw in display_name for kw in AR_KEYWORDS)
                        )
                        
                        if is_arabic and not is_excluded:
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
            
        print(f"Success! Filtered down to {len(kept_channel_ids)} high-quality channels.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
