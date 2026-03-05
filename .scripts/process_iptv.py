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
    "https://epgshare01.online/epgshare01/epg_ripper_AE1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_ALJAZEERA1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_BEIN1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_SA2.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_UK1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_US2.xml.gz",
]

# Paths
LOGO_MAP_PATH = os.path.join('resources', 'logo_map.json')
EXCLUDE_WORDS_PATH = os.path.join('resources', 'exclude_words.txt')

def load_logo_map():
    if not os.path.exists(LOGO_MAP_PATH): return {}
    try:
        with open(LOGO_MAP_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {norm(k): v for k, v in data.items()}
    except: return {}

def load_exclude_words():
    if not os.path.exists(EXCLUDE_WORDS_PATH): return []
    with open(EXCLUDE_WORDS_PATH, 'r', encoding='utf-8') as f:
        return [line.strip().lower() for line in f if line.strip() and not line.startswith('#')]
        
def strip_quality(s):
    return re.sub(r'(@\S+)|(\s*\(.*\))', '', s or '').strip()

def norm(s):
    s = strip_quality(s)
    return re.sub(r'[^a-z0-9]', '', s.lower())

LOGO_MAP = load_logo_map()
EXCLUDE_WORDS = load_exclude_words()

ID_MAP = {
    # --- Dubai Media Inc ---
    'Dubai TV': 'Dubai.ae',
    'Dubai HD': 'Dubai.HD.ae',
    'Sama Dubai': 'Sama.Dubai.ae',
    'Sama Dubai HD': 'Sama.Dubai.HD.ae',
    'One TV': 'One.Tv.ae',
    'Dubai One': 'One.Tv.ae',
    'Dubai One HD': 'Dubai.One.HD.ae',
    'Noor Dubai TV': 'Noor.DubaiTV.ae',
    'Noor DubaiTV': 'Noor.DubaiTV.ae',
    'Dubai Sports 1': 'Dubai.Sports.1.ae',
    'Dubai Sports 2': 'Dubai.Sports.2.ae',
    'Dubai Racing': 'Dubai.Racing.ae',
    'Dubai Racing 1': 'Dubai.Racing.1.HD.ae',
    'Dubai Racing 2': 'Dubai.Racing.2.ae',
    'Dubai Zaman': 'Dubai.Zaman.ae',
    'Dubai Radio': 'Dubai.Radio.ae',
    'Noor Dubai Radio': 'Noor.Dubai.Radio.ae',
    'Quran Radio': 'Quran.Radio.ae',

    # --- Abu Dhabi Media ---
    'Abu Dhabi TV': 'Abu.Dhabi.HD.ae',
    'Abu Dhabi HD': 'Abu.Dhabi.HD.ae',
    'Emarat TV': 'Emarat.HD.ae',
    'Emarat HD': 'Emarat.HD.ae',
    'Nat Geo Abu Dhabi': 'Nat.Geo.Abu.Dhabi.HD.ae',
    'Nat Geo Abu Dhabi HD': 'Nat.Geo.Abu.Dhabi.HD.ae',
    'AD Sports 1': 'AD.Sports.1.HD.ae',
    'AD Sports 2': 'AD.Sports.2.HD.ae',
    'Yas TV': 'Yas.TV.HD.ae',
    'Majid Kids': 'Majid.Kids.TV.HD.ae',

    # --- MBC Group ---
    'MBC 1': 'MBC.1.ae',
    'MBC 2': 'MBC.2.ae',
    'MBC 3': 'MBC.3.ae',
    'MBC 4': 'MBC.4.ae',
    'MBC Action': 'MBC.Action.ae',
    'MBC Drama': 'MBC.Drama.ae',
    'MBC Bollywood': 'MBC.Bollywood.ae',
    'MBC Masr': 'MBC.Masr.HD.ae',
    'MBC Masr HD': 'MBC.Masr.HD.ae',
    'MBC Masr 2': 'MBC.Masr.2.HD.ae',
    'MBC Masr Drama': 'MBC.Masr.Drama.HD.ae',
    'MBC Iraq': 'MBC.Iraq.HD.ae',

    # --- Sharjah Channels ---
    'Sharjah TV': 'Sharjah.HD.ae',
    'Sharjah Sports': 'Sharjah.Sports.HD.ae',
    'Sharjah Quran': 'Sharjah.Quran.TV.ae',

    # --- Rotana Group ---
    'Rotana Khalijia': 'Rotana.Khalijia.ae',
    'Rotana Cinema KSA': 'Rotana.Cinema.KSA.ae',
    'Rotana Cinema Egypt': 'Rotana.Cinema.Egypt.ae',
    'Rotana Classic': 'Rotana.Classic.ae',
    'Rotana Drama': 'Rotana.Drama.ae',
    'Rotana Music': 'Rotana.Music.ae',
    'Rotana Clip': 'Rotana.Clip.ae',

    # --- News & International ---
    'Al Arabiya': 'Al.Arabiya.HD.ae',
    'Al Arabiya HD': 'Al.Arabiya.HD.ae',
    'Al Hadath': 'Al.Hadath.ae',
    'Sky News Arabia': 'Sky.News.Arabia.HD.ae',
    'Sky News Arabia HD': 'Sky.News.Arabia.HD.ae',
    'BBC Arabic': 'BBC.Arabic.ae',
    'BBC World News': 'BBC.World.News.ae',
    'Extra News': 'Extra.News.HD.ae',
    'Extra News HD': 'Extra.News.HD.ae',
    'RT Arabic': 'RT.Arabic.HD.ae',
    'RT Arabic HD': 'RT.Arabic.HD.ae',
    'France 24 Arabic': 'France.24.Arabic.ae',
    'France 24 English': 'France.24.English.ae',
    'CGTN': 'CGTN.ae',
    'CGTN Arabic': 'CGTN.Arabic.ae',
    'CNN International': 'CNN.International.ae',
    'NHK World Japan': 'NHK.World.Japan.ae',
    'TV5 Monde': 'TV5.Monde.ae',
    'KBS World': 'KBS.World.ae',
    'Wion HD': 'Wion.HD.ae',
    'Arirang World': 'Arirang.World.ae',

    # --- Regional & State Channels ---
    'Saudi TV': 'Saudi.HD.ae',
    'Saudi Al Ekhbariya': 'Saudi.Al.Ekhbariya.HD.ae',
    'Saudi Al Ekhbariya HD': 'Saudi.Al.Ekhbariya.HD.ae',
    'SBC': 'SBC.HD.ae',
    'Kuwait TV 1': 'Kuwait.TV.1.HD.ae',
    'Jordan TV': 'Jordan.TV.HD.ae',
    'Sudan TV': 'Sudan.TV.ae',
    'Al Oula': 'Al.Oula.ae',
    'Iraq Future': 'Iraq.Future.TV.ae',
    'Iraq Future TV': 'Iraq.Future.TV.ae',
    'Al Jamahiriya TV': 'Al.Jamahiriya.TV.ae',
    'Libya Al Ahrar HD': 'Libya.Al.Ahrar.HD.ae',
    'Libya Alhadath HD': 'Libya.Alhadath.HD.ae',
    'Libya Alrasmia Channel': 'Libya.Alrasmia.Channel.ae',
    'Libya Al Hedaya': 'Libya.Al.Hedaya.ae',
    'Al Mamlaka TV HD': 'Al.Mamlaka.TV.HD.ae',

    # --- Religious & Specialized ---
    'Saudi Quran': 'Saudi.Quran.TV.HD.ae',
    'Saudi Sunna': 'Saudi.Sunna.TV.HD.ae',
    'Al Resala': 'Al.Resala.ae',
    'Al Majd': 'Al.Majd.ae',
    'Al Majd Holy Quran': 'Al.Majd.Holy.Quran.ae',
    'Makkah TV': 'Makkah.TV.ae',
    'Sharjah Quran': 'Sharjah.Quran.TV.ae',
    'Dua Channel': 'Dua.Channel.ae',

    # --- Entertainment, Movies & Kids ---
    'Nile Cinema': 'Nile.Cinema.ae',
    'On Drama': 'On.Drama.ae',
    'Sada El Balad': 'Sada.El.Balad.ae',
    'DMC': 'DMC.ae',
    'CBC': 'CBC.ae',
    'Zee Aflam': 'Zee.Aflam.ae',
    'Zee Alwan': 'Zee.Alwan.ae',
    'B4U Plus': 'B4U.Plus.ae',
    'Al Aan TV': 'Al.Aan.TV.ae',
    'LBC': 'LBC.ae',
    'Mazzika': 'Mazzika.ae',
    'Chada TV': 'Chada.TV.ae',
    'Space Toon': 'Space.Toon.ae',
    'CN Arabic': 'CN.Arabic.ae',
    'Mekameleen': 'Mekameleen.ae',
    'Al Mayadeen HD': 'Al.Mayadeen.HD.ae',
    'Al Kahera 3': 'Al.Kahera.3.ae',
    'Teba 8': 'Teba.8.ae',
    'Extra live': 'Extra.live.ae',
    'Zaytoona': 'Zaytoona.ae',
}

def is_excluded(tvg_id, name=''):
    c_id, c_name = (tvg_id or '').lower(), (name or '').lower()
    n_id, n_name = norm(tvg_id), norm(name)
    forbidden = ('.hk', '.kr', '.dk', '.fi', '.no', '.se', '.be', '.es', '.fr', '.ca', '.gr', '.de', '.cz', '.it', '.us', '.pluto')
    if any(c_id.endswith(s) for s in forbidden): return True
    for word in EXCLUDE_WORDS:
        if word in c_id or word in c_name or word in n_id or word in n_name: return True
    return False

def apply_logo(line, tvg_id, tvg_name):
    n_id, n_name = norm(tvg_id), norm(tvg_name)
    logo = LOGO_MAP.get(n_id) or LOGO_MAP.get(n_name)
    if logo:
        if 'tvg-logo=' in line: return re.sub(r'tvg-logo="[^"]*"', f'tvg-logo="{logo}"', line)
        else: return re.sub(r'(#EXTINF:[^,]*)', rf'\1 tvg-logo="{logo}"', line, count=1)
    return line

def load_epg_channels():
    """
    THE REAL FIX: Don't use elem.clear() at all during parsing.
    Store the raw XML string directly without modifying the tree.
    """
    epg_exact, epg_norm = set(), {}
    epg_programmes = defaultdict(list)
    
    for url in EPG_SOURCES:
        print(f"📥 Loading EPG: {url.split('/')[-1]}")
        try:
            r = requests.get(url, timeout=60)
            content = gzip.decompress(r.content) if r.content[:2] == b'\x1f\x8b' else r.content
            
            # Parse content as string to extract raw XML
            content_str = content.decode('utf-8')
            
            # Use regex to extract channel IDs and programmes
            # Extract channels
            for match in re.finditer(r'<channel id="([^"]+)"', content_str):
                cid = match.group(1)
                epg_exact.add(cid)
                epg_norm[norm(cid)] = cid
            
            # Extract complete programme tags (preserving all content)
            for match in re.finditer(r'<programme[^>]*>.*?</programme>', content_str, re.DOTALL):
                prog_xml = match.group(0)
                # Extract channel ID from this programme
                cid_match = re.search(r'channel="([^"]+)"', prog_xml)
                if cid_match:
                    cid = cid_match.group(1)
                    epg_programmes[cid].append(prog_xml)
            
            print(f"    ✅ Found {len([c for c in epg_exact if c not in epg_programmes])} channels")
            print(f"    ✅ Found {sum(len(v) for k, v in epg_programmes.items() if k in epg_exact)} programmes")
            
        except Exception as e:
            print(f"    ⚠️  Error: {e}")
            
    return epg_exact, epg_norm, epg_programmes

def main():
    epg_exact, epg_norm, epg_progs = load_epg_channels()
    id_map_norm = {norm(k): v for k, v in ID_MAP.items()}
    
    print(f"\n📡 Fetching M3U...")
    r = requests.get(M3U_URL, timeout=30)
    lines = r.text.splitlines()
    kept, epg_needed = [], set()

    matched_count = 0
    
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('#EXTINF'):
            extinf, url = line, lines[i+1] if i+1 < len(lines) else ''
            i += 2
            tid = re.search(r'tvg-id="([^"]*)"', extinf).group(1) if 'tvg-id="' in extinf else ''
            tname = re.search(r'tvg-name="([^"]*)"', extinf).group(1) if 'tvg-name="' in extinf else ''
            
            if is_excluded(tid, tname): continue
            
            n = norm(tid)
            epg_id = id_map_norm.get(n) or (tid if tid in epg_exact else epg_norm.get(n))
            
            if epg_id:
                epg_needed.add(epg_id)
                extinf = re.sub(r'tvg-id="[^"]*"', f'tvg-id="{epg_id}"', extinf)
                matched_count += 1
            
            kept.append((apply_logo(extinf, tid, tname), url))
        else: i += 1

    with open(M3U_OUTPUT, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        for extinf, url in kept: f.write(f"{extinf}\n{url}\n")

    with open(EPG_OUTPUT, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n<tv>\n')
        for eid in sorted(epg_needed):
            f.write(f'  <channel id="{eid}"><display-name>{eid}</display-name></channel>\n')
        for eid in sorted(epg_needed):
            for prog in epg_progs.get(eid, []):
                f.write(f'  {prog}\n')
        f.write('</tv>\n')
    
    print(f"\n✅ Created {M3U_OUTPUT} ({len(kept)} channels)")
    print(f"✅ Created {EPG_OUTPUT} ({matched_count} channels with EPG data)")

if __name__ == '__main__':
    main()
