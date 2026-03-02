import requests
import re
import gzip
import xml.etree.ElementTree as ET
import io
import os
from collections import defaultdict

M3U_URL = "https://iptv-org.github.io/iptv/languages/ara.m3u"
OUTPUT_FILE = "arabic-epg.xml"
EPG_SOURCES = [
    "https://epgshare01.online/epgshare01/epg_ripper_ALL_SOURCES1.xml.gz",
    #Combined Egypt, Lebanon, Saudi, UAE, GB, USA
    "https://iptv-epg.org/files/epg-meyqso.xml"
]

ID_MAP = {
    # Abu Dhabi Network
    'AbuDhabiTV.ae': 'Abu.Dhabi.HD.ae',
    'AbuDhabiEmirates.ae': 'Abu.Dhabi.HD.ae',
    'AbuDhabiSports1.ae': 'AD.Sports.1.HD.ae',
    'AbuDhabiSports2.ae': 'AD.Sports.2.HD.ae',
    'YasTV.ae': 'Yas.TV.HD.ae',

    # Dubai Network
    'DubaiTV.ae': 'Dubai.HD.ae',
    'SamaDubai.ae': 'Sama.Dubai.HD.ae',
    'DubaiOne.ae': 'Dubai.One.HD.ae',
    'NoorDubaiTV.ae': 'Noor.DubaiTV.ae',
    'DubaiSports1.ae': 'Dubai.Sports.1.HD.ae',
    'DubaiSports2.ae': 'Dubai.Sports.2.ae',
    'DubaiRacing1.ae': 'Dubai.Racing.ae',
    'DubaiZaman.ae': 'Dubai.Zaman.ae',
    'OneTv.ae': 'One.Tv.ae',

    # MBC Network
    'MBC1.ae': 'MBC.1.ae',
    'MBC2.ae': 'MBC.2.ae',
    'MBC3.ae': 'MBC.3.ae',
    'MBC4.ae': 'MBC.4.ae',
    'MBCAction.ae': 'MBC.Action.ae',
    'MBCDrama.ae': 'MBC.Drama.ae',
    'MBCMasr.eg': 'MBC.Masr.HD.ae',
    'MBCMasr2.eg': 'MBC.Masr.2.HD.ae',
    'Wanasah.ae': 'Wanasah.ae',

    # Rotana Network
    'RotanaCinema.sa': 'Rotana.Cinema.KSA.ae',
    'RotanaCinemaEgypt.eg': 'Rotana.Cinema.Egypt.ae',
    'RotanaDrama.sa': 'Rotana.Drama.ae',
    'RotanaClassic.sa': 'Rotana.Classic.ae',
    'RotanaKhalijia.sa': 'Rotana.Khalijia.ae',
    'RotanaMousica.sa': 'Rotana.Mousica.ae',

    # Sports & News
    'KSA-Sports-1.sa': 'KSA.Sports.1.ae',
    'KSA-Sports-2.sa': 'KSA.Sports.2.HD.ae',
    'OnTimeSports1.eg': 'On.Time.Sports.HD.ae',
    'OnTimeSports2.eg': 'On.Time.Sport.2.HD.ae',
    'SharjahSports.ae': 'Sharjah.Sports.HD.ae',
    'AlArabiya.net': 'Al.Arabiya.HD.ae',
    'AlHadath.net': 'Al.Hadath.ae',
    'SkyNewsArabia.ae': 'Sky.News.Arabia.HD.ae',
    'JordanTV.jo': 'Jordan.TV.HD.ae',
    'BBCArabic.uk': 'BBC.Arabic.ae',
    'France24Arabic.fr': 'France.24.Arabic.ae',
    'RTArabic.ru': 'RT.Arabic.HD.ae',

    # Religious
    'SaudiQuran.sa': 'Saudi.Quran.TV.HD.ae',
    'SaudiSunnah.sa': 'Saudi.Sunna.TV.HD.ae',
    'SaudiEkhbariya.sa': 'Saudi.Al.Ekhbariya.HD.ae',
    'SharjahQuran.ae': 'Sharjah.Quran.TV.ae'
}

