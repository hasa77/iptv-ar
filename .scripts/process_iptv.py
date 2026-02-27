import requests
import os
import gzip
import xml.etree.ElementTree as ET
from datetime import datetime

EPG_URL = "https://epgshare01.online/epgshare01/epg_ripper_ALL_SOURCES1.xml.gz"
AR_SUFFIXES = ('.ae', '.ar', '.dz', '.eg', '.iq', '.jo', '.kw', '.lb', '.ly', 
               '.ma', '.om', '.ps', '.qa', '.sa', '.sd', '.sy', '.tn', '.ye', '.me')

def main():
    print(f"Filter started: {datetime.now()}")
    session = requests.Session()
    
    try:
        response = session.get(EPG_URL, stream=True, timeout=600)
        new_root = ET.Element("tv", {"generator-info-name": "Arabic-EPG-Optimizer"})
        kept_channel_ids = set()

        with gzip.open(response.raw, 'rb') as gz:
            context = ET.iterparse(gz, events=('start', 'end'))
            event, root = next(context) 

            for event, elem in context:
                if event == 'end':
                    if elem.tag == 'channel':
                        cid = elem.get('id', '')
                        # Logic: Match Suffix OR "arabic" in ID
                        if any(cid.lower().endswith(s) for s in AR_SUFFIXES) or "arabic" in cid.lower():
                            new_root.append(elem)
                            kept_channel_ids.add(cid)
                    
                    elif elem.tag == 'programme':
                        if elem.get('channel') in kept_channel_ids:
                            new_root.append(elem)
                    
                    # CRITICAL: Keep memory flat
                    if elem.tag in ['channel', 'programme']:
                        root.clear()

        # Save compressed for TiviMate
        with gzip.open("arabic-epg.xml.gz", "wb") as f:
            ET.ElementTree(new_root).write(f, encoding="utf-8", xml_declaration=True)
            
        print(f"Success! Kept {len(kept_channel_ids)} channels.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
