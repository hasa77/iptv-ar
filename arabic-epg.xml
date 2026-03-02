import requests
import re
import gzip
import xml.etree.ElementTree as ET
import io
import os

M3U_URL = "https://iptv-org.github.io/iptv/languages/ara.m3u"
OUTPUT_FILE = "arabic-epg.xml"
EPG_SOURCES = [
    "https://epgshare01.online/epgshare01/epg_ripper_ALL_SOURCES1.xml.gz",
    "https://iptv-epg.org/files/epg-eg.xml",
    "https://iptv-epg.org/files/epg-lb.xml",
    "https://iptv-epg.org/files/epg-sa.xml",
    "https://iptv-epg.org/files/epg-ae.xml",
    "https://iptv-epg.org/files/epg-gb.xml",
    "https://iptv-epg.org/files/epg-us.xml"
]

# Suffixes that indicate the channel is definitely NOT the Arabic version
FORBIDDEN_SUFFIXES = (
    '.hk', '.kr', '.dk', '.fi', '.no', '.se', '.be', '.es', '.fr', 
    '.ca', '.ca2', '.gr', '.de', ".dk", '.cz', '.cy', '.ch', '.it', '.us', '.bb',
    '.distro', '.us_locals1', '.pluto'
)

AR_SUFFIXES = ('.ae', '.dz', '.eg', '.iq', '.jo', '.kw', '.lb', '.ly', '.ma', 
               '.om', '.ps', '.qa', '.sa', '.sd', '.sy', '.tn', '.ye', '.me', '.ar')

# Strong keywords that are almost certainly Arabic
STRONG_AR_KEYWORDS = ('mbc', 'bein', 'osn', 'rotana', 'alkass', 'aljazeera', 'nilesat', 
                      'sharjah', 'dubai', 'abu dhabi', 'alarabiya', 'hadath', 'cbc', 'dmc', 
                      'on ent', 'ssc ', 'al jadeed', 'lbc')

# Generic keywords that need a suffix to be safe
GENERIC_AR_KEYWORDS = ('arabic', 'arab', 'royal', 'art ', 'syria', 'iraq', 'lebanon')

EXCLUDE_WORDS = (
    'radio', 'fm', 'chaine', 'distro.tv', 'argentina', 'colombia', 'telefe', 'eltrece', 
    'kurd', 'kurdistan', 'rudaw', 'waar', 'duhok',      # Kurdish
	'mbc 1', 'mbc 1 usa',                               # Redundant (Keep only MBC 1 Masr)
    'morocco', 'maroc', 'maghreb', '2m',                # Morocco
    'tunisia', 'tunisie', 'ttv', 'hannibal',            # Tunisia
    'libya', 'libye', '218 tv',                         # Libya
    'iran', 'persian', 'farsi', 'gem tv', 'mbcpersia',  # Iran
    'afghanistan', 'afghan', 'pashto', 'tolo',          # Afghanistan
    'tchad', 'chad', 'turkmenistan', 'turkmen',         # Central Africa / Central Asia
    'babyfirst',                                        # US English Kids
    'eritrea', 'eri-tv',                                # Eritrea
    'i24news',                                          # Israel-based news
    'india', 'hindi', 'tamil', 'telugu', 'malayalam',   # India
    'korea', 'korean', 'kbs', 'sbs', 'tvn',             # Korea
    'zealand', 'nz', 'australia', 'canterbury',         # NZ/AU
    'turk', 'trrt', 'atv.tr', 'fox.tr',                 # Turkish
	'milb', 'ncaa', 'broncos', 'lobos', 'santa-clara',  # US Sports Junk
    'canada', 'cbc.ca', 'cbcmusic', 'halifax', 'ottawa', 'winnipeg', 'calgary', 'vancouver', 'montreal',                 # Canadian CBC
    'kmbc', 'wmbc', 'tmbc', 'mbc1usa', 'samsung',       # US MBC Look-alikes
	'milb', 'ncaa', 'broncos', 'lobos', 'santa-clara',  # US Sports
    'mlb-', 'cubs', 'guardians', 'white-sox', 'reds',   # Baseball specific
    'canada', 'cbc.ca', 'cbcmusic',                     # Canadian CBC
    'kmbc', 'wmbc', 'tmbc', 'mbc1usa', 'samsung',       # US MBC
    'español', 'wellbeing', 'xtra',             		# Spanish / Health junk
    '-cd', '-ld', 'locals1', 'global.bc',				# US local station patterns
	'engelsk',											# Denmark
)

