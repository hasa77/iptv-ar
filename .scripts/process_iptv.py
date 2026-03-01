import requests
import re
import gzip
import xml.etree.ElementTree as ET
import io

M3U_URL = "https://iptv-org.github.io/iptv/languages/ara.m3u"
EPG_SOURCES = [
    "https://epgshare01.online/epgshare01/epg_ripper_ALL_SOURCES1.xml.gz",
    "https://iptv-epg.org/files/epg-eg.xml",
    "https://iptv-epg.org/files/epg-lb.xml",
    "https://iptv-epg.org/files/epg-sa.xml",
    "https://iptv-epg.org/files/epg-ae.xml",
    "https://iptv-epg.org/files/epg-gb.xml",
    "https://iptv-epg.org/files/epg-us.xml"
]

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
    'canada', 'cbc.ca', 'cbcmusic',                     # Canadian CBC
    'kmbc', 'wmbc', 'tmbc', 'mbc1usa', 'samsung',       # US MBC Look-alikes
	'milb', 'ncaa', 'broncos', 'lobos', 'santa-clara',  # US Sports
    'mlb-', 'cubs', 'guardians', 'white-sox', 'reds',   # Baseball specific
    'canada', 'cbc.ca', 'cbcmusic',                     # Canadian CBC
    'kmbc', 'wmbc', 'tmbc', 'mbc1usa', 'samsung',       # US MBC
    'español', 'wellbeing', 'xtra',             		# Spanish / Health junk
)

ID_MAP = {
    'AbuDhabiSports1.ae': 'AD.Sports.1.HD.ae',
    'AbuDhabiSports2.ae': 'AD.Sports.2.HD.ae',
    'AbuDhabiEmirates.ae': 'Abu.Dhabi.HD.ae',
    'AbuDhabiTV.ae': 'Abu.Dhabi.HD.ae',
    'YasTV.ae': 'Yas.TV.HD.ae',
    'DubaiTV.ae': 'Dubai.HD.ae',
    'DubaiSports1.ae': 'Dubai.Sports.1.HD.ae',
    'DubaiSports2.ae': 'Dubai.Sports.2.ae',
    'DubaiRacing1.ae': 'Dubai.Racing.1.HD.ae',
    'SamaDubai.ae': 'Sama.Dubai.HD.ae',
    'DubaiOne.ae': 'Dubai.One.HD.ae',
    'DubaiZaman.ae': 'Dubai.Zaman.ae',
    'NoorDubaiTV.ae': 'Noor.DubaiTV.ae',
    'OneTv.ae': 'One.Tv.ae',
    'MBC1.ae': 'MBC.1.ae',
    'MBC2.ae': 'MBC.2.ae',
    'MBCMasr.eg': 'MBC.Masr.HD.ae',
    'MBCMasr2.eg': 'MBC.Masr.2.HD.ae',
    'RotanaCinema.sa': 'Rotana.Cinema.KSA.ae',
    'RotanaCinemaEgypt.eg': 'Rotana.Cinema.Egypt.ae',
    'RotanaDrama.sa': 'Rotana.Drama.ae',
    'RotanaClassic.sa': 'Rotana.Classic.ae',
    'RotanaKhalijia.sa': 'Rotana.Khalijia.ae',
    'KSA-Sports-1.sa': 'KSA.sports.1.ae',
    'KSA-Sports-2.sa': 'KSA.sports.2.HD.ae',
    'OnTimeSports1.eg': 'On.Time.Sports.HD.ae',
    'OnTimeSports2.eg': 'On.Time.Sport.2.HD.ae',
    'SharjahSports.ae': 'Sharjah.Sports.HD.ae',
    'JordanTV.jo': 'Jordan.TV.HD.ae',
    'AlArabiya.net': 'Al.Arabiya.HD.ae',
    'AlHadath.net': 'Al.Hadath.ae',
    'SkyNewsArabia.ae': 'Sky.News.Arabia.HD.ae',
    'BBCArabic.uk': 'BBC.Arabic.ae',
    'France24Arabic.fr': 'France.24.Arabic.ae',
    'RTArabic.ru': 'RT.Arabic.HD.ae',
    'SaudiEkhbariya.sa': 'Saudi.Al.Ekhbariya.HD.ae',
    'SaudiQuran.sa': 'Saudi.Quran.TV.HD.ae',
    'SaudiSunnah.sa': 'Saudi.Sunna.TV.HD.ae',
    'SharjahQuran.ae': 'Sharjah.Quran.TV.ae'
}

