import requests
import re
import os
import gzip
import xml.etree.ElementTree as ET
from datetime import datetime

# Configuration
# We use the giant file but "rip" only the Arabic parts out of it
EPG_URL = "https://epgshare01.online/epgshare01/epg_ripper_ALL_SOURCES1.xml.gz"
HEADERS = {'User-Agent': 'Mozilla/5.0'}

# We filter for any ID ending in these Arabic country codes
AR_SUFFIXES = ('.ae', '.ar', '.dz', '.eg', '.iq', '.jo', '.kw', '.lb', '.ly', 
               '.ma', '.om', '.ps', '.qa', '.sa', '.sd', '.sy', '.tn', '.ye', '.distro')

def main():
    session = requests.Session()
    print(f"Filter started: {datetime.now()}")

    try:
        print("Downloading EPG... (This takes a few minutes)")
        response = session.get(EPG_URL, stream=True, timeout=600)
        
        # Create the XML shell
        new_root = ET.Element("tv", {"generator-info-name": "Gemini-Arabic-Filter-2026"})
        kept_channel_ids = set()

        # Stream process the GZIP file to save memory
        with gzip.open(response.raw, 'rb') as gz:
            # We use iterparse to process the 1.6GB file line by line
            context = ET.iterparse(gz, events=('end',))
            
            for event, elem in context:
                # 1. Look for Channels
                if elem.tag == 'channel':
                    chan_id = elem.get('id', '')
                    
                    # Logic: Keep it if it has an Arabic country suffix OR contains "Arabic"
                    is_arabic = any(chan_id.lower().endswith(s) for s in AR_SUFFIXES)
                    
                    if is_arabic:
                        new_root.append(elem)
                        kept_channel_ids.add(chan_id)
                    else:
                        elem.clear() # Delete from memory immediately if not Arabic

                # 2. Look for Programmes
                elif elem.tag == 'programme':
                    chan_id = elem.get('channel')
                    if chan_id in kept_channel_ids:
                        new_root.append(elem)
                    else:
                        elem.clear() # Delete from memory immediately

        # Save the result
        print(f"Writing filtered EPG with {len(kept_channel_ids)} channels...")
        tree = ET.ElementTree(new_root)
        tree.write("arabic-epg-clean.xml", encoding="utf-8", xml_declaration=True)
        
        # Check size
        size_mb = os.path.getsize('arabic-epg-clean.xml') / (1024 * 1024)
        print(f"Done! Final Size: {size_mb:.2f} MB")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