EXCLUDE_WORDS = (
    'radio', 'fm', 'chaine', 'distro.tv', 'argentina', 'colombia', 'telefe', 'eltrece', 
    'kurd', 'kurdistan', 'rudaw', 'waar', 'duhok',      # Kurdish
	'mbc 1', 'mbc 1 usa',                               # Redundant (Keep only MBC 1 Masr)
    'morocco', 'maroc', 'maghreb', '2m',                # Morocco
    'tunisia', 'tunisie', 'ttv', 'hannibal',            # Tunisia
    'libya', 'libye', '218 tv',                         # Libya
    'iran', 'persian', 'farsi', 'gem tv', 'mbcpersia',  # Iran
    'afghanistan', 'afghan', 'pashto', 'tolo',          # Afghanistan
    'tchad', 'chad', 'turkmenistan', 'turkmen',         # Central Africa / Central Asia
    'babyfirst',                                        # US English Kids
    'eritrea', 'eri-tv',                                # Eritrea
    'i24news',                                          # Israel-based news
    'india', 'hindi', 'tamil', 'telugu', 'malayalam',   # India
    'korea', 'korean', 'kbs', 'sbs', 'tvn',             # Korea
    'zealand', 'nz', 'australia', 'canterbury',         # NZ/AU
    'turk', 'trrt', 'atv.tr', 'fox.tr',                 # Turkish
	'milb', 'ncaa', 'broncos', 'lobos', 'santa-clara',  # US Sports Junk
    'canada', 'cbc.ca', 'cbcmusic', 'halifax', 'ottawa', 'winnipeg', 'calgary', 'vancouver', 'montreal',                 # Canadian CBC
    'kmbc', 'wmbc', 'tmbc', 'mbc1usa', 'samsung',       # US MBC Look-alikes
	'milb', 'ncaa', 'broncos', 'lobos', 'santa-clara',  # US Sports
    'mlb-', 'cubs', 'guardians', 'white-sox', 'reds',   # Baseball specific
    'canada', 'cbc.ca', 'cbcmusic',                     # Canadian CBC
    'kmbc', 'wmbc', 'tmbc', 'mbc1usa', 'samsung',       # US MBC
    'español', 'wellbeing', 'xtra',             		# Spanish / Health junk
    '-cd', '-ld', 'locals1', 'global.bc',				# US local station patterns
	'engelsk',											# Denmark
)



def normalise_id(cid):
    """Strip punctuation and lowercase for fuzzy comparison."""
    if not cid:
        return ""
    clean = re.sub(r'(@[A-Z0-9]+)', '', cid)
    return re.sub(r'[._\-\s]', '', clean).lower()


def get_m3u_channels():
    """
    Fetch the live M3U and return:
      - allowed_ids: exact set of tvg-id values
      - norm_to_exact: normalised_id -> exact tvg-id  (for fuzzy lookup)
      - channel_names: dict of tvg-id -> tvg-name
    """
    allowed_ids = set()
    norm_to_exact = {}
    channel_names = {}

    # Pre-load all ID_MAP targets
    for target_id in ID_MAP.values():
        allowed_ids.add(target_id)
        norm_to_exact[normalise_id(target_id)] = target_id

    print(f"🌐 Fetching live M3U from: {M3U_URL}")
    try:
        r = requests.get(M3U_URL, timeout=30)
        # Parse each EXTINF line to grab tvg-id and tvg-name together
        for line in r.text.splitlines():
            if line.startswith('#EXTINF'):
                tid = re.search(r'tvg-id="([^"]*)"', line)
                tname = re.search(r'tvg-name="([^"]*)"', line)
                if tid and tid.group(1):
                    exact = tid.group(1)
                    allowed_ids.add(exact)
                    norm_to_exact[normalise_id(exact)] = exact
                    if tname:
                        channel_names[exact] = tname.group(1)

        print(f"✅ Found {len(allowed_ids)} unique channel IDs in M3U.")
    except Exception as e:
        print(f"⚠️  Could not fetch M3U: {e}")

    return allowed_ids, norm_to_exact, channel_names


