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

# --- THE STEADY STATE MAP (Matches TiviMate IDs) ---
ID_MAP = {
    # Iraq Fix
    'MBCIraq.iq': 'MBC.Iraq.iq',
    'MBCIraq.ae': 'MBC.Iraq.iq',
    'MBC.Iraq.iq': 'MBC.Iraq.iq',
    
    # Abu Dhabi & Dubai
    'AbuDhabiTV.ae': 'Abu.Dhabi.HD.ae',
    'AbuDhabiEmirates.ae': 'Abu.Dhabi.HD.ae',
    'AbuDhabiSports1.ae': 'AD.Sports.1.HD.ae',
    'DubaiTV.ae': 'Dubai.HD.ae',
    'DubaiOne.ae': 'Dubai.One.HD.ae',
    'SamaDubai.ae': 'Sama.Dubai.HD.ae',

    # MBC
    'MBC1.ae': 'MBC.1.ae',
    'MBC2.ae': 'MBC.2.ae',
    'MBC3.ae': 'MBC.3.ae',
    'MBC4.ae': 'MBC.4.ae',
    'MBCAction.ae': 'MBC.Action.ae',
    'MBCDrama.ae': 'MBC.Drama.ae',
    'MBCMasr.eg': 'MBC.Masr.HD.ae',
    'MBCMasr2.eg': 'MBC.Masr.2.HD.ae',

    # News & Sports
    'AlArabiya.net': 'Al.Arabiya.HD.ae',
    'SkyNewsArabia.ae': 'Sky.News.Arabia.HD.ae',
    'OnTimeSports1.eg': 'On.Time.Sports.HD.ae',
    
    # Rotana
    'RotanaCinema.sa': 'Rotana.Cinema.KSA.ae',
    'RotanaCinemaEgypt.eg': 'Rotana.Cinema.Egypt.ae'
}

def clean_id(cid):
    if not cid: return ""
    # Strip @SD, @HD tags
    base = re.sub(r'(@[A-Z0-9]+)', '', cid)
    # Standardize for comparison
    return re.sub(r'[._\-\s]', '', base).lower()

def process_iptv():
    print("🚀 Running Filtered Master Mapper...")
    REVERSE_MAP = {clean_id(k): v for k, v in ID_MAP.items()}
    
    channel_elements = []
    program_elements = []
    processed_channels = set()

    for url in EPG_SOURCES:
        print(f"📥 Processing: {url.split('/')[-1]}")
        try:
            r = requests.get(url, timeout=45)
            f = gzip.GzipFile(fileobj=io.BytesIO(r.content)) if r.content.startswith(b'\x1f\x8b') else io.BytesIO(r.content)
            
            for event, elem in ET.iterparse(f, events=('end',)):
                tag = elem.tag.split('}')[-1]
                
                if tag == 'programme':
                    source_id = elem.get('channel')
                    norm = clean_id(source_id)
                    
                    # 1. Match against our Map
                    if norm in REVERSE_MAP:
                        target_id = REVERSE_MAP[norm]
                        
                        # 2. Apply your Filters
                        # If it has a forbidden suffix AND isn't in our forced map, skip it
                        if any(source_id.endswith(s) for s in FORBIDDEN_SUFFIXES):
                            elem.clear()
                            continue
                        
                        # If it contains exclude words, skip it
                        if any(x in norm for x in EXCLUDE_WORDS):
                            elem.clear()
                            continue

                        elem.set('channel', target_id)
                        program_elements.append(ET.tostring(elem, encoding='utf-8'))
                        
                        if target_id not in processed_channels:
                            processed_channels.add(target_id)
                            chan_xml = f'<channel id="{target_id}"><display-name>{target_id}</display-name></channel>'
                            channel_elements.append(chan_xml.encode('utf-8'))
                    elem.clear()
        except Exception as e:
            print(f"  ⚠️ Error: {e}")

    if program_elements:
        with open(OUTPUT_FILE, "wb") as f_out:
            f_out.write(b'<?xml version="1.0" encoding="utf-8"?>\n<tv>\n')
            for c in channel_elements: f_out.write(c + b'\n')
            for p in program_elements: f_out.write(p + b'\n')
            f_out.write(b'</tv>')
        print(f"✅ Success! Created EPG with {len(processed_channels)} channels.")

if __name__ == "__main__":
    process_iptv()
