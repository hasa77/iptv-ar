import requests
import re
import gzip
import xml.etree.ElementTree as ET
import io

M3U_URL = "https://iptv-org.github.io/iptv/languages/ara.m3u"
EPG_URL = "https://epgshare01.online/epgshare01/epg_ripper_ALL_SOURCES1.xml.gz"

# 1. Target Suffixes (Must have one of these)
AR_SUFFIXES = ('.ae', '.dz', '.eg', '.iq', '.jo', '.kw', '.lb', '.ly', '.ma', 
               '.om', '.ps', '.qa', '.sa', '.sd', '.sy', '.tn', '.ye', '.me', '.ar')

# 2. Keywords to Keep (Force include if found)
AR_KEYWORDS = ('mbc', 'bein', 'osn', 'rotana', 'alkass', 'aljazeera', 'arabic', 'nilesat', 
               'sharjah', 'dubai', 'abu dhabi', 'alarabiya', 'hadath', 'cbc', 'dmc', 'on ent',
               'royal', 'art ', 'ssc ', 'syria', 'iraq', 'lebanon', 'al jadeed', 'lbc')

# 3. YOUR STRICT REJECTION LIST
EXCLUDE_WORDS = (
    'radio', 'fm', 'chaine', 'distro.tv', 'argentina', 'colombia', 'telefe', 'eltrece', 
    'kurd', 'kurdistan', 'rudaw', 'waar', 'duhok',      # Kurdish
    'mbc 1', 'mbc 1 usa',                               # Redundant (Keep only MBC 1 Masr)
    'morocco', 'maroc', 'maghreb', '2m',                # Morocco
    'tunisia', 'tunisie', 'ttv', 'hannibal',            # Tunisia
    'libya', 'libye', '218 tv',                         # Libya
    'iran', 'persian', 'farsi', 'gem tv',               # Iran
    'afghanistan', 'afghan', 'pashto', 'tolo',           # Afghanistan
    'tchad', 'chad', 'turkmenistan', 'turkmen',         # Central Africa / Central Asia
    'babyfirst',                                        # US English Kids
    'eritrea', 'eri-tv',                                # Eritrea
    'i24news'                                           # Israel-based news
)

# 4. ID Mapping for TiviMate Guide Matching
ID_MAP = {
    # Abu Dhabi Network
    'AbuDhabiSports1.ae': 'AD.Sports.1.HD.ae',
    'AbuDhabiSports2.ae': 'AD.Sports.2.HD.ae',
    'AbuDhabiEmirates.ae': 'Abu.Dhabi.HD.ae',
    'AbuDhabiTV.ae': 'Abu.Dhabi.HD.ae',
    'YasTV.ae': 'Yas.TV.HD.ae',
    # Dubai Network
    'DubaiTV.ae': 'Dubai.HD.ae',
    'DubaiSports1.ae': 'Dubai.Sports.1.HD.ae',
    'DubaiSports2.ae': 'Dubai.Sports.2.ae',
    'DubaiRacing1.ae': 'Dubai.Racing.1.HD.ae',
    'SamaDubai.ae': 'Sama.Dubai.HD.ae',
    'DubaiOne.ae': 'Dubai.One.HD.ae',
    'DubaiZaman.ae': 'Dubai.Zaman.ae',
    'NoorDubaiTV.ae': 'Noor.DubaiTV.ae',
    'OneTv.ae': 'One.Tv.ae',
    # MBC Network
    'MBC1.ae': 'MBC.1.ae',
    'MBC2.ae': 'MBC.2.ae',
    'MBCMasr.eg': 'MBC.Masr.HD.ae',
    'MBCMasr2.eg': 'MBC.Masr.2.HD.ae',
    # Rotana Network
    'RotanaCinema.sa': 'Rotana.Cinema.KSA.ae',
    'RotanaCinemaEgypt.eg': 'Rotana.Cinema.Egypt.ae',
    'RotanaDrama.sa': 'Rotana.Drama.ae',
    'RotanaClassic.sa': 'Rotana.Classic.ae',
    'RotanaKhalijia.sa': 'Rotana.Khalijia.ae',
    # Saudi & Sports Specific
    'KSA-Sports-1.sa': 'KSA.sports.1.ae',
    'KSA-Sports-2.sa': 'KSA.sports.2.HD.ae',
    'OnTimeSports1.eg': 'On.Time.Sports.HD.ae',
    'OnTimeSports2.eg': 'On.Time.Sport.2.HD.ae',
    'SharjahSports.ae': 'Sharjah.Sports.HD.ae',
    'JordanTV.jo': 'Jordan.TV.HD.ae',
    # News & International
    'AlArabiya.net': 'Al.Arabiya.HD.ae',
    'AlHadath.net': 'Al.Hadath.ae',
    'SkyNewsArabia.ae': 'Sky.News.Arabia.HD.ae',
    'BBCArabic.uk': 'BBC.Arabic.ae',
    'France24Arabic.fr': 'France.24.Arabic.ae',
    'RTArabic.ru': 'RT.Arabic.HD.ae',
    'SaudiEkhbariya.sa': 'Saudi.Al.Ekhbariya.HD.ae',
    # Religious
    'SaudiQuran.sa': 'Saudi.Quran.TV.HD.ae',
    'SaudiSunnah.sa': 'Saudi.Sunna.TV.HD.ae',
    'SharjahQuran.ae': 'Sharjah.Quran.TV.ae'
}

