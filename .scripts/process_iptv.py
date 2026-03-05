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
    "https://iptv-epg.org/files/epg-meyqso.xml"
]

# Paths
LOGO_MAP_PATH = os.path.join('resources', 'logo_map.json')
EXCLUDE_WORDS_PATH = os.path.join('resources', 'exclude_words.txt')

# --- Resource Loading ---
def load_logo_map():
    if not os.path.exists(LOGO_MAP_PATH):
        return {}
    try:
        with open(LOGO_MAP_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {norm(k): v for k, v in data.items()}
    except Exception as e:
        print(f"Error loading logo map: {e}")
        return {}

def load_exclude_words():
    if not os.path.exists(EXCLUDE_WORDS_PATH):
        return []
    with open(EXCLUDE_WORDS_PATH, 'r', encoding='utf-8') as f:
        return [line.strip().lower() for line in f if line.strip() and not line.startswith('#')]
        
# ── Helpers ──────────────────────────────────────────────────────────────────
def strip_quality(s):
    """Remove quality indicators like @HD, @SD, (1080p), etc."""
    return re.sub(r'(@\S+)|(\s*\(.*\))', '', s or '').strip()

def norm(s):
    """Normalize string for matching: lowercase, alphanumeric only"""
    s = strip_quality(s)
    return re.sub(r'[^a-z0-9]', '', s.lower())

# Load external resources
LOGO_MAP = load_logo_map()
EXCLUDE_WORDS = load_exclude_words()

# ── Enhanced ID mapping ──────────────────────────────────────────────────────
ID_MAP = {
    'Al.Arabiya.Programs': 'AlArabiya.net',
    'Al.Araby.TV2': 'Al.Araby.2.HD.ae',
    'Al.Iraqia.News': 'Al.Iraqiya.HD.ae',
    'Al.Maaref.TV': 'AlMaaref.bh',
    'Abu.Dhabi.HD.ae': 'AbuDhabiTV.ae',
    'AD.Sports.1.HD.ae': 'AbuDhabiSports1.ae',
    'AD.Sports.2.HD.ae': 'AbuDhabiSports2.ae',
    'Yas.TV.HD.ae': 'YasTV.ae',
    'Dubai.HD.ae': 'DubaiTV.ae',
    'Sama.Dubai.HD.ae': 'SamaDubai.ae',
    'Dubai.One.HD.ae': 'DubaiOne.ae',
    'Noor.DubaiTV.ae': 'NoorDubaiTV.ae',
    'Dubai.Sports.1.HD.ae': 'DubaiSports1.ae',
    'Dubai.Sports.2.ae': 'DubaiSports2.ae',
    'Dubai.Racing.ae': 'DubaiRacing1.ae',
    'Dubai.Zaman.ae': 'DubaiZaman.ae',
    'One.Tv.ae': 'OneTv.ae',
    'MBC.1.ae': 'MBC1.ae',
    'MBC.2.ae': 'MBC2.ae',
    'MBC.3.ae': 'MBC3.ae',
    'MBC.4.ae': 'MBC4.ae',
    'MBC.Action.ae': 'MBCAction.ae',
    'MBC.Drama.ae': 'MBCDrama.ae',
    'MBC.Masr.HD.ae': 'MBCMasr.eg',
    'MBC.Masr.2.HD.ae': 'MBCMasr2.eg',
    'MBCIraq.iq@SD': 'MBC.Iraq.HD.ae',
    'Rotana.Cinema.KSA.ae': 'RotanaCinema.sa',
    'Rotana.Cinema.Egypt.ae': 'RotanaCinemaEgypt.eg',
    'Rotana.Drama.ae': 'RotanaDrama.sa',
    'Rotana.Classic.ae': 'RotanaClassic.sa',
    'Rotana.Khalijia.ae': 'RotanaKhalijia.sa',
    'Rotana.Mousica.ae': 'RotanaMousica.sa',
    'KSA.Sports.1.ae': 'KSA-Sports-1.sa',
    'KSA.Sports.2.HD.ae': 'KSA-Sports-2.sa',
    'On.Time.Sports.HD.ae': 'OnTimeSports1.eg',
    'On.Time.Sport.2.HD.ae': 'OnTimeSports2.eg',
    'Sharjah.Sports.HD.ae': 'SharjahSports.ae',
    'Al.Arabiya.HD.ae': 'AlArabiya.net',
    'Al.Hadath.ae': 'AlHadath.net',
    'Sky.News.Arabia.HD.ae': 'SkyNewsArabia.ae',
    'Jordan.TV.HD.ae': 'JordanTV.jo',
    'BBC.Arabic.ae': 'BBCArabic.uk',
    'France.24.Arabic.ae': 'France24Arabic.fr',
    'RT.Arabic.HD.ae': 'RTArabic.ru',
    'Saudi.Quran.TV.HD.ae': 'SaudiQuran.sa',
    'Saudi.Sunna.TV.HD.ae': 'SaudiSunnah.sa',
    'Saudi.Al.Ekhbariya.HD.ae': 'SaudiEkhbariya.sa',
    'Sharjah.Quran.TV.ae': 'SharjahQuran.ae',
}

FORBIDDEN_SUFFIXES = (
    '.hk', '.kr', '.dk', '.fi', '.no', '.se', '.be', '.es', '.fr', 
    '.ca', '.ca2', '.gr', '.de', '.cz', '.cy', '.ch', '.it', '.us', '.bb',
    '.distro', '.us_locals1', '.pluto'
)

def is_excluded(tvg_id, name=''):
    c_id = (tvg_id or '').lower()
    c_name = (name or '').lower()
    n_id, n_name = norm(tvg_id), norm(name)
    if any(c_id.endswith(s) for s in FORBIDDEN_SUFFIXES): return True
    for word in EXCLUDE_WORDS:
        if word in c_id or word in c_name or word in n_id or word in n_name:
            return True
    return False

def apply_logo(extinf_line, tvg_id, tvg_name):
    n_id, n_name = norm(tvg_id), norm(tvg_name)
    logo_url = LOGO_MAP.get(n_id) or LOGO_MAP.get(n_name)
    if logo_url:
        if 'tvg-logo=' in extinf_line:
            return re.sub(r'tvg-logo="[^"]*"', f'tvg-logo="{logo_url}"', extinf_line)
        else:
            return re.sub(r'(#EXTINF:[^,]*)', rf'\1 tvg-logo="{logo_url}"', extinf_line, count=1)
    return extinf_line

def load_epg_channels():
    """Load EPG data by buffering all programmes to avoid missing data due to tag order."""
    epg_exact = set()
    epg_norm = {}
    epg_programmes = defaultdict(list)
    
    for url in EPG_SOURCES:
        print(f"📥 Loading EPG: {url.split('/')[-1]}")
        try:
            r = requests.get(url, timeout=60)
            content = gzip.decompress(r.content) if r.content[:2] == b'\x1f\x8b' else r.content
            
            # Use event-based parsing to handle both tags simultaneously
            f = io.BytesIO(content)
            for _, elem in ET.iterparse(f, events=('end',)):
                tag = elem.tag.split('}')[-1]
                if tag == 'channel':
                    cid = elem.get('id', '')
                    if cid:
                        epg_exact.add(cid)
                        epg_norm[norm(cid)] = cid
                elif tag == 'programme':
                    cid = elem.get('channel', '')
                    if cid:
                        # Store ALL programmes temporarily; we filter them in write_outputs
                        epg_programmes[cid].append(ET.tostring(elem, encoding='unicode'))
                elem.clear()
        except Exception as e:
            print(f"    ⚠️  Error: {e}")
    
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
            extinf, url = line, lines[i+1] if i+1 < len(lines) else ''
            i += 2
            tid_m = re.search(r'tvg-id="([^"]*)"', extinf)
            name_m = re.search(r'tvg-name="([^"]*)"', extinf)
            tid, tname = tid_m.group(1) if tid_m else '', name_m.group(1) if name_m else ''
            
            n = norm(tid)
            # Match priority: Explicit Map -> Exact Match -> Normalized Match
            epg_id = id_map_norm.get(n) or (tid if tid in epg_exact else epg_norm.get(n))
            
            channels.append({'extinf': extinf, 'url': url, 'tvg_id': tid, 'tvg_name': tname, 'epg_id': epg_id})
        else:
            i += 1
    return channels

def write_outputs(channels, epg_programmes):
    kept, epg_needed = [], set()
    for ch in channels:
        if is_excluded(ch['tvg_id'], ch['tvg_name']): continue
        kept.append(ch)
        if ch['epg_id']: epg_needed.add(ch['epg_id'])

    with open(M3U_OUTPUT, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        for ch in kept:
            line = apply_logo(ch['extinf'], ch['tvg_id'], ch['tvg_name'])
            if ch['epg_id']:
                line = re.sub(r'tvg-id="[^"]*"', f'tvg-id="{ch["epg_id"]}"', line)
            f.write(f"{line}\n{ch['url']}\n")

    # Write uncompressed XML EPG
    with open(EPG_OUTPUT, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n<tv>\n')
        # Definitions
        for eid in sorted(epg_needed):
            f.write(f'  <channel id="{eid}"><display-name>{eid}</display-name></channel>\n')
        # Matched programmes
        for eid in sorted(epg_needed):
            for prog in epg_programmes.get(eid, []):
                f.write(f'  {prog}\n')
        f.write('</tv>\n')
    
    print(f"\n📊 Channels Kept: {len(kept)}")
    print(f"📺 EPG Matched: {len(epg_needed)} channels")
    print(f"✅ Created: {M3U_OUTPUT} and {EPG_OUTPUT}")

def main():
    print("🚀 Starting IPTV and EPG Sync...")
    epg_exact, epg_norm, epg_progs = load_epg_channels()
    channels = fetch_and_resolve_m3u(epg_exact, epg_norm)
    write_outputs(channels, epg_progs)

if __name__ == '__main__':
    main()
