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
    "https://epgshare01.online/epgshare01/epg_ripper_EG1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_SA1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_SA2.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_UK1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_US2.xml.gz",
    "https://iptv-epg.org/files/epg-meyqso.xml"
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
    epg_exact, epg_norm = set(), {}
    epg_programmes = defaultdict(list)
    
    for url in EPG_SOURCES:
        print(f"📥 Loading EPG: {url.split('/')[-1]}")
        try:
            r = requests.get(url, timeout=60)
            content = gzip.decompress(r.content) if r.content[:2] == b'\x1f\x8b' else r.content
            
            # Using context manager for memory safety
            f = io.BytesIO(content)
            channel_count = 0
            programme_count = 0
            
            for _, elem in ET.iterparse(f, events=('end',)):
                # This split extracts the tag name regardless of namespace (e.g., 'ns0:programme' -> 'programme')
                tag = elem.tag.split('}')[-1]
                
                if tag == 'channel':
                    cid = elem.get('id')
                    if cid:
                        epg_exact.add(cid)
                        epg_norm[norm(cid)] = cid
                        channel_count += 1
                        
                elif tag == 'programme':
                    cid = elem.get('channel')
                    if cid:
                        # Extract the full XML of the programme block
                        # method='xml' ensures <desc>, <category> etc are included
                        prog_xml = ET.tostring(elem, encoding='unicode', method='xml')
                        epg_programmes[cid].append(prog_xml)
                        programme_count += 1
                
                elem.clear() # Free memory
            print(f"    ✅ Found {channel_count:,} channels and {programme_count:,} programmes")
        except Exception as e:
            print(f"    ⚠️ Error: {e}")
            
    return epg_exact, epg_norm, epg_programmes

def main():
    epg_exact, epg_norm, epg_progs = load_epg_channels()
    id_map_norm = {norm(k): v for k, v in ID_MAP.items()}
    
    print(f"\n📡 Fetching M3U...")
    r = requests.get(M3U_URL, timeout=30)
    lines = r.text.splitlines()
    kept, epg_needed = [], set()

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
            
            kept.append((apply_logo(extinf, tid, tname), url))
        else: i += 1

    # Write M3U
    with open(M3U_OUTPUT, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        for extinf, url in kept: f.write(f"{extinf}\n{url}\n")

    # Write EPG
    with open(EPG_OUTPUT, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n<tv>\n')
        for eid in sorted(epg_needed):
            f.write(f'  <channel id="{eid}"><display-name>{eid}</display-name></channel>\n')
            for prog in epg_progs.get(eid, []):
                # Remove namespace prefixes like ns0: from tags so players can read them
                clean_prog = re.sub(r'ns\d+:', '', prog)
                f.write(f'  {clean_prog}\n')
        f.write('</tv>\n')
    
    print(f"\n📊 Summary: {matched_count} matches. Files created.")

if __name__ == '__main__':
    main()
