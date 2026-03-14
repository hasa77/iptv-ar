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

#"normalized_m3u_tvg_id": "Exact_EPG_Channel_ID"
ID_MAP = {
    'AbuDhabiEmirates.ae@HD': 'Dubai.ae',
    'AbuDhabiSports1.ae@HD': 'Dubai.Sports.1.ae',
    'AbuDhabiSports2.ae@SD': 'Dubai.Sports.2.ae',
    'Al Mamlaka TV HD': 'Al.Mamlaka.TV.HD.ae',
    'Al.Arabiya.Programs': 'AlArabiya.net',
    'Al.Arabiya.Business.ae': 'AlArabiyaBusiness.ae',
    'AlArabyTV.qa@SD': 'AlAraby.qa',
    'AlArabyTV2.qa@SD': 'AlAraby2.qa',
    'AlerthAlnabawiChannel.jo@SD': 'AlerthAlnabawi.jo',
    'Al.Qamar.TV.ae': 'AlQamar.ae',
    'AlalamNewsChannelSyria.sy@SD': 'AlalamSyria.ir',
    'Al.Iraqia.News': 'Al.Iraqiya.HD.ae',
    'Al.Maaref.TV': 'AlMaaref.bh',  
    'alarabiyahd': 'Al.Arabiya.HD.ae',
    'Al.Hadath.ae': 'AlHadath.net', 
    'dubaitv': 'Dubai.HD.ae',
    'samadubai': 'Sama.Dubai.HD.ae',
    'dubaione': 'Dubai.One.HD.ae',
    'dubaisports1': 'Dubai.Sports.1.HD.ae',
    'Dubai.Sports.2.ae': 'DubaiSports2.ae',
    'dubairacing': 'Dubai.Racing.1.HD.ae',
    'Dubai.Zaman.ae': 'DubaiZaman.ae',
    'BaynounahTV.ae@HD': 'Sama.Dubai.ae',
    'Majid.ae@HD': 'One.Tv.ae',
    'Iraq Future': 'IraqFuture.iq@SD',
    'Iraq Future TV': 'IraqFuture.iq@SD',
    'Iraq.Future.TV.ae': 'IraqFuture.iq@SD',
    'mbc1sa': 'MBC1.ae', #MBC 1 
    'mbc1eg': 'MBC.Masr.ae', #mbc 1 EGYPT
    'mbc2sa': 'MBC2.ae',
    'mbc3sa': 'MBC3.ae',
    'mbc4sa': 'MBC4.ae',
    'mbc5sa': 'MBC5.ae',
    'MBC.Action.ae': 'MBCAction.ae',
    'mbcdramasa': 'MBCDrama.ae', #MBC DRAMA
    'mbcdramausa': 'MBC.Drama.ae', #MBC DRAMA USA
    'mbcmasreg': 'MBC.Masr.ae',
    'mbcmasr2eg': 'MBC.Masr.2.ae',
    'mbcmasrdramaeg': 'MBC.Masr.ae', #MBC MASR DRAMA
    'mbcplusdrama': 'MBC.Drama.Plus.ae', #MBC PLUS DRAMA
    'MBCIraq.iq@SD': 'MBC.Iraq.HD.ae',
    'MBC Iraq': 'MBC.Iraq.HD.ae',
    'Noor.DubaiTV.ae': 'NoorDubaiTV.ae',
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
    'skynewsarabia': 'Sky.News.Arabia.HD.ae',
    'Jordan.TV.HD.ae': 'JordanTV.jo',
    'BBC.Arabic.ae': 'BBCArabic.uk',
    'France.24.Arabic.ae': 'France24Arabic.fr',
    'RT.Arabic.HD.ae': 'RTArabic.ru',
    'Saudi.Quran.TV.HD.ae': 'SaudiQuran.sa',
    'Saudi.Sunna.TV.HD.ae': 'SaudiSunnah.sa',
    'Saudi.Al.Ekhbariya.HD.ae': 'SaudiEkhbariya.sa',
    'Sharjah.Quran.TV.ae': 'SharjahQuran.ae',
    'spacetoon': 'Space.Toon.ae',
    'Yas.TV.HD.ae': 'YasTV.ae',
    '1.Baghdad.ae': '1Baghdad.ae',
    'Ajman.TV.HD.ae': 'AjmanTV.ae@SD',
    'Al.Hurra.TV.HD.ae': 'AlHurra.us@SD',
    'Al.Iraqiya.News.HD.ae': 'AlIraqiaNews.iq@SD',
    'Al.Iraqiya.Sport.HD.ae': 'AlIraqiaSport.iq@SD',
    'Al.Janoub.ae': 'AlJanoub.iq@SD',
    'Al.Jazeera.HD.ae': 'AlJazeera.qa@Arabic',
    'Al.Jazeera.Mobasher.2.HD.ae': 'AlJazeeraMubasherBroadcast2.qa@SD',
    'Al.Jazeera.Mobasher.HD.ae': 'AlJazeeraMubasher.qa@SD',
    'Al.Masar.TV.HD.ae': 'AlMasarTV.ly@SD',
    'Al.Mashhad.ae': 'AlMashhad.ae@SD',
    'Al.Mawqef.ae': 'AlMawqefTV.iq@SD',
    'Al.Rabiaa.HD.ae': 'AlRabiaaTV.iq@SD',
    'Al.sharqiya.News.HD.ae': 'AlSharqiyaNews.iq@SD',
    'Alkass.Four.ae': 'AlkassFour.qa@SD',
    'Alkass.One.HD.ae': 'AlkassOne.qa@SD',
    'Alkass.Three.ae': 'AlkassThree.qa@SD',
    'Alkass.Two.HD.ae': 'AlkassTwo.qa@SD',
    'Almasirah.TV.ae': 'AlMasirah.ye@SD',
    'Almasirah.TV.Mubasher.ae': 'AlMasirahMubasher.ye@SD',
    'Asharq.News.HD.ae': 'AsharqNews.sa@SD',
    'Baghdad.TV.ae': 'BaghdadTV.iq@SD',
    'CNBC.Arabiya.ae': 'CNBCArabiya.ae@SD',
    'DW.Arabia.HD.ae': 'DWArabia.de@SD',
    'falestinona.TV.ae': 'FalestinonaTV.ps@SD',
    'Halab.Today.TV.ae': 'HalabTodayTV.sy@SD',
    'Hawa.Baghdad.ae': 'HawaBaghdad.iq@SD',
    'Iraq.Future.TV.ae': 'IraqFuture.iq@SD',
    'Nile.News.ae': 'NileNews.eg@SD',
    'Palestine.Live.HD.ae': 'PalestineLive.ps@SD',
    'Syria.One.TV.ae': 'SyriaTV.sy@SD',
    'Syria.TV.HD.ae': 'SyriaTV.sy@SD',
    'UTV.Iraq.ae': 'UTV.iq@SD',
    'Watan.TV.ae': 'WatanTV.eg@SD',
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
