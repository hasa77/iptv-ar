import requests
import re
import gzip
import xml.etree.ElementTree as ET
import io
import os
import json
from collections import defaultdict

M3U_URL = "https://iptv-org.github.io/iptv/languages/ara.m3u"
M3U_OUTPUT = "curated.m3u"
EPG_OUTPUT = "arabic-epg.xml"
EPG_SOURCES = [
    "https://epgshare01.online/epgshare01/epg_ripper_AE1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_ALJAZEERA1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_BEIN1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_SA2.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_UK1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_US2.xml.gz",
    "https://iptv-epg.org/files/epg-meyqso.xml",
]

# Paths
ID_MAP_PATH = os.path.join('resources', 'id_map.json')
LOGO_MAP_PATH = os.path.join('resources', 'logo_map.json')
LOGOS_DIR = os.path.join('resources', 'logos')
EXCLUDE_WORDS_PATH = os.path.join('resources', 'exclude_words.txt')

# Global list to track external links
EXTERNAL_LOGOS_TRACKER = []

def strip_quality(s):
    return re.sub(r'(@\S+)|(\s*\(.*\))', '', s or '').strip()
    
def norm(s):
    s = strip_quality(s)
    return re.sub(r'[^a-z0-9]', '', s.lower())
    
def load_id_map():
    if not os.path.exists(ID_MAP_PATH): 
        print(f"⚠️ ID MAP NOT FOUND at {ID_MAP_PATH}")
        return {}
    try:
        with open(ID_MAP_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Error loading ID_MAP: {e}")
        return {}

def load_logo_map():
    if not os.path.exists(LOGO_MAP_PATH):
        print("⚠️ LOGO MAP NOT FOUND!")
        return {}
    try:
        with open(LOGO_MAP_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Error loading LOGO_MAP: {e}")
        return {}

def download_logos(logo_map):
    if not os.path.exists(LOGOS_DIR):
        os.makedirs(LOGOS_DIR)
        
    for n_id, url in logo_map.items():
        if '.svg' in url.lower(): continue  # Skip SVG files
        
        ext = '.jpg' if ('.jpg' in url.lower() or '.jpeg' in url.lower()) else '.png'
        local_file = os.path.join(LOGOS_DIR, f"{n_id}{ext}")
        
        if not os.path.exists(local_file):
            print(f"📥 Downloading logo: {n_id}{ext}")
            download_logo(url, local_file)

def load_exclude_words():
    if not os.path.exists(EXCLUDE_WORDS_PATH): return []
    with open(EXCLUDE_WORDS_PATH, 'r', encoding='utf-8') as f:
        return [line.strip().lower() for line in f if line.strip() and not line.startswith('#')]

# Initialize Data
LOGO_MAP = load_logo_map()
EXCLUDE_WORDS = load_exclude_words()
ID_MAP = load_id_map()

def is_excluded(tvg_id, name=''):
    c_id, c_name = (tvg_id or '').lower(), (name or '').lower()
    n_id, n_name = norm(tvg_id), norm(name)
    forbidden = ('.hk', '.kr', '.dk', '.fi', '.no', '.se', '.be', '.es', '.fr', '.ca', '.gr', '.de', '.cz', '.it', '.us', '.pluto')
    if any(c_id.endswith(s) for s in forbidden): return True
    for word in EXCLUDE_WORDS:
        if word in c_id or word in c_name or word in n_id or word in n_name: return True
    return False

def download_logo(url, local_path):
    """Downloads a single logo file."""
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if r.status_code == 200:
            with open(local_path, 'wb') as f:
                f.write(r.content)
            return True
    except Exception as e:
        print(f"      ⚠️ Download Error: {e}")
    return False

def apply_logo(extinf, tid, tname):
    n = norm(tid)
    
    # Define potential extensions to check
    valid_extensions = ['.png', '.jpg', '.jpeg']
    
    # 1. Check if ANY valid local file already exists
    for ext in valid_extensions:
        local_path = os.path.join(LOGOS_DIR, f"{n}{ext}")
        if os.path.exists(local_path):
            logo_url = f"https://raw.githubusercontent.com/hasa77/iptv-ar/main/{local_path.replace(os.sep, '/')}"
            return re.sub(r'tvg-logo=\"[^\"]*\"', f'tvg-logo=\"{logo_url}\"', extinf)

    # 2. If not found locally, try downloading from map
    ext_url = LOGO_MAP.get(n)
    if ext_url:
        # Determine correct extension from the URL
        if '.jpg' in ext_url.lower() or '.jpeg' in ext_url.lower():
            target_ext = '.jpg'
        else:
            target_ext = '.png'
            
        local_path = os.path.join(LOGOS_DIR, f"{n}{target_ext}")
        
        if download_logo(ext_url, local_path):
            logo_url = f"https://raw.githubusercontent.com/hasa77/iptv-ar/main/{local_path.replace(os.sep, '/')}"
            return re.sub(r'tvg-logo=\"[^\"]*\"', f'tvg-logo=\"{logo_url}\"', extinf)

    return extinf

def load_epg_channels():
    epg_exact, epg_norm = set(), {}
    epg_programmes = defaultdict(list)
    
    for url in EPG_SOURCES:
        print(f"📥 Loading EPG: {url.split('/')[-1]}")
        try:
            r = requests.get(url, timeout=60)
            content = gzip.decompress(r.content) if r.content[:2] == b'\x1f\x8b' else r.content
            content_str = content.decode('utf-8')
            
            for match in re.finditer(r'<channel id="([^"]+)"', content_str):
                cid = match.group(1)
                epg_exact.add(cid)
                epg_norm[norm(cid)] = cid
            
            for match in re.finditer(r'<programme[^>]*>.*?</programme>', content_str, re.DOTALL):
                prog_xml = match.group(0)
                cid_match = re.search(r'channel="([^"]+)"', prog_xml)
                if cid_match:
                    cid = cid_match.group(1)
                    epg_programmes[cid].append(prog_xml)
            
            print(f"    ✅ Found {len(epg_exact)} channels")
        except Exception as e:
            print(f"    ⚠️ Error: {e}")
            
    return epg_exact, epg_norm, epg_programmes

def main():
    # 1. Download missing logos
    download_logos(LOGO_MAP)
    
    # 2. Process EPG
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
            
            # Apply logo (Local first, then Map)
            extinf = apply_logo(extinf, tid, tname)
            kept.append((extinf, url))
        else: i += 1

    # Save Output
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
