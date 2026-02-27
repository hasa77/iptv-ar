import requests
import os
import gzip
import xml.etree.ElementTree as ET
from datetime import datetime

# Source: The massive 1.6GB global file
EPG_URL = "https://epgshare01.online/epgshare01/epg_ripper_ALL_SOURCES1.xml.gz"

# Primary Country Suffixes (Reduced to purely Middle East to avoid Argentina/Latin issues)
AR_SUFFIXES = ('.ae', '.dz', '.eg', '.iq', '.jo', '.kw', '.lb', '.ly', 
               '.ma', '.om', '.ps', '.qa', '.sa', '.sd', '.sy', '.tn', '.ye', '.me')

# High-Value Arabic Keywords
AR_KEYWORDS = ('mbc', 'bein', 'osn', 'rotana', 'alkass', 'aljazeera', 'arabic', 'nilesat', 'sharjah', 'dubai', 'abu dhabi', 'alarabiya', 'hadath')

# Strict Exclusions (Removes Radio, non-Arabic news, and junk providers)
EXCLUDE = ('.radio.', 'radio ', 'fm ', '.fm', 'chaine ', 'distro.tv', 'france 24 english', 'bbc world news', 'india', 'argentina')

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
                        
                        # Get display name for deeper matching
                        display_name = ""
                        dn_elem = elem.find('display-name')
                        if dn_elem is not None:
                            display_name = dn_elem.text.lower() if dn_elem.text else ""

                        # 1. Exclusion Logic (Filters out Radio and Junk)
                        is_excluded = any(x in cid for x in EXCLUDE) or any(x in display_name for x in EXCLUDE)
                        
                        # 2. Arabic script detection (Fallback for channels without standard IDs)
                        has_arabic_script = any('\u0600' <= char <= '\u06FF' for char in display_name)
                        
                        # 3. Match Logic
                        is_arabic = (
                            any(cid.endswith(s) for s in AR_SUFFIXES) or 
                            any(kw in cid for kw in AR_KEYWORDS) or
                            has_arabic_script
                        )
                        
                        if is_arabic and not is_excluded:
                            new_root.append(elem)
                            kept_channel_ids.add(elem.get('id'))
                    
                    elif elem.tag == 'programme':
                        if elem.get('channel') in kept_channel_ids:
                            new_root.append(elem)
                    
                    if elem.tag in ['channel', 'programme']:
                        root.clear()

        # Save as compressed .gz for TiviMate speed
        output_file = "arabic-epg.xml.gz"
        with gzip.open(output_file, "wb") as f:
            ET.ElementTree(new_root).write(f, encoding="utf-8", xml_declaration=True)
            
        print(f"Success! Filtered down to {len(kept_channel_ids)} high-quality Arabic channels.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
