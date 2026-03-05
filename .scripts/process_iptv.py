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
        print(f"Warning: {LOGO_MAP_PATH} not found.")
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
        print(f"Warning: {EXCLUDE_WORDS_PATH} not found.")
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
# Format: M3U tvg-id → EPG channel id
ID_MAP = {
    # Manual mappings
    'Al.Arabiya.Programs': 'AlArabiya.net',
    'Al.Araby.TV2': 'Al.Araby.2.HD.ae',
    'Al.Iraqia.News': 'Al.Iraqiya.HD.ae',
    'Al.Maaref.TV': 'AlMaaref.bh',
    
    # Abu Dhabi
    'Abu.Dhabi.HD.ae': 'AbuDhabiTV.ae',
    'AD.Sports.1.HD.ae': 'AbuDhabiSports1.ae',
    'AD.Sports.2.HD.ae': 'AbuDhabiSports2.ae',
    'Yas.TV.HD.ae': 'YasTV.ae',

    # Dubai
    'Dubai.HD.ae': 'DubaiTV.ae',
    'Sama.Dubai.HD.ae': 'SamaDubai.ae',
    'Dubai.One.HD.ae': 'DubaiOne.ae',
    'Noor.DubaiTV.ae': 'NoorDubaiTV.ae',
    'Dubai.Sports.1.HD.ae': 'DubaiSports1.ae',
    'Dubai.Sports.2.ae': 'DubaiSports2.ae',
    'Dubai.Racing.ae': 'DubaiRacing1.ae',
    'Dubai.Zaman.ae': 'DubaiZaman.ae',
    'One.Tv.ae': 'OneTv.ae',

    # MBC - Map both formats
    'MBC.1.ae': 'MBC1.ae',
    'MBC.2.ae': 'MBC2.ae',
    'MBC.3.ae': 'MBC3.ae',
    'MBC.4.ae': 'MBC4.ae',
    'MBC.Action.ae': 'MBCAction.ae',
    'MBC.Drama.ae': 'MBCDrama.ae',
    'MBC.Masr.HD.ae': 'MBCMasr.eg',
    'MBC.Masr.2.HD.ae': 'MBCMasr2.eg',
    'MBCIraq.iq@SD': 'MBC.Iraq.HD.ae',  # NEW: Map MBC Iraq
    'MBC1.ae': 'MBC1.ae',
    'MBC2.ae': 'MBC2.ae',
    'MBC3.ae': 'MBC3.ae',
    'MBC4.ae': 'MBC4.ae',

    # Rotana
    'Rotana.Cinema.KSA.ae': 'RotanaCinema.sa',
    'Rotana.Cinema.Egypt.ae': 'RotanaCinemaEgypt.eg',
    'Rotana.Drama.ae': 'RotanaDrama.sa',
    'Rotana.Classic.ae': 'RotanaClassic.sa',
    'Rotana.Khalijia.ae': 'RotanaKhalijia.sa',
    'Rotana.Mousica.ae': 'RotanaMousica.sa',

    # Sports & News
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

    # Religious
    'Saudi.Quran.TV.HD.ae': 'SaudiQuran.sa',
    'Saudi.Sunna.TV.HD.ae': 'SaudiSunnah.sa',
    'Saudi.Al.Ekhbariya.HD.ae': 'SaudiEkhbariya.sa',
    'Sharjah.Quran.TV.ae': 'SharjahQuran.ae',
}

FORBIDDEN_SUFFIXES = (
    '.hk', '.kr', '.dk', '.fi', '.no', '.se', '.be', '.es', '.fr', 
    '.ca', '.ca2', '.gr', '.de', ".dk", '.cz', '.cy', '.ch', '.it', '.us', '.bb',
    '.distro', '.us_locals1', '.pluto'
)

def is_excluded(tvg_id, name=''):
    """Check if channel should be excluded"""
    c_id = (tvg_id or '').lower()
    c_name = (name or '').lower()
    n_id, n_name = norm(tvg_id), norm(name)

    if any(c_id.endswith(s) for s in FORBIDDEN_SUFFIXES):
        return True

    for word in EXCLUDE_WORDS:
        if word in c_id or word in c_name or word in n_id or word in n_name:
            return True
    return False

def apply_logo(extinf_line, tvg_id, tvg_name):
    """Apply logo from logo map if available"""
    n_id, n_name = norm(tvg_id), norm(tvg_name)
    
    logo_url = LOGO_MAP.get(n_id) or LOGO_MAP.get(n_name)

    if logo_url:
        if 'tvg-logo=' in extinf_line:
            return re.sub(r'tvg-logo="[^"]*"', f'tvg-logo="{logo_url}"', extinf_line)
        else:
            return re.sub(r'(#EXTINF:[^,]*)', rf'\1 tvg-logo="{logo_url}"', extinf_line, count=1)
    return extinf_line