def normalise_id(cid):
    if not cid: return ""
    clean = re.sub(r'(@[A-Z0-9]+)', '', cid)
    return re.sub(r'[._\-\s]', '', clean).lower()

def process_iptv():
    print("🚀 Running Smart Filter (Cleaning Data for TiviMate)...")
    REVERSE_MAP = {normalise_id(k): v for k, v in ID_MAP.items()}
    channel_elements = []
    program_elements = []
    global_added_channels = set()

    for url in EPG_SOURCES:
        file_name = url.split('/')[-1]
        print(f"📥 Processing {file_name}...")
        try:
            r = requests.get(url, stream=True, timeout=120)
            content = r.content
            f = gzip.GzipFile(fileobj=io.BytesIO(content)) if content.startswith(b'\x1f\x8b') else io.BytesIO(content)
            
            context = ET.iterparse(f, events=('start', 'end'))
            for event, elem in context:
                tag = elem.tag.split('}')[-1]
                
                if event == 'end' and tag == 'programme':
                    chan_id = elem.get('channel')
                    if chan_id:
                        norm_id = normalise_id(chan_id)
                        
                        if any(ex in norm_id for ex in EXCLUDE_WORDS) or '.tr' in norm_id:
                            elem.clear()
                            continue

                        final_id = None
                        if norm_id in REVERSE_MAP:
                            final_id = REVERSE_MAP[norm_id]
                        elif any(k in norm_id for k in STRONG_AR_KEYWORDS):
                            final_id = chan_id
                        elif any(k in norm_id for k in GENERIC_AR_KEYWORDS):
                            if any(suffix in norm_id for suffix in AR_SUFFIXES):
                                final_id = chan_id

                        if final_id:
                            is_forbidden_lang = False
                            has_valid_title = False
                            
                            for child in elem:
                                if child.tag.endswith('title'):
                                    lang = child.get('lang', '').lower()
                                    if lang in ['tr', 'tur', 'per', 'fas', 'kur', 'hi', 'kor']:
                                        is_forbidden_lang = True
                                        break
                                    # Ensure the title actually has text and isn't just <title />
                                    if child.text and len(child.text.strip()) > 0:
                                        has_valid_title = True
                            
                            if not is_forbidden_lang and has_valid_title:
                                elem.set('channel', final_id)
                                program_elements.append(ET.tostring(elem, encoding='utf-8'))
                                if final_id not in global_added_channels:
                                    global_added_channels.add(final_id)
                                    chan_xml = f'<channel id="{final_id}"><display-name>{final_id}</display-name></channel>'
                                    channel_elements.append(chan_xml.encode('utf-8'))
                    elem.clear()
        except Exception as e:
            print(f"  ⚠️ Skipping {file_name}: {e}")

    if program_elements:
        # Saving as plain XML for maximum TiviMate compatibility
        with open("arabic-epg.xml", "wb") as f_out:
            f_out.write(b'<?xml version="1.0" encoding="utf-8"?>\n<tv>\n')
            for c in channel_elements: f_out.write(c + b'\n')
            for p in program_elements: f_out.write(p + b'\n')
            f_out.write(b'</tv>')
        print(f"✅ Success! Saved {len(program_elements)} programs for {len(global_added_channels)} channels.")

if __name__ == "__main__":
    process_iptv()
