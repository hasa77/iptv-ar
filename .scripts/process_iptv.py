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

# ── Logo overrides ────────────────────────────────────────────────────────────
# Key = stripped tvg-id (no @SD/@HD suffix), matched with norm()
# Value = direct image URL
LOGO_MAP = {
    # Abu Dhabi TV
    'AbuDhabiTV.ae':            'https://upload.wikimedia.org/wikipedia/commons/d/d7/Abu_Dhabi_TV_logo_2023.png',
    'AbuDhabiEmirates.ae':      'https://upload.wikimedia.org/wikipedia/commons/d/d7/Abu_Dhabi_TV_logo_2023.png',

    # Ajman
    'AjmanTV.ae':               'https://static.wikia.nocookie.net/logopedia/images/b/b3/Ajman_TV_Logo_1996.png/revision/latest?cb=20241210014941',

    # Ajyal
    'AjyalTV.ps':               'https://upload.wikimedia.org/wikipedia/en/2/23/AjyalTVLogo2014.png',

    # Al Aqsa
    'AlAqsaTV.ps':              'https://cdn.broadbandtvnews.com/wp-content/uploads/2024/01/04120752/Al-Aqsa-TV.jpg',
}

# ── Explicit EPG ID bridges ───────────────────────────────────────────────────
# Key   = M3U tvg-id stripped of @suffix
# Value = exact EPG channel id
ID_MAP = {
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

EXCLUDE_WORDS = (
    'radio', '.fm', 'chaine', 'distrotv',
    'kurd', 'kurdistan', 'rudaw', 'waar', 'duhok',
    'morocco', 'maroc', 'maghreb',
    'tunisia', 'tunisie',
    'libya', 'libye', '218tv',
    'iran', 'persian', 'farsi', 'gemtv', 'mbcpersia',
    'afghanistan', 'afghan', 'pashto', 'tolo',
    'babyfirst',
    'eritrea', 'eritv',
    'i24news',
    'india', 'hindi', 'tamil', 'telugu', 'malayalam',
    'korea', 'korean',
    'zealand', 'australia',
    'turk', 'trrt',
    'canada', 'cbcca', 'cbcmusic',
    'kmbc', 'wmbc', 'tmbc', 'mbc1usa',
    'espanol', 'wellbeing',
    'engelsk',
    'argentina', 'colombia',
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def strip_quality(s):
    """Remove trailing @SD, @HD, @Arabic, @Plus1, etc."""
    return re.sub(r'@\S+$', '', s or '').strip()

def norm(s):
    s = strip_quality(s)
    return re.sub(r'[._\-\s/]', '', s).lower()

def is_excluded(tvg_id, name=''):
    combined = norm(tvg_id) + ' ' + norm(name)
    return any(x in combined for x in EXCLUDE_WORDS)

def apply_logo(extinf_line, tvg_id):
    """Inject or replace tvg-logo in an EXTINF line if we have one."""
    stripped = strip_quality(tvg_id)
    n = norm(stripped)
    # Build a norm->url lookup
    logo_url = None
    for k, v in LOGO_MAP.items():
        if norm(k) == n:
            logo_url = v
            break
    if not logo_url:
        return extinf_line  # nothing to change

    if 'tvg-logo=' in extinf_line:
        # Replace existing logo
        return re.sub(r'tvg-logo="[^"]*"', f'tvg-logo="{logo_url}"', extinf_line)
    else:
        # Insert before the closing comma+name section
        return re.sub(r'(#EXTINF:[^,]*)', rf'\1 tvg-logo="{logo_url}"', extinf_line, count=1)


# ── Step 1: Load EPG ──────────────────────────────────────────────────────────

def load_epg_channels():
    epg_exact      = set()
    epg_norm       = {}
    epg_programmes = defaultdict(list)

    for url in EPG_SOURCES:
        fname = url.split('/')[-1]
        print(f"📥 Loading EPG: {fname}")
        try:
            r = requests.get(url, timeout=60)
            content = r.content
            if not content:
                print("   ⚠️  Empty"); continue

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

            stripped = strip_quality(tvg_id)
            n        = norm(stripped)

            epg_id = None
            if n in id_map_norm:
                candidate = id_map_norm[n]
                if candidate in epg_exact:
                    epg_id = candidate
            if not epg_id and stripped in epg_exact:
                epg_id = stripped
            if not epg_id and n in epg_norm:
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

    logos_applied = 0

    # M3U
    print(f"📝 Writing M3U: {len(kept)} channels with EPG")
    with open(M3U_OUTPUT, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        for ch in kept:
            extinf = re.sub(r'tvg-id="[^"]*"', f'tvg-id="{ch["epg_id"]}"', ch['extinf'])
            new_extinf = apply_logo(extinf, ch['tvg_id'])
            if new_extinf != extinf:
                logos_applied += 1
            f.write(new_extinf + '\n' + ch['url'] + '\n')

    print(f"🖼️  Logos applied: {logos_applied}")

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

    print(f"\n❓ {len(no_epg)} channels without EPG:")
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
