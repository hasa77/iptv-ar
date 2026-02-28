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
    for old_id, new_id in ID_MAP.items():
        if f'tvg-id="{old_id}"' in line:
            return line.replace(f'tvg-id="{old_id}"', f'tvg-id="{new_id}"')
    if 'tvg-id="' in line:
        line = re.sub(r'([a-z])([A-Z])', r'\1.\2', line)
    return line

def process_iptv():
    print("🚀 Running High-Speed Filter & EPG Sync...")
    try:
        # 1. M3U FILTERING (Keep your existing logic here)
        r = requests.get(M3U_URL, timeout=30)
        lines = r.text.splitlines()
        final_m3u = ["#EXTM3U"]
        kept_ids = set()
        
        for i in range(len(lines)):
            if lines[i].startswith("#EXTINF"):
                line_lower = lines[i].lower()
                if (any(s in line_lower for s in AR_SUFFIXES) or any(k in line_lower for k in AR_KEYWORDS)) and not any(w in line_lower for w in EXCLUDE_WORDS):
                    fixed_line = clean_line(lines[i])
                    if i + 1 < len(lines) and lines[i+1].startswith("http"):
                        final_m3u.append(fixed_line)
                        final_m3u.append(lines[i+1])
                        id_match = re.search(r'tvg-id="([^"]+)"', fixed_line)
                        if id_match:
                            kept_ids.add(id_match.group(1))
        
        with open("curated-live.m3u", "w", encoding="utf-8") as f:
            f.write("\n".join(final_m3u))

        # 2. HIGH-SPEED EPG STREAMING
        print(f"📥 Downloading Global EPG...")
        r_epg = requests.get(EPG_URL, stream=True, timeout=120)
        r_epg.raise_for_status()

        print(f"⚡ Streaming Filter for {len(kept_ids)} channels...")
        
        # We write directly to the compressed file as we read
        with gzip.open("arabic-epg.xml.gz", "wb") as f_out:
            # Start the XML file manually
            f_out.write(b'<?xml version="1.0" encoding="utf-8"?>\n')
            f_out.write(b'<!DOCTYPE tv SYSTEM "xmltv.dtd">\n')
            f_out.write(b'<tv>\n')

            # Stream the input file
            with gzip.GzipFile(fileobj=io.BytesIO(r_epg.content)) as g:
                context = ET.iterparse(g, events=('end',))
                for event, elem in context:
                    # Only keep the tags we want that match our kept_ids
                    if elem.tag == 'channel':
                        if elem.get('id') in kept_ids:
                            f_out.write(ET.tostring(elem, encoding='utf-8'))
                    elif elem.tag == 'programme':
                        if elem.get('channel') in kept_ids:
                            f_out.write(ET.tostring(elem, encoding='utf-8'))
                    
                    # CRITICAL: Clear the element from memory after writing
                    elem.clear()
                
            f_out.write(b'</tv>')

        print(f"✅ Finished! M3U and EPG are perfectly synced.")
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)

if __name__ == "__main__":
    process_iptv()
