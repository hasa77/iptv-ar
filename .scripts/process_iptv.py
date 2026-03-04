import requests
import re
import gzip
import xml.etree.ElementTree as ET
import io
import os
import json
from collections import defaultdict

M3U_URL = "https://iptv-org.github.io/iptv/languages/ara.m3u"
M3U_OUTPUT = "curated-live.m3u"
EPG_OUTPUT = "arabic-epg.xml"
EPG_SOURCES = [
    "https://epgshare01.online/epgshare01/epg_ripper_ALL_SOURCES1.xml.gz",
    #Combined Egypt, Lebanon, Saudi, UAE, GB, USA
    "https://iptv-epg.org/files/epg-meyqso.xml"
]

# Paths
LOGO_MAP_PATH = os.path.join('resources', 'logo_map.json')
EXCLUDE_WORDS_PATH = os.path.join('resources', 'exclude_words.txt')

# Path to logo map JSON
def load_logo_map():
    """Loads the logo map from root/resources/logo_map.json"""
    if not os.path.exists(LOGO_MAP_PATH):
        print(f"Warning: {LOGO_MAP_PATH} not found. Logo mapping will be disabled.")
        return {}
    try:
        with open(LOGO_MAP_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading logo map JSON: {e}")
        return {}

def load_exclude_words(file_path=EXCLUDE_WORDS_PATH):
    """Loads exclusion keywords from root/resources/exclude_words.txt"""
    if not os.path.exists(file_path):
        print(f"Warning: {file_path} not found. Using empty exclusion list.")
        return []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        # Reads lines, strips whitespace, ignores empty lines and comments
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

# Load external resources
LOGO_MAP = load_logo_map()
EXCLUDE_WORDS = load_exclude_words()

# ── Explicit bridges: M3U tvg-id  →  EPG channel id ──────────────────────────
# Left side  = exact tvg-id value as it appears in the iptv-org M3U
# Right side = exact channel id as it appears in the EPG source
ID_MAP = {

    'Al.Arabiya.Programs': 'AlArabiya.net',
    'Al.Araby.TV2': 'Al.Araby.2.HD.ae',
    'Al.Iraqia.News': 'Al.Iraqiya.HD.ae',
    'Al.Maaref.TV': 'AlMaaref.bh',
    
    # Abu Dhabi
    'Abu.Dhabi.HD.ae':          'AbuDhabiTV.ae',
    'AD.Sports.1.HD.ae':        'AbuDhabiSports1.ae',
    'AD.Sports.2.HD.ae':        'AbuDhabiSports2.ae',
    'Yas.TV.HD.ae':             'YasTV.ae',

    # Dubai
    'Dubai.HD.ae':              'DubaiTV.ae',
    'Sama.Dubai.HD.ae':         'SamaDubai.ae',
    'Dubai.One.HD.ae':          'DubaiOne.ae',
    'Noor.DubaiTV.ae':          'NoorDubaiTV.ae',
    'Dubai.Sports.1.HD.ae':     'DubaiSports1.ae',
    'Dubai.Sports.2.ae':        'DubaiSports2.ae',
    'Dubai.Racing.ae':          'DubaiRacing1.ae',
    'Dubai.Zaman.ae':           'DubaiZaman.ae',
    'One.Tv.ae':                'OneTv.ae',

    # MBC
    'MBC.1.ae':                 'MBC1.ae',
    'MBC.2.ae':                 'MBC2.ae',
    'MBC.3.ae':                 'MBC3.ae',
    'MBC.4.ae':                 'MBC4.ae',
    'MBC.Action.ae':            'MBCAction.ae',
    'MBC.Drama.ae':             'MBCDrama.ae',
    'MBC.Masr.HD.ae':           'MBCMasr.eg',
    'MBC.Masr.2.HD.ae':         'MBCMasr2.eg',

    # Rotana
    'Rotana.Cinema.KSA.ae':     'RotanaCinema.sa',
    'Rotana.Cinema.Egypt.ae':   'RotanaCinemaEgypt.eg',
    'Rotana.Drama.ae':          'RotanaDrama.sa',
    'Rotana.Classic.ae':        'RotanaClassic.sa',
    'Rotana.Khalijia.ae':       'RotanaKhalijia.sa',
    'Rotana.Mousica.ae':        'RotanaMousica.sa',

    # Sports & News
    'KSA.Sports.1.ae':          'KSA-Sports-1.sa',
    'KSA.Sports.2.HD.ae':       'KSA-Sports-2.sa',
    'On.Time.Sports.HD.ae':     'OnTimeSports1.eg',
    'On.Time.Sport.2.HD.ae':    'OnTimeSports2.eg',
    'Sharjah.Sports.HD.ae':     'SharjahSports.ae',
    'Al.Arabiya.HD.ae':         'AlArabiya.net',
    'Al.Hadath.ae':             'AlHadath.net',
    'Sky.News.Arabia.HD.ae':    'SkyNewsArabia.ae',
    'Jordan.TV.HD.ae':          'JordanTV.jo',
    'BBC.Arabic.ae':            'BBCArabic.uk',
    'France.24.Arabic.ae':      'France24Arabic.fr',
    'RT.Arabic.HD.ae':          'RTArabic.ru',

    # Religious
    'Saudi.Quran.TV.HD.ae':     'SaudiQuran.sa',
    'Saudi.Sunna.TV.HD.ae':     'SaudiSunnah.sa',
    'Saudi.Al.Ekhbariya.HD.ae': 'SaudiEkhbariya.sa',
    'Sharjah.Quran.TV.ae':      'SharjahQuran.ae',
}

FORBIDDEN_SUFFIXES = (
    '.hk', '.kr', '.dk', '.fi', '.no', '.se', '.be', '.es', '.fr', 
    '.ca', '.ca2', '.gr', '.de', ".dk", '.cz', '.cy', '.ch', '.it', '.us', '.bb',
    '.distro', '.us_locals1', '.pluto'
)

# ── Helpers ──────────────────────────────────────────────────────────────────
def strip_quality(s):
    return re.sub(r'(@\S+)|(\s*\(.*\))', '', s or '').strip()

def norm(s):
    s = strip_quality(s)
    return re.sub(r'[^a-z0-9]', '', s.lower())

def is_excluded(tvg_id, name=''):
    c_id = (tvg_id or '').lower()
    c_name = (name or '').lower()
    n_id = norm(tvg_id)
    n_name = norm(name)

    # 1. Suffix check
    if any(c_id.endswith(s) for s in FORBIDDEN_SUFFIXES):
        return True

    # 2. Keyword check
    for word in EXCLUDE_WORDS:
        # Check if word exists in raw id, raw name, or normalized versions
        if word in c_id or word in c_name or word in n_id or word in n_name:
            return True
    return False

def apply_logo(extinf_line, tvg_id, tvg_name):
    n_id = norm(tvg_id)
    n_name = norm(tvg_name)
    logo_url = None
    
    for key, url in LOGO_MAP.items():
        n_key = norm(key)
        if not n_key: continue
        
        if n_key in n_id or n_id in n_key or n_key in n_name or n_name in n_key:
            logo_url = url
            break

    if logo_url:
        if 'tvg-logo=' in extinf_line:
            return re.sub(r'tvg-logo="[^"]*"', f'tvg-logo="{logo_url}"', extinf_line)
        else:
            return re.sub(r'(#EXTINF:[^,]*)', rf'\1 tvg-logo="{logo_url}"', extinf_line, count=1)
    return extinf_line

def load_epg_channels():
    epg_exact = set()
    epg_norm = {}
    epg_programmes = defaultdict(list)
    for url in EPG_SOURCES:
        fname = url.split('/')[-1]
        print(f"📥 Loading EPG channels from: {fname}")
        try:
            r = requests.get(url, timeout=60)
            content = r.content
            if not content:
                print(f"   ⚠️  Empty response")
                continue
            f = gzip.GzipFile(fileobj=io.BytesIO(content)) if content[:2] == b'\x1f\x8b' else io.BytesIO(content)
            for event, elem in ET.iterparse(f, events=('end',)):
                tag = elem.tag.split('}')[-1]
                if tag == 'channel':
                    cid = elem.get('id', '')
                    if cid:
                        epg_exact.add(cid)
                        epg_norm[norm(cid)] = cid
                elif tag == 'programme':
                    cid = elem.get('channel', '')
                    if cid in epg_exact:
                        epg_programmes[cid].append(ET.tostring(elem, encoding='utf-8'))
                elem.clear()
        except Exception as e:
            print(f"   ⚠️  Error: {e}")
    print(f"   ✅ EPG has {len(epg_exact)} unique channel ids\n")
    return epg_exact, epg_norm, epg_programmes

def fetch_and_resolve_m3u(epg_exact, epg_norm):
    id_map_norm = {norm(k): v for k, v in ID_MAP.items()}
    r = requests.get(M3U_URL, timeout=30)
    lines = r.text.splitlines()
    channels = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('#EXTINF'):
            extinf = line
            url = lines[i + 1] if i + 1 < len(lines) else ''
            i += 2
            tid_m = re.search(r'tvg-id="([^"]*)"', extinf)
            name_m = re.search(r'tvg-name="([^"]*)"', extinf)
            tvg_id = tid_m.group(1) if tid_m else ''
            tvg_name = name_m.group(1) if name_m else ''
            n = norm(tvg_id)
            epg_id = None
            if n in id_map_norm:
                epg_id = id_map_norm[n]
            elif tvg_id in epg_exact:
                epg_id = tvg_id
            elif n in epg_norm:
                epg_id = epg_norm[n]
            channels.append({'extinf': extinf, 'url': url, 'tvg_id': tvg_id, 'tvg_name': tvg_name, 'epg_id': epg_id})
        else:
            i += 1
    return channels

def write_outputs(channels, epg_exact, epg_norm, epg_programmes):
    kept_channels = []
    epg_ids_needed = set()
    no_epg = []
    
    for ch in channels:
        if is_excluded(ch['tvg_id'], ch['tvg_name']):
            continue
        kept_channels.append(ch)
        
        if ch['epg_id']:
            epg_ids_needed.add(ch['epg_id'])
        else:
            no_epg.append(ch)

    with open(M3U_OUTPUT, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        for ch in kept_channels:
            # 1. APPLY LOGO FIRST (while the original IDs are still present)
            line = apply_logo(ch['extinf'], ch['tvg_id'], ch['tvg_name'])
            
            # 2. THEN OVERWRITE TVG-ID FOR EPG (if a match exists)
            if ch['epg_id']:
                line = re.sub(r'tvg-id="[^"]*"', f'tvg-id="{ch["epg_id"]}"', line)
                
            f.write(line + '\n' + ch['url'] + '\n')

    total_progs = sum(len(epg_programmes[eid]) for eid in epg_ids_needed)
    print(f"💾 Writing EPG: {len(epg_ids_needed)} channels, {total_progs} programmes")
    with open(EPG_OUTPUT, 'wb') as f:
        f.write(b'<?xml version="1.0" encoding="utf-8"?>\n<tv>\n')
        for eid in sorted(epg_ids_needed):
            chan_xml = f'<channel id="{eid}"><display-name>{eid}</display-name></channel>\n'
            f.write(chan_xml.encode('utf-8'))
        for eid in sorted(epg_ids_needed):
            for prog in epg_programmes[eid]:
                f.write(prog + b'\n')
        f.write(b'</tv>')

    print(f"\n❓ Channels WITHOUT EPG match ({len(no_epg)}):")
    for ch in sorted(no_epg, key=lambda x: x['tvg_name']):
        print(f"   tvg-id={ch['tvg_id']!r:45s}  name={ch['tvg_name']!r}")
    print(f"\n✅ Done! → {M3U_OUTPUT} + {EPG_OUTPUT}")

def main():
    print("🚀 Arabic IPTV Sync\n")
    epg_exact, epg_norm, epg_programmes = load_epg_channels()
    channels = fetch_and_resolve_m3u(epg_exact, epg_norm)
    write_outputs(channels, epg_exact, epg_norm, epg_programmes)

if __name__ == '__main__':
    main()