def resolve_id(source_id, allowed_ids, norm_to_exact, reverse_map):
    """
    Try to resolve a source EPG channel id to a known M3U tvg-id.
    Resolution order:
      1. Explicit ID_MAP bridge  (normalised key -> mapped target)
      2. Exact match in allowed_ids
      3. Normalised fuzzy match
    Returns final_id string or None.
    """
    if not source_id:
        return None

    norm = normalise_id(source_id)

    # 1. Explicit bridge map
    if norm in reverse_map:
        return reverse_map[norm]

    # 2. Exact match
    if source_id in allowed_ids:
        return source_id

    # 3. Normalised fuzzy match
    if norm in norm_to_exact:
        return norm_to_exact[norm]

    return None


def process_iptv():
    print("🚀 Starting Smart Mapper...")

    allowed_ids, norm_to_exact, channel_names = get_m3u_channels()

    # Build reverse map: normalised EPG-source-id -> M3U target id
    reverse_map = {normalise_id(k): v for k, v in ID_MAP.items()}

    channel_elements = []
    program_elements = []
    processed_channels = set()

    # Stats for debugging
    matched_counts = defaultdict(int)
    unmatched_sample = set()

    for url in EPG_SOURCES:
        file_name = url.split('/')[-1]
        print(f"📥 Processing EPG: {file_name}")
        try:
            r = requests.get(url, timeout=60)
            content = r.content
            if not content:
                print(f"  ⚠️  Empty response from {file_name}")
                continue

            f = (gzip.GzipFile(fileobj=io.BytesIO(content))
                 if content[:2] == b'\x1f\x8b'
                 else io.BytesIO(content))

            for event, elem in ET.iterparse(f, events=('end',)):
                tag = elem.tag.split('}')[-1]

                if tag == 'programme':
                    source_id = elem.get('channel', '')
                    final_id = resolve_id(source_id, allowed_ids, norm_to_exact, reverse_map)

                    if final_id:
                        norm = normalise_id(source_id)
                        # Only apply exclude filter for non-bridged channels
                        if norm not in reverse_map:
                            low_id = final_id.lower()
                            if any(x in low_id for x in EXCLUDE_WORDS):
                                elem.clear()
                                continue

                        elem.set('channel', final_id)
                        program_elements.append(ET.tostring(elem, encoding='utf-8'))
                        matched_counts[final_id] += 1

                        if final_id not in processed_channels:
                            processed_channels.add(final_id)
                            display = channel_names.get(final_id, final_id)
                            chan_xml = (
                                f'<channel id="{final_id}">'
                                f'<display-name>{display}</display-name>'
                                f'</channel>'
                            )
                            channel_elements.append(chan_xml.encode('utf-8'))
                    else:
                        # Collect unmatched samples for the debug report (limit noise)
                        if len(unmatched_sample) < 200:
                            unmatched_sample.add(source_id)

                    elem.clear()

        except Exception as e:
            print(f"  ⚠️  Error processing {file_name}: {e}")

    # ── Debug report ────────────────────────────────────────────────────────────
    print(f"\n📊 Match summary: {len(processed_channels)} channels, "
          f"{len(program_elements)} programmes")
    print("\n✅ Matched channels (programme count):")
    for cid, cnt in sorted(matched_counts.items(), key=lambda x: -x[1]):
        print(f"   {cid:50s}  {cnt:>5} programmes")

    print(f"\n❓ Sample of UNMATCHED EPG source IDs ({len(unmatched_sample)} shown):")
    for uid in sorted(unmatched_sample)[:100]:
        print(f"   {uid}")

    # ── Write output ─────────────────────────────────────────────────────────────
    if program_elements:
        print(f"\n💾 Writing {len(program_elements)} programs for "
              f"{len(processed_channels)} channels to {OUTPUT_FILE} …")
        with open(OUTPUT_FILE, "wb") as f_out:
            f_out.write(b'<?xml version="1.0" encoding="utf-8"?>\n<tv>\n')
            for c in channel_elements:
                f_out.write(c + b'\n')
            for p in program_elements:
                f_out.write(p + b'\n')
            f_out.write(b'</tv>')
        print(f"✅ Done! Output: {OUTPUT_FILE}")
    else:
        print("❌ No programmes matched — output file not written.")


if __name__ == "__main__":
    process_iptv()