ID_MAP = {
    # Abu Dhabi Network
    'AbuDhabiTV.ae': 'Abu.Dhabi.HD.ae',
    'AbuDhabiEmirates.ae': 'Abu.Dhabi.HD.ae',
    'AbuDhabiSports1.ae': 'AD.Sports.1.HD.ae',
    'AbuDhabiSports2.ae': 'AD.Sports.2.HD.ae',
    'YasTV.ae': 'Yas.TV.HD.ae',

    # Dubai Network
    'DubaiTV.ae': 'Dubai.HD.ae',
    'SamaDubai.ae': 'Sama.Dubai.HD.ae',
    'DubaiOne.ae': 'Dubai.One.HD.ae',
    'NoorDubaiTV.ae': 'Noor.DubaiTV.ae',
    'DubaiSports1.ae': 'Dubai.Sports.1.HD.ae',
    'DubaiSports2.ae': 'Dubai.Sports.2.ae',
    'DubaiRacing1.ae': 'Dubai.Racing.ae',
    'DubaiZaman.ae': 'Dubai.Zaman.ae',
    'OneTv.ae': 'One.Tv.ae',

    # MBC Network
    'MBC1.ae': 'MBC.1.ae',
    'MBC2.ae': 'MBC.2.ae',
    'MBC3.ae': 'MBC.3.ae',
    'MBC4.ae': 'MBC.4.ae',
    'MBCAction.ae': 'MBC.Action.ae',
    'MBCDrama.ae': 'MBC.Drama.ae',
    'MBCMasr.eg': 'MBC.Masr.HD.ae',
    'MBCMasr2.eg': 'MBC.Masr.2.HD.ae',
    'Wanasah.ae': 'Wanasah.ae',

    # Rotana Network
    'RotanaCinema.sa': 'Rotana.Cinema.KSA.ae',
    'RotanaCinemaEgypt.eg': 'Rotana.Cinema.Egypt.ae',
    'RotanaDrama.sa': 'Rotana.Drama.ae',
    'RotanaClassic.sa': 'Rotana.Classic.ae',
    'RotanaKhalijia.sa': 'Rotana.Khalijia.ae',
    'RotanaMousica.sa': 'Rotana.Mousica.ae',

    # Sports & News
    'KSA-Sports-1.sa': 'KSA.Sports.1.ae',
    'KSA-Sports-2.sa': 'KSA.Sports.2.HD.ae',
    'OnTimeSports1.eg': 'On.Time.Sports.HD.ae',
    'OnTimeSports2.eg': 'On.Time.Sport.2.HD.ae',
    'SharjahSports.ae': 'Sharjah.Sports.HD.ae',
    'AlArabiya.net': 'Al.Arabiya.HD.ae',
    'AlHadath.net': 'Al.Hadath.ae',
    'SkyNewsArabia.ae': 'Sky.News.Arabia.HD.ae',
    'JordanTV.jo': 'Jordan.TV.HD.ae',
    'BBCArabic.uk': 'BBC.Arabic.ae',
    'France24Arabic.fr': 'France.24.Arabic.ae',
    'RTArabic.ru': 'RT.Arabic.HD.ae',

    # Religious
    'SaudiQuran.sa': 'Saudi.Quran.TV.HD.ae',
    'SaudiSunnah.sa': 'Saudi.Sunna.TV.HD.ae',
    'SaudiEkhbariya.sa': 'Saudi.Al.Ekhbariya.HD.ae',
    'SharjahQuran.ae': 'Sharjah.Quran.TV.ae'
}

def normalise_id(cid):
    if not cid: return ""
    clean = re.sub(r'(@[A-Z0-9]+)', '', cid)
    return re.sub(r'[._\-\s]', '', clean).lower()

def get_allowed_ids():
    """Fetches the live M3U from the URL to find what IDs TiviMate wants."""
    allowed = set()
    # Always allow IDs that we have manually mapped
    for target_id in ID_MAP.values():
        allowed.add(target_id)
        
    print(f"🌐 Fetching live M3U from: {M3U_URL}")
    try:
        r = requests.get(M3U_URL, timeout=30)
        matches = re.findall(r'tvg-id="([^"]+)"', r.text)
        for m in matches:
            allowed.add(m)
        print(f"✅ Found {len(allowed)} potential channel IDs.")
    except Exception as e:
        print(f"⚠️ Could not fetch M3U URL: {e}")
    return allowed

def process_iptv():
    print("🚀 Starting Smart Mapper...")
    ALLOWED_IDS = get_allowed_ids()
    REVERSE_MAP = {normalise_id(k): v for k, v in ID_MAP.items()}
    
    channel_elements = []
    program_elements = []
    processed_channels = set()

    for url in EPG_SOURCES:
        file_name = url.split('/')[-1]
        print(f"📥 Processing EPG: {file_name}")
        try:
            r = requests.get(url, timeout=45)
            content = r.content
            # Handle both Gzip and raw XML
            f = gzip.GzipFile(fileobj=io.BytesIO(content)) if content.startswith(b'\x1f\x8b') else io.BytesIO(content)
            
            for event, elem in ET.iterparse(f, events=('end',)):
                tag = elem.tag.split('}')[-1]
                
                if tag == 'programme':
                    source_id = elem.get('channel')
                    norm = normalise_id(source_id)
                    final_id = None

                    # 1. Map bridge (EPG Source ID -> M3U Target ID)
                    if norm in REVERSE_MAP:
                        final_id = REVERSE_MAP[norm]
                    # 2. Direct Match (If EPG ID already matches M3U ID)
                    elif source_id in ALLOWED_IDS:
                        final_id = source_id
                    
                    if final_id:
                        # Protection: Don't exclude channels we went to the trouble of mapping
                        if norm not in REVERSE_MAP and any(x in norm for x in EXCLUDE_WORDS):
                            elem.clear()
                            continue

                        elem.set('channel', final_id)
                        program_elements.append(ET.tostring(elem, encoding='utf-8'))
                        
                        if final_id not in processed_channels:
                            processed_channels.add(final_id)
                            chan_xml = f'<channel id="{final_id}"><display-name>{final_id}</display-name></channel>'
                            channel_elements.append(chan_xml.encode('utf-8'))
                    elem.clear()
        except Exception as e:
            print(f"  ⚠️ Error processing {file_name}: {e}")

    if program_elements:
        print(f"💾 Writing {len(program_elements)} programs for {len(processed_channels)} channels...")
        with open(OUTPUT_FILE, "wb") as f_out:
            f_out.write(b'<?xml version="1.0" encoding="utf-8"?>\n<tv>\n')
            for c in channel_elements: f_out.write(c + b'\n')
            for p in program_elements: f_out.write(p + b'\n')
            f_out.write(b'</tv>')
        print(f"✅ Success! Created {OUTPUT_FILE}")

if __name__ == "__main__":
    process_iptv()
