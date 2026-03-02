import requests
import re
import gzip
import xml.etree.ElementTree as ET
import io
import os
from collections import defaultdict

M3U_URL = "https://iptv-org.github.io/iptv/languages/ara.m3u"
EPG_OUTPUT     = "arabic-epg.xml"
M3U_OUTPUT     = "curated-live.m3u"
EPG_SOURCES = [
    "https://epgshare01.online/epgshare01/epg_ripper_ALL_SOURCES1.xml.gz",
    #Combined Egypt, Lebanon, Saudi, UAE, GB, USA
    "https://iptv-epg.org/files/epg-meyqso.xml"
]

# Explicit overrides where even stripped fuzzy match won't work.
# Key   = M3U tvg-id (with or without @suffix — we strip before lookup)
# Value = exact EPG channel id
ID_MAP = {
    'AlJazeera.qa':        'AlJazeera.qa',
    'France24.fr':         'France24Arabic.fr',
    'DW.de':               'DWArabic.de',
    'BBCArabic.uk':        'BBCArabic.uk',
    'RTArabic.ru':         'RTArabic.ru',
    'JordanTV.jo':         'JordanTV.jo',
    'MBCMasr.eg':          'MBCMasr.eg',
    'MBCMasr2.eg':         'MBCMasr2.eg',
    'MBC1Egypt.eg':        'MBCMasr.eg',
    'RotanaCinemaEgypt.eg':'RotanaCinemaEgypt.eg',
    'KSA-Sports-1.sa':     'KSA-Sports-1.sa',
    'KSA-Sports-2.sa':     'KSA-Sports-2.sa',
    'OnTimeSports1.eg':    'OnTimeSports1.eg',
    'OnTimeSports2.eg':    'OnTimeSports2.eg',
    'AlArabiya.ae':        'AlArabiya.net',
    'Alarabiya.ae':        'AlArabiya.net',
    'AlEkhbariya.sa':      'SaudiEkhbariya.sa',
    'SkyNewsArabia.ae':    'SkyNewsArabia.ae',
}

