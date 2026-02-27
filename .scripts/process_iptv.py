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
AR_KEYWORDS = ('mbc', 'bein', 'osn', 'rotana', 'alkass', 'aljazeera', 'arabic', 'nilesat', 
               'sharjah', 'dubai', 'abu dhabi', 'alarabiya', 'hadath', 'cbc', 'dmc', 'on ent',
               'royal', 'art ', 'ssc ', 'syria', 'iraq', 'lebanon', 'al jadeed', 'lbc')

# STRICT REJECTION LIST (Now includes specific countries and redundant MBC)
EXCLUDE_WORDS = (
    'radio', 'fm', 'chaine', 'distro.tv', 'argentina', 'colombia', 'telefe', 'eltrece', 
    'kurd', 'kurdistan', 'rudaw', 'waar', 'duhok', 
    'rojava', 'sterk', 'ronahi',                       # Added specific Kurdish channel names
    'mbc 1', 'mbc 1 usa',                               # Redundant (Keep only MBC 1 Masr)
    'morocco', 'maroc', 'maghreb', '2m',                # Morocco
    'tunisia', 'tunisie', 'ttv', 'hannibal',            # Tunisia
    'libya', 'libye', '218 tv',                         # Libya
    'iran', 'persian', 'farsi', 'gem tv',               # Iran
    'afghanistan', 'afghan', 'pashto', 'tolo'           # Afghanistan
    'babyfirst',                                        # US English Kids
    'eritrea', 'eri-tv',                                # Eritrea
    'i24news'                                           # Israel-based news
    'tchad', 'chad', 'turkmenistan', 'turkmen'          # Chad and Turkmenistan
)

def filter_m3u():
    print("Downloading and filtering M3U...")
    try:
        response = requests.get(M3U_URL, timeout=30)
        lines = response.text.splitlines()
        filtered_m3u = ["#EXTM3U"]
        
        # We use a loop to check the #EXTINF line and the URL line following it
        for i in range(len(lines)):
            if lines[i].startswith("#EXTINF"):
                line_content = lines[i].lower()
                # Check for any excluded words
                if not any(word in line_content for word in EXCLUDE_WORDS):
                    # If clean, add this line and the next line (the URL)
                    if i + 1 < len(lines) and lines[i+1].startswith("http"):
                        filtered_m3u.append(lines[i])
                        filtered_m3u.append(lines[i+1])
        
        with open("curated-live.m3u", "w", encoding="utf-8") as f:
            f.write("\n".join(filtered_m3u))
        print(f"M3U Update Success. Saved {len(filtered_m3u)//2} channels.")
    except Exception as e:
        print(f"M3U Error: {e}")

def filter_epg():
    print(f"Filtering EPG: {datetime.now()}")
    try:
        response = requests.get(EPG_URL, stream=True, timeout=600)
        new_root = ET.Element("tv", {"generator-info-name": "Arabic-300-Final-v2"})
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

                        # Logic checks
                        has_arabic = any('\u0600' <= char <= '\u06FF' for char in display_name)
                        is_match = any(cid.endswith(s) for s in AR_SUFFIXES) or any(kw in cid or kw in display_name for kw in AR_KEYWORDS)
                        is_junk = any(x in cid or x in display_name for x in EXCLUDE_WORDS)

                        if (has_arabic or is_match) and not is_junk:
                            new_root.append(elem)
                            kept_channel_ids.add(elem.get('id'))
                    
                    elif elem.tag == 'programme':
                        if elem.get('channel') in kept_channel_ids:
                            new_root.append(elem)
                    
                    if elem.tag in ['channel', 'programme']:
                        root.clear()

        with gzip.open("arabic-epg.xml.gz", "wb") as f:
            ET.ElementTree(new_root).write(f, encoding="utf-8", xml_declaration=True)
        print(f"EPG Update Success. Found {len(kept_channel_ids)} channel guides.")
    except Exception as e:
        print(f"EPG Error: {e}")

if __name__ == "__main__":
    filter_m3u()
    filter_epg()
