import requests
import re
import gzip
import xml.etree.ElementTree as ET
import io

M3U_URL = "https://iptv-org.github.io/iptv/languages/ara.m3u"
EPG_SOURCES = [
    "https://epgshare01.online/epgshare01/epg_ripper_AE1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_AR1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_EG1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_BEIN1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_ALJAZEERA1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_ALL_SOURCES1.xml.gz"
]

# --- [DIAGNOSTIC FUNCTION] ---
def check_source_quality(epg_bytes):
    print("🔍 Diagnostic: Checking if source EPG actually contains data...")
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(epg_bytes)) as g:
            context = ET.iterparse(g, events=('end',))
            title_count = 0
            desc_count = 0
            for event, elem in context:
                tag = elem.tag.split('}')[-1]
                if tag == 'title' and elem.text and len(elem.text.strip()) > 0:
                    title_count += 1
                if tag == 'desc' and elem.text and len(elem.text.strip()) > 0:
                    desc_count += 1
                
                # If we find at least 5 populated titles, the source is likely fine
                if title_count > 5:
                    print(f"✅ Source looks GOOD. Found populated titles and descriptions.")
                    return True
                elem.clear()
        print("❌ Source Alert: Scanned EPG and found NO text inside <title> or <desc> tags.")
        return False
    except Exception as e:
        print(f"⚠️ Diagnostic failed: {e}")
        return False

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
    print("🚀 Starting Multi-Pass Fuzzy Hunt...")
    try:
        # Step 1: Define our targets
        target_ids = set(ID_MAP.values()) | set(ID_MAP.keys())
        matched_real_ids = set()
        channel_elements = []
        program_elements = []

        # Step 2: Pass 1 - Find all valid Channel IDs across ALL sources
        for url in EPG_SOURCES:
            print(f"🔍 Pass 1: Finding IDs in {url.split('/')[-1]}...")
            try:
                r = requests.get(url, timeout=60)
                # Keep the bytes in memory for Pass 2 so we don't download twice
                content = r.content 
                with gzip.GzipFile(fileobj=io.BytesIO(content)) as g:
                    for event, elem in ET.iterparse(g, events=('end',)):
                        tag = elem.tag.split('}')[-1]
                        if tag == 'channel':
                            cid = elem.get('id')
                            if any(t.lower() in cid.lower() or cid.lower() in t.lower() for t in target_ids):
                                if cid not in matched_real_ids:
                                    matched_real_ids.add(cid)
                                    channel_elements.append(ET.tostring(elem, encoding='utf-8'))
                        elem.clear()
                
                # Step 3: Pass 2 - Now that we know the IDs, grab the programs from the SAME file
                print(f"  📥 Pass 2: Extracting programs for {len(matched_real_ids)} channels...")
                with gzip.GzipFile(fileobj=io.BytesIO(content)) as g:
                    for event, elem in ET.iterparse(g, events=('end',)):
                        tag = elem.tag.split('}')[-1]
                        if tag == 'programme':
                            cid = elem.get('channel')
                            if cid in matched_real_ids:
                                # Ensure it has a title
                                title_node = elem.find('.//{*}title')
                                if title_node is not None and title_node.text:
                                    program_elements.append(ET.tostring(elem, encoding='utf-8'))
                        elem.clear()
            except Exception as e:
                print(f"  ⚠️ Error processing {url}: {e}")

        # Step 4: Final Save
        with gzip.open("arabic-epg.xml.gz", "wb") as f_out:
            f_out.write(b'<?xml version="1.0" encoding="utf-8"?>\n<tv>\n')
            for c in channel_elements: f_out.write(c + b'\n')
            for p in program_elements: f_out.write(p + b'\n')
            f_out.write(b'</tv>')

        print(f"📊 Success! Saved {len(channel_elements)} channels and {len(program_elements)} programs.")

    except Exception as e:
        print(f"❌ Critical Error: {e}")
        
if __name__ == "__main__":
    process_iptv()
