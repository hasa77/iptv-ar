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

def strip_quality(s):
    return re.sub(r'(@\S+)|(\s*\(.*\))', '', s or '').strip()

def norm(s):
    s = strip_quality(s)
    return re.sub(r'[^a-z0-9]', '', s.lower())

def load_id_map():
    if not os.path.exists(ID_MAP_PATH):
        print(f"⚠️ ID MAP NOT FOUND at {ID_MAP_PATH}")
        return {}, set()
    try:
        with open(ID_MAP_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            blocked = {norm(k) for k, v in data.items() if v == ""}
            valid = {k: v for k, v in data.items() if v != ""}
            return valid, blocked
    except:
        return {}, set()

def load_logo_map():
    if not os.path.exists(LOGO_MAP_PATH):
        print("⚠️ LOGO MAP NOT FOUND!")
        return {}
    try:
        with open(LOGO_MAP_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def download_logos(logo_map):
    if not os.path.exists(LOGOS_DIR):
        os.makedirs(LOGOS_DIR)
        
    for n_id, url in logo_map.items():
        if '.svg' in url.lower(): continue
        ext = '.jpg' if ('.jpg' in url.lower() or '.jpeg' in url.lower()) else '.png'
        local_file = os.path.join(LOGOS_DIR, f"{n_id}{ext}")
        if not os.path.exists(local_file):
            print(f"📥 Downloading logo: {n_id}{ext}")
            download_logo(url, local_file)

def load_exclude_words():
    if not os.path.exists(EXCLUDE_WORDS_PATH): return []
    with open(EXCLUDE_WORDS_PATH, 'r', encoding='utf-8') as f:
        return [line.strip().lower() for line in f if line.strip() and not line.startswith('#')]

LOGO_MAP = load_logo_map()
EXCLUDE_WORDS = load_exclude_words()
ID_MAP, EPG_BLOCKED = load_id_map()

def is_excluded(tvg_id, name=''):
    c_id, c_name = (tvg_id or '').lower(), (name or '').lower()
    n_id, n_name = norm(tvg_id), norm(name)
    forbidden = ('.hk', '.kr', '.dk', '.fi', '.no', '.se', '.be', '.es', '.fr', '.ca', '.gr', '.de', '.cz', '.it', '.us', '.pluto')
    if any(c_id.endswith(s) for s in forbidden): return True
    for word in EXCLUDE_WORDS:
        if word in c_id or word in c_name or word in n_id or word in n_name: return True
    return False

def download_logo(url, local_path):
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if r.status_code != 200:
            print(f"⚠️ Download failed ({r.status_code}) for {url}")
            return False
        with open(local_path, 'wb') as f:
            f.write(r.content)
        return True
    except Exception as e:
        print(f"⚠️ Download Error: {e}")
    return False

def apply_logo(extinf, tid, tname):
    n = norm(tid)
    for ext in [".png", ".jpg", ".jpeg"]:
        local_path = os.path.join(LOGOS_DIR, f"{n}{ext}")
        if os.path.exists(local_path):
            logo_url = f"https://raw.githubusercontent.com/hasa77/iptv-ar/main/{local_path.replace(os.sep, '/')}"
            return re.sub(r'tvg-logo=\"[^\"]*\"', f'tvg-logo=\"{logo_url}\"', extinf)
    ext_url = LOGO_MAP.get(n)
    if ext_url:
        return re.sub(r'tvg-logo=\"[^\"]*\"', f'tvg-logo=\"{ext_url}\"', extinf)
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

            try:
                ET.fromstring(content_str)
            except:
                print(f"[EPG ERROR] Malformed XML in {url}")
                continue

            for match in re.finditer(r'<channel id="([^"]+)"', content_str):
                cid = match.group(1)
                epg_exact.add(cid)
                epg_norm[norm(cid)] = cid

            for match in re.finditer(r'<programme[^>]*>.*?</programme>', content_str, re.DOTALL):
                prog_xml = match.group(0)
                cid_match = re.search(r'channel="([^"]+)"', prog_xml)
                if cid_match:
                    epg_programmes[cid_match.group(1)].append(prog_xml)

            print(f"    ✅ Found {len(epg_exact)} channels")
        except Exception as e:
            print(f"[EPG ERROR] Failed to load {url}: {e}")

    return epg_exact, epg_norm, epg_programmes

def main():
    download_logos(LOGO_MAP)

    epg_exact, epg_norm, epg_progs = load_epg_channels()
    id_map_norm = {norm(k): v for k, v in ID_MAP.items()}

    print("\n📡 Fetching M3U...")
    r = requests.get(M3U_URL, timeout=30)
    lines = r.text.splitlines()

    kept, epg_needed = [], set()
    matched_count = 0
    blocked_count = 0

    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.startswith('#EXTINF'):
            i += 1
            continue

        extinf, url = line, lines[i+1]
        i += 2

        tid = re.search(r'tvg-id="([^"]*)"', extinf).group(1)
        tname = re.search(r'tvg-name="([^"]*)"', extinf).group(1) if 'tvg-name="' in extinf else ''
        n = norm(tid)

        if is_excluded(tid, tname):
            continue
        
        # BLOCKED CHANNEL → NO EPG
        if n in EPG_BLOCKED:
            blocked_count += 1
            extinf = apply_logo(extinf, tid, tname)
            kept.append((extinf, url))
            continue

        # MATCHING
        epg_id = None
        if tid in epg_exact:
            epg_id = tid
        if not epg_id:
            epg_id = epg_norm.get(n)
        if not epg_id:
            epg_id = id_map_norm.get(n)

        # BLOCK EPG ID ITSELF
        if epg_id and norm(epg_id) in EPG_BLOCKED:
            epg_id = None

        if epg_id:
            epg_needed.add(epg_id)
            extinf = re.sub(r'tvg-id="[^"]*"', f'tvg-id="{epg_id}"', extinf)
            matched_count += 1

        extinf = apply_logo(extinf, tid, tname)
        kept.append((extinf, url))

    # OUTPUT
    with open(M3U_OUTPUT, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        for extinf, url in kept:
            f.write(f"{extinf}\n{url}\n")

    with open(EPG_OUTPUT, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n<tv>\n')
        for eid in sorted(epg_needed):
            f.write(f'  <channel id="{eid}"><display-name>{eid}</display-name></channel>\n')
        for eid in sorted(epg_needed):
            for prog in epg_progs.get(eid, []):
                f.write(f'  {prog}\n')
        f.write('</tv>\n')

    print(f"\n✅ Created {M3U_OUTPUT}")
    print(f"✅ Created {EPG_OUTPUT} ({matched_count} channels with EPG)")
    print(f"🚫 Blocked EPG for {blocked_count} channels")

if __name__ == '__main__':
    main()
