import requests
import os
import gzip
import xml.etree.ElementTree as ET
from datetime import datetime

# Source: The massive global file
EPG_URL = "https://epgshare01.online/epgshare01/epg_ripper_ALL_SOURCES1.xml.gz"

# Primary Country Suffixes
AR_SUFFIXES = ('.ae', '.ar', '.dz', '.eg', '.iq', '.jo', '.kw', '.lb', '.ly', 
               '.ma', '.om', '.ps', '.qa', '.sa', '.sd', '.sy', '.tn', '.ye', '.me')

# High-Value Arabic Keywords (Matches even without country codes)
AR_KEYWORDS = ('mbc', 'bein', 'osn', 'rotana', 'alkass', 'aljazeera', 'arabic', 'nilesat')

def main():
    print(f"Filter started: {datetime.now()}")
    session = requests.Session()
    
    try:
        response = session.get(EPG_URL, stream=True, timeout=600)
        # Create a cleaner generator name
        new_root = ET.Element("tv", {"generator-info-name": "Custom-Arabic-EPG-2026"})
        kept_channel_ids = set()

        with gzip.open(response.raw, 'rb') as gz:
            context = ET.iterparse(gz, events=('start', 'end'))
            event, root = next(context) 

            for event, elem in context:
                if event == 'end':
                    if elem.tag == 'channel':
                        cid = elem.get('id', '').lower()
                        
                        # Logic: Match Suffix OR Keyword
                        is_arabic = (
                            any(cid.endswith(s) for s in AR_SUFFIXES) or 
                            any(kw in cid for kw in AR_KEYWORDS)
                        )
                        
                        if is_arabic:
                            new_root.append(elem)
                            kept_channel_ids.add(elem.get('id')) # Keep original casing
                    
                    elif elem.tag == 'programme':
                        if elem.get('channel') in kept_channel_ids:
                            new_root.append(elem)
                    
                    # Memory Management: Clear processed elements from the source tree
                    if elem.tag in ['channel', 'programme']:
                        root.clear()

        # Save compressed for TiviMate - it's faster and smaller
        output_file = "arabic-epg.xml.gz"
        with gzip.open(output_file, "wb") as f:
            ET.ElementTree(new_root).write(f, encoding="utf-8", xml_declaration=True)
            
        print(f"Success! Filtered down to {len(kept_channel_ids)} quality Arabic channels.")

    except Exception as e:
        print(f"Error during processing: {e}")

if __name__ == "__main__":
    main()