def clean_line(line):
    # 1. First, strip @HD/@SD from the line just for mapping purposes
    # This ensures "MBC1.ae@HD" becomes "MBC1.ae" so it matches your ID_MAP
    line = re.sub(r'(@[A-Z0-9]+)', '', line)

    # 2. Apply specific ID mapping
    for old_id, new_id in ID_MAP.items():
        if f'tvg-id="{old_id}"' in line:
            return line.replace(f'tvg-id="{old_id}"', f'tvg-id="{new_id}"')
    
    # 3. Generic fix for camelCase (e.g., DubaiZaman -> Dubai.Zaman)
    if 'tvg-id="' in line:
        line = re.sub(r'([a-z])([A-Z])', r'\1.\2', line)
    return line
  
def process_iptv():
    print("🚀 Starting Deep Scan (ID + Name Match)...")
    try:
        r = requests.get(M3U_URL, timeout=30)
        lines = r.text.splitlines()
        final_m3u = ["#EXTM3U"]
        
        def normalize(s):
            return re.sub(r'[^a-z0-9]', '', s.lower()) if s else ""

        wanted_ids = set()
        wanted_names = set() # New: Track the actual names of the channels
        
        for i in range(len(lines)):
            if lines[i].startswith("#EXTINF"):
                line_lower = lines[i].lower()
                if (any(s in line_lower for s in AR_SUFFIXES) or any(k in line_lower for k in AR_KEYWORDS)) and not any(w in line_lower for w in EXCLUDE_WORDS):
                    
                    # 1. Grab IDs
                    id_match = re.search(r'tvg-id="([^"]+)"', lines[i])
                    if id_match:
                        raw_id = id_match.group(1).split('@')[0]
                        wanted_ids.add(normalize(raw_id))

                    # 2. Grab the Channel Name (the text after the last comma)
                    name_match = lines[i].split(',')[-1].strip()
                    if name_match:
                        wanted_names.add(normalize(name_match))

                    fixed_line = clean_line(lines[i])
                    if i + 1 < len(lines) and lines[i+1].startswith("http"):
                        final_m3u.append(fixed_line)
                        final_m3u.append(lines[i+1])
        
        print(f"✅ M3U Scanned. Looking for {len(wanted_ids)} IDs and {len(wanted_names)} Name patterns.")

        print(f"📥 Downloading EPG...")
        response = requests.get(EPG_URL, stream=True, timeout=120)
        content = response.content # Load once for two passes
        
        matched_epg_ids = set()

        # PASS 1: Find Channels by ID OR Name
        with gzip.GzipFile(fileobj=io.BytesIO(content)) as g:
            context = ET.iterparse(g, events=('end',))
            for event, elem in context:
                tag_name = elem.tag.split('}')[-1]
                if tag_name == 'channel':
                    cid = elem.get('id')
                    # Check ID match
                    if normalize(cid) in wanted_ids:
                        matched_epg_ids.add(cid)
                    else:
                        # Check Display Name match
                        for dn in elem.findall('display-name'):
                            if normalize(dn.text) in wanted_names:
                                matched_epg_ids.add(cid)
                                break
                elem.clear()

        # PASS 2: Write matched data
        print(f"⚡ Saving matches to file...")
        with gzip.open("arabic-epg.xml.gz", "wb") as f_out:
            f_out.write(b'<?xml version="1.0" encoding="utf-8"?>\n<tv>\n')
            
            with gzip.GzipFile(fileobj=io.BytesIO(content)) as g:
                context = ET.iterparse(g, events=('end',))
                for event, elem in context:
                    tag_name = elem.tag.split('}')[-1]
                    if tag_name == 'channel' and elem.get('id') in matched_epg_ids:
                        f_out.write(ET.tostring(elem, encoding='utf-8'))
                    elif tag_name == 'programme' and elem.get('channel') in matched_epg_ids:
                        f_out.write(ET.tostring(elem, encoding='utf-8'))
                    elem.clear()
            f_out.write(b'</tv>')

        print(f"📊 Final Results: Found {len(matched_epg_ids)} channels.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)
      
if __name__ == "__main__":
    process_iptv()