EXCLUDE_WORDS = (
    'radio', 'fm',
    'kurd', 'kurdistan', 'rudaw', 'waar', 'duhok',
    'iran', 'persian', 'farsi', 'gemtv', 'mbcpersia', 'kawthar', 'wilayah',
    'afghanistan', 'afghan', 'pashto', 'tolo',
    'babyfirst',
    'eritrea',
    'i24news',
    'hindi', 'tamil', 'telugu', 'malayalam',
    'korean',
    'turk', 'trrt',
    'cbcca', 'cbcmusic',
    'kmbc', 'wmbc', 'tmbc', 'mbc1usa',
    'wellbeing',
    'engelsk',
    'argentina', 'colombia',
    'rojavatv', 'ronahitv', 'welatv', 'zagrostv',   # Kurdish Syria
    'chada', 'medi1',                                # Morocco
    'jawhara', 'mosaiquepm',                         # Tunisia
    'february', 'tanasuh', 'wasat',                  # Libya
    'dabanga',                                       # Sudan
    'teletChad', 'rtd4',                             # Chad/Djibouti
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def strip_quality(s):
    """Remove trailing @SD, @HD, @Arabic, @Plus1, etc."""
    return re.sub(r'@\S+$', '', s or '').strip()

def norm(s):
    """Normalise: strip quality suffix, punctuation, lowercase."""
    s = strip_quality(s)
    s = re.sub(r'[._\-\s/]', '', s)
    return s.lower()

def is_excluded(tvg_id, name=''):
    combined = norm(tvg_id) + ' ' + norm(name)
    return any(x in combined for x in EXCLUDE_WORDS)


# ── Step 1: Load EPG ──────────────────────────────────────────────────────────

def load_epg_channels():
    epg_exact      = set()
    epg_norm       = {}          # norm(id) -> exact id
    epg_programmes = defaultdict(list)

    for url in EPG_SOURCES:
        fname = url.split('/')[-1]
        print(f"📥 Loading EPG: {fname}")
        try:
            r = requests.get(url, timeout=60)
            content = r.content
            if not content:
                print("   ⚠️  Empty response"); continue

            f = (gzip.GzipFile(fileobj=io.BytesIO(content))
                 if content[:2] == b'\x1f\x8b' else io.BytesIO(content))

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

    print(f"   ✅ {len(epg_exact)} EPG channels, "
          f"{sum(len(v) for v in epg_programmes.values())} programmes\n")
    return epg_exact, epg_norm, epg_programmes


# ── Step 2: Fetch M3U and resolve ─────────────────────────────────────────────

def fetch_and_resolve_m3u(epg_exact, epg_norm):
    # norm(stripped M3U id) -> EPG id
    id_map_norm = {norm(k): v for k, v in ID_MAP.items()}

    print(f"🌐 Fetching M3U: {M3U_URL}")
    r = requests.get(M3U_URL, timeout=30)
    lines = r.text.splitlines()
    print(f"   ✅ {len(lines)} lines\n")

    channels = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('#EXTINF'):
            url = lines[i + 1] if i + 1 < len(lines) else ''
            i += 2

            tid_m  = re.search(r'tvg-id="([^"]*)"',   line)
            name_m = re.search(r'tvg-name="([^"]*)"', line)
            tvg_id = tid_m.group(1)  if tid_m  else ''
            name   = name_m.group(1) if name_m else ''

            stripped = strip_quality(tvg_id)   # e.g. BBCArabic.uk@SD -> BBCArabic.uk
            n        = norm(stripped)           # e.g. bbcarabicuk

            epg_id = None
            if n in id_map_norm:               # 1. explicit map
                candidate = id_map_norm[n]
                if candidate in epg_exact:
                    epg_id = candidate
            if not epg_id and stripped in epg_exact:   # 2. exact stripped
                epg_id = stripped
            if not epg_id and n in epg_norm:           # 3. fuzzy
                epg_id = epg_norm[n]

            channels.append({
                'extinf': line, 'url': url,
                'tvg_id': tvg_id, 'name': name, 'epg_id': epg_id,
            })
        else:
            i += 1

    return channels


# ── Step 3: Write outputs ─────────────────────────────────────────────────────

def write_outputs(channels, epg_programmes):
    kept, no_epg = [], []

    for ch in channels:
        if is_excluded(ch['tvg_id'], ch['name']):
            continue
        (kept if ch['epg_id'] else no_epg).append(ch)

    epg_ids = {ch['epg_id'] for ch in kept}

    # M3U — rewrite tvg-id to the EPG id TiviMate expects
    print(f"📝 Writing M3U: {len(kept)} channels with EPG  "
          f"({len(no_epg)} without EPG — kept but no guide)")
    with open(M3U_OUTPUT, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        for ch in kept:
            extinf = re.sub(r'tvg-id="[^"]*"', f'tvg-id="{ch["epg_id"]}"', ch['extinf'])
            f.write(extinf + '\n' + ch['url'] + '\n')

    # EPG
    total = sum(len(epg_programmes[e]) for e in epg_ids)
    print(f"💾 Writing EPG: {len(epg_ids)} channels, {total} programmes")
    with open(EPG_OUTPUT, 'wb') as f:
        f.write(b'<?xml version="1.0" encoding="utf-8"?>\n<tv>\n')
        for eid in sorted(epg_ids):
            f.write(f'<channel id="{eid}"><display-name>{eid}</display-name></channel>\n'.encode())
        for eid in sorted(epg_ids):
            for prog in epg_programmes[eid]:
                f.write(prog + b'\n')
        f.write(b'</tv>')

    # Debug: unmatched
    print(f"\n❓ {len(no_epg)} channels without EPG (not written to M3U):")
    for ch in sorted(no_epg, key=lambda x: x['tvg_id']):
        print(f"   {ch['tvg_id']}")

    print(f"\n✅ Done!  →  {M3U_OUTPUT}  +  {EPG_OUTPUT}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("🚀 Arabic IPTV Sync\n")
    epg_exact, epg_norm, epg_programmes = load_epg_channels()
    channels = fetch_and_resolve_m3u(epg_exact, epg_norm)
    write_outputs(channels, epg_programmes)

if __name__ == '__main__':
    main()