def load_epg_channels():
    """Load EPG data from sources, extracting .gz files"""
    epg_exact = set()  # Exact channel IDs
    epg_norm = {}      # Normalized ID → exact ID mapping
    epg_programmes = defaultdict(list)
    
    for url in EPG_SOURCES:
        print(f"📥 Loading EPG: {url.split('/')[-1]}")
        try:
            r = requests.get(url, timeout=60)
            
            # Handle gzipped content (extract it!)
            if r.content[:2] == b'\x1f\x8b':
                print(f"    🗜️  Decompressing .gz file...")
                content = gzip.decompress(r.content)
                f = io.BytesIO(content)
            else:
                f = io.BytesIO(r.content)
            
            # Parse XML
            for _, elem in ET.iterparse(f, events=('end',)):
                tag = elem.tag.split('}')[-1]
                
                if tag == 'channel':
                    cid = elem.get('id', '')
                    if cid:
                        epg_exact.add(cid)
                        epg_norm[norm(cid)] = cid
                        
                elif tag == 'programme':
                    cid = elem.get('channel', '')
                    if cid in epg_exact:
                        epg_programmes[cid].append(ET.tostring(elem, encoding='unicode'))
                
                elem.clear()
                
        except Exception as e:
            print(f"    ⚠️  Error: {e}")
    
    print(f"📊 Total unique EPG channel IDs found: {len(epg_exact)}")
    print(f"    Sample EPG IDs: {list(epg_exact)[:10]}")
    return epg_exact, epg_norm, epg_programmes

def fetch_and_resolve_m3u(epg_exact, epg_norm):
    """Fetch M3U and match channels to EPG IDs"""
    id_map_norm = {norm(k): v for k, v in ID_MAP.items()}
    
    r = requests.get(M3U_URL, timeout=30)
    lines = r.text.splitlines()
    channels = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        if line.startswith('#EXTINF'):
            extinf = line
            url = lines[i+1] if i+1 < len(lines) else ''
            i += 2
            
            # Extract tvg-id and tvg-name
            tid_m = re.search(r'tvg-id="([^"]*)"', extinf)
            name_m = re.search(r'tvg-name="([^"]*)"', extinf)
            tid = tid_m.group(1) if tid_m else ''
            tname = name_m.group(1) if name_m else ''
            
            # Try to find matching EPG ID
            n = norm(tid)
            epg_id = None
            
            # 1. Check explicit mapping first
            if n in id_map_norm:
                epg_id = id_map_norm[n]
            # 2. Check if tvg-id exists exactly in EPG
            elif tid in epg_exact:
                epg_id = tid
            # 3. Try normalized match
            elif n in epg_norm:
                epg_id = epg_norm[n]
            
            channels.append({
                'extinf': extinf,
                'url': url,
                'tvg_id': tid,
                'tvg_name': tname,
                'epg_id': epg_id
            })
        else:
            i += 1
    
    return channels

def write_outputs(channels, epg_programmes):
    """Write M3U and EPG files"""
    kept = []
    epg_needed = set()
    
    # Filter channels
    for ch in channels:
        if is_excluded(ch['tvg_id'], ch['tvg_name']):
            continue
        kept.append(ch)
        if ch['epg_id']:
            epg_needed.add(ch['epg_id'])

    # Write M3U
    with open(M3U_OUTPUT, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        for ch in kept:
            line = apply_logo(ch['extinf'], ch['tvg_id'], ch['tvg_name'])
            
            # Update tvg-id to match EPG
            if ch['epg_id']:
                line = re.sub(r'tvg-id="[^"]*"', f'tvg-id="{ch["epg_id"]}"', line)
            
            f.write(f"{line}\n{ch['url']}\n")

    # Write EPG (uncompressed XML)
    with open(EPG_OUTPUT, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n<tv>\n')
        
        # Write channel definitions
        for eid in sorted(epg_needed):
            f.write(f'  <channel id="{eid}"><display-name>{eid}</display-name></channel>\n')
        
        # Write programmes
        for eid in sorted(epg_needed):
            for prog in epg_programmes.get(eid, []):
                f.write(f'  {prog}\n')
        
        f.write('</tv>\n')
    
    print(f"\n📺 EPG Matched: {len(epg_needed)} channels have guide data")
    print(f"🚫 EPG Missing: {len(kept) - len(epg_needed)} channels have no guide data")
    print(f"\n✅ Done! → {M3U_OUTPUT} ({len(kept)} channels total)")
    print(f"✅ EPG  → {EPG_OUTPUT} (uncompressed XML for TiviMate)")

def main():
    print("🚀 Arabic IPTV Sync (with .gz extraction)\n")
    epg_exact, epg_norm, epg_progs = load_epg_channels()
    channels = fetch_and_resolve_m3u(epg_exact, epg_norm)
    write_outputs(channels, epg_progs)

if __name__ == '__main__':
    main()
