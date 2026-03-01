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

# Manual fixes for common mismatches
ID_MAP = {
    'mbcmasr': 'MBC.Masr.HD.ae',
    'mbcmasr2': 'MBC.Masr.2.HD.ae',
    'mbcmasrtwo': 'MBC.Masr.2.HD.ae',
    'abudhabitv': 'Abu.Dhabi.HD.ae',
    'abudhabiemirates': 'Abu.Dhabi.HD.ae',
    'adsports1': 'AD.Sports.1.HD.ae',
    'adsports2': 'AD.Sports.2.HD.ae',
    'ontimesport1': 'On.Time.Sports.HD.ae',
    'ontimesports1': 'On.Time.Sports.HD.ae',
    'alarabiya': 'Al.Arabiya.HD.ae',
    'alarabiyahd': 'Al.Arabiya.HD.ae',
    'skynewsarabia': 'Sky.News.Arabia.HD.ae',
    'rotanacinemaegypt': 'Rotana.Cinema.Egypt.ae',
    'rotanacinema': 'Rotana.Cinema.KSA.ae'
}

def normalise(text):
    """Removes all non-alphanumeric chars and makes lowercase for comparison."""
    if not text: return ""
    # Remove things like ".ae", "HD", "TV", and special characters
    text = re.sub(r'(@[A-Z0-9]+)', '', text)
    text = text.lower().replace('hd', '').replace('tv', '').replace('.ae', '').replace('.eg', '')
    return re.sub(r'[^a-z0-9]', '', text)

def get_m3u_data():
    """Fetches the M3U and builds a dictionary of {CleanName: OriginalID}."""
    m3u_map = {}
    print(f"🌐 Fetching live M3U from: {M3U_URL}")
    try:
        r = requests.get(M3U_URL, timeout=30)
        # Find tvg-id and the channel name from the #EXTINF line
        matches = re.findall(r'tvg-id="([^"]+)".*?,(.*)', r.text)
        for tvg_id, channel_name in matches:
            # Map both the ID and the Name to the target ID
            m3u_map[normalise(tvg_id)] = tvg_id
            m3u_map[normalise(channel_name)] = tvg_id
    except Exception as e:
        print(f"⚠️ M3U Fetch Error: {e}")
    return m3u_map

def process_iptv():
    print("🚀 Starting Smart Auto-Mapper...")
    
    # This map contains clean versions of every ID and Name in your M3U
    SMART_MAP = get_m3u_data()
    
    # Merge our manual ID_MAP into the smart map
    for key, val in ID_MAP.items():
        SMART_MAP[normalise(key)] = val

    channel_elements = []
    program_elements = []
    processed_channels = set()

    for url in EPG_SOURCES:
        file_name = url.split('/')[-1]
        print(f"📥 Processing: {file_name}")
        try:
            r = requests.get(url, timeout=45)
            content = r.content
            f = gzip.GzipFile(fileobj=io.BytesIO(content)) if content.startswith(b'\x1f\x8b') else io.BytesIO(content)
            
            for event, elem in ET.iterparse(f, events=('end',)):
                tag = elem.tag.split('}')[-1]
                
                if tag == 'programme':
                    source_id = elem.get('channel')
                    norm_source = normalise(source_id)
                    final_id = None

                    # STEP 1 & 2 & 3: Look for match in our Smart Map
                    if norm_source in SMART_MAP:
                        final_id = SMART_MAP[norm_source]
                    
                    if final_id:
                        # Skip if it's junk (like Radio)
                        if any(x in norm_source for x in EXCLUDE_WORDS):
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
            print(f"  ⚠️ Error: {e}")

    if program_elements:
        print(f"💾 Saving {len(program_elements)} programs for {len(processed_channels)} channels...")
        with open(OUTPUT_FILE, "wb") as f_out:
            f_out.write(b'<?xml version="1.0" encoding="utf-8"?>\n<tv>\n')
            for c in channel_elements: f_out.write(c + b'\n')
            for p in program_elements: f_out.write(p + b'\n')
            f_out.write(b'</tv>')
        print(f"✅ Created EPG with {len(processed_channels)} channels matched!")

if __name__ == "__main__":
    process_iptv()
