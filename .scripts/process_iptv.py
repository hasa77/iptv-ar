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

# ── Explicit bridges: M3U tvg-id  →  EPG channel id ──────────────────────────
# Left side  = exact tvg-id value as it appears in the iptv-org M3U
# Right side = exact channel id as it appears in the EPG source
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

# ── Helpers ──────────────────────────────────────────────────────────────────

def norm(s):
    """Normalise: strip punctuation, lowercase."""
    if not s:
        return ''
    s = re.sub(r'(@[A-Z0-9]+)', '', s)
    return re.sub(r'[._\-\s/]', '', s).lower()


def is_excluded(channel_id, name=''):
    """Return True if this channel should be dropped."""
    combined = norm(channel_id) + ' ' + norm(name)
    return any(x in combined for x in EXCLUDE_WORDS)


# ── Step 1: Load all EPG channels ────────────────────────────────────────────

def load_epg_channels():
    """
    Returns:
      epg_exact      : set of exact EPG channel ids
      epg_norm       : dict  norm(id) -> exact EPG channel id
      epg_programmes : dict  exact_id -> list of ET element bytes
    """
    epg_exact      = set()
    epg_norm       = {}
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

    print(f"   ✅ EPG has {len(epg_exact)} unique channel ids, "
          f"{sum(len(v) for v in epg_programmes.values())} programmes total\n")
    return epg_exact, epg_norm, epg_programmes


# ── Step 2: Fetch M3U and resolve each channel to an EPG id ──────────────────

def fetch_and_resolve_m3u(epg_exact, epg_norm):
    """
    Returns list of dicts:
      { 'extinf': original #EXTINF line,
        'url':    stream URL,
        'tvg_id': original tvg-id from M3U,
        'epg_id': resolved EPG channel id (or None) }
    """
    # Build normalised ID_MAP lookup: norm(M3U tvg-id) -> EPG channel id
    id_map_norm = {norm(k): v for k, v in ID_MAP.items()}

    print(f"🌐 Fetching M3U: {M3U_URL}")
    r = requests.get(M3U_URL, timeout=30)
    lines = r.text.splitlines()
    print(f"   ✅ {len(lines)} lines fetched\n")

    channels = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('#EXTINF'):
            extinf = line
            url    = lines[i + 1] if i + 1 < len(lines) else ''
            i += 2

            tid_m  = re.search(r'tvg-id="([^"]*)"',   extinf)
            name_m = re.search(r'tvg-name="([^"]*)"', extinf)
            tvg_id = tid_m.group(1)  if tid_m  else ''
            name   = name_m.group(1) if name_m else ''

            # Try to resolve to EPG id
            epg_id = None
            n = norm(tvg_id)

            if n in id_map_norm:                     # 1. explicit map
                candidate = id_map_norm[n]
                if candidate in epg_exact:
                    epg_id = candidate
            if not epg_id and tvg_id in epg_exact:   # 2. exact
                epg_id = tvg_id
            if not epg_id and n in epg_norm:         # 3. fuzzy
                epg_id = epg_norm[n]

            channels.append({
                'extinf': extinf,
                'url':    url,
                'tvg_id': tvg_id,
                'name':   name,
                'epg_id': epg_id,
            })
        else:
            i += 1

    return channels


# ── Step 3: Filter and write outputs ─────────────────────────────────────────

def write_outputs(channels, epg_exact, epg_norm, epg_programmes):
    kept_channels   = []
    epg_ids_needed  = set()
    no_epg          = []

    for ch in channels:
        if is_excluded(ch['tvg_id'], ch['name']):
            continue

        if ch['epg_id']:
            epg_ids_needed.add(ch['epg_id'])
            kept_channels.append(ch)
        else:
            no_epg.append(ch)

    # ── Write M3U ────────────────────────────────────────────────────────────
    print(f"📝 Writing M3U: {len(kept_channels)} channels with EPG  "
          f"({len(no_epg)} dropped — no EPG match)")

    with open(M3U_OUTPUT, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        for ch in kept_channels:
            # Rewrite tvg-id in the EXTINF line to the EPG id
            extinf = re.sub(r'tvg-id="[^"]*"', f'tvg-id="{ch["epg_id"]}"', ch['extinf'])
            f.write(extinf + '\n')
            f.write(ch['url'] + '\n')

    # ── Write EPG ────────────────────────────────────────────────────────────
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

    # ── Debug: what didn't get EPG ────────────────────────────────────────────
    print(f"\n❓ Channels WITHOUT EPG match ({len(no_epg)}) — add to ID_MAP if you want them:")
    for ch in sorted(no_epg, key=lambda x: x['name']):
        print(f"   tvg-id={ch['tvg_id']!r:45s}  name={ch['name']!r}")

    print(f"\n✅ Done!  →  {M3U_OUTPUT}  +  {EPG_OUTPUT}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("🚀 Arabic IPTV Sync\n")
    epg_exact, epg_norm, epg_programmes = load_epg_channels()
    channels = fetch_and_resolve_m3u(epg_exact, epg_norm)
    write_outputs(channels, epg_exact, epg_norm, epg_programmes)


if __name__ == '__main__':
    main()
