import requests
import re
import gzip
import xml.etree.ElementTree as ET
import io

M3U_URL = "https://iptv-org.github.io/iptv/languages/ara.m3u"
EPG_URL = "https://epgshare01.online/epgshare01/epg_ripper_ALL_SOURCES1.xml.gz"

# --- [DIAGNOSTIC FUNCTION] ---
def check_source_quality(epg_bytes):
    print("🔍 Diagnostic: Checking if source EPG actually contains data...")
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(epg_bytes)) as g:
            context = ET.iterparse(g, events=('end',))
            title_count = 0
            desc_count = 0
            for event, elem in context:
                tag = elem.tag.split('}')[-1]
                if tag == 'title' and elem.text and len(elem.text.strip()) > 0:
                    title_count += 1
                if tag == 'desc' and elem.text and len(elem.text.strip()) > 0:
                    desc_count += 1
                
                # If we find at least 5 populated titles, the source is likely fine
                if title_count > 5:
                    print(f"✅ Source looks GOOD. Found populated titles and descriptions.")
                    return True
                elem.clear()
        print("❌ Source Alert: Scanned EPG and found NO text inside <title> or <desc> tags.")
        return False
    except Exception as e:
        print(f"⚠️ Diagnostic failed: {e}")
        return False

# 1. Target Suffixes (Must have one of these)
AR_SUFFIXES = ('.ae', '.dz', '.eg', '.iq', '.jo', '.kw', '.lb', '.ly', '.ma', 
               '.om', '.ps', '.qa', '.sa', '.sd', '.sy', '.tn', '.ye', '.me', '.ar')

# 2. Keywords to Keep (Force include if found)
AR_KEYWORDS = ('mbc', 'bein', 'osn', 'rotana', 'alkass', 'aljazeera', 'arabic', 'nilesat', 
               'sharjah', 'dubai', 'abu dhabi', 'alarabiya', 'hadath', 'cbc', 'dmc', 'on ent',
               'royal', 'art ', 'ssc ', 'syria', 'iraq', 'lebanon', 'al jadeed', 'lbc')

# 3. YOUR STRICT REJECTION LIST
EXCLUDE_WORDS = (
    'radio', 'fm', 'chaine', 'distro.tv', 'argentina', 'colombia', 'telefe', 'eltrece', 
    'kurd', 'kurdistan', 'rudaw', 'waar', 'duhok',      # Kurdish
    'mbc 1', 'mbc 1 usa',                               # Redundant (Keep only MBC 1 Masr)
    'morocco', 'maroc', 'maghreb', '2m',                # Morocco
    'tunisia', 'tunisie', 'ttv', 'hannibal',            # Tunisia
    'libya', 'libye', '218 tv',                         # Libya
    'iran', 'persian', 'farsi', 'gem tv',               # Iran
    'afghanistan', 'afghan', 'pashto', 'tolo',           # Afghanistan
    'tchad', 'chad', 'turkmenistan', 'turkmen',         # Central Africa / Central Asia
    'babyfirst',                                        # US English Kids
    'eritrea', 'eri-tv',                                # Eritrea
    'i24news'                                           # Israel-based news
)

# 4. ID Mapping for TiviMate Guide Matching
ID_MAP = {
    # Abu Dhabi Network
    'AbuDhabiSports1.ae': 'AD.Sports.1.HD.ae',
    'AbuDhabiSports2.ae': 'AD.Sports.2.HD.ae',
    'AbuDhabiEmirates.ae': 'Abu.Dhabi.HD.ae',
    'AbuDhabiTV.ae': 'Abu.Dhabi.HD.ae',
    'YasTV.ae': 'Yas.TV.HD.ae',
    # Dubai Network
    'DubaiTV.ae': 'Dubai.HD.ae',
    'DubaiSports1.ae': 'Dubai.Sports.1.HD.ae',
    'DubaiSports2.ae': 'Dubai.Sports.2.ae',
    'DubaiRacing1.ae': 'Dubai.Racing.1.HD.ae',
    'SamaDubai.ae': 'Sama.Dubai.HD.ae',
    'DubaiOne.ae': 'Dubai.One.HD.ae',
    'DubaiZaman.ae': 'Dubai.Zaman.ae',
    'NoorDubaiTV.ae': 'Noor.DubaiTV.ae',
    'OneTv.ae': 'One.Tv.ae',
    # MBC Network
    'MBC1.ae': 'MBC.1.ae',
    'MBC2.ae': 'MBC.2.ae',
    'MBCMasr.eg': 'MBC.Masr.HD.ae',
    'MBCMasr2.eg': 'MBC.Masr.2.HD.ae',
    # Rotana Network
    'RotanaCinema.sa': 'Rotana.Cinema.KSA.ae',
    'RotanaCinemaEgypt.eg': 'Rotana.Cinema.Egypt.ae',
    'RotanaDrama.sa': 'Rotana.Drama.ae',
    'RotanaClassic.sa': 'Rotana.Classic.ae',
    'RotanaKhalijia.sa': 'Rotana.Khalijia.ae',
    # Saudi & Sports Specific
    'KSA-Sports-1.sa': 'KSA.sports.1.ae',
    'KSA-Sports-2.sa': 'KSA.sports.2.HD.ae',
    'OnTimeSports1.eg': 'On.Time.Sports.HD.ae',
    'OnTimeSports2.eg': 'On.Time.Sport.2.HD.ae',
    'SharjahSports.ae': 'Sharjah.Sports.HD.ae',
    'JordanTV.jo': 'Jordan.TV.HD.ae',
    # News & International
    'AlArabiya.net': 'Al.Arabiya.HD.ae',
    'AlHadath.net': 'Al.Hadath.ae',
    'SkyNewsArabia.ae': 'Sky.News.Arabia.HD.ae',
    'BBCArabic.uk': 'BBC.Arabic.ae',
    'France24Arabic.fr': 'France.24.Arabic.ae',
    'RTArabic.ru': 'RT.Arabic.HD.ae',
    'SaudiEkhbariya.sa': 'Saudi.Al.Ekhbariya.HD.ae',
    # Religious
    'SaudiQuran.sa': 'Saudi.Quran.TV.HD.ae',
    'SaudiSunnah.sa': 'Saudi.Sunna.TV.HD.ae',
    'SharjahQuran.ae': 'Sharjah.Quran.TV.ae'
}

def clean_line(line):
    # 1. First, strip @HD/@SD from the line just for mapping purposes
    # This ensures "MBC1.ae@HD" becomes "MBC1.ae" so it matches your ID_MAP
    line = re.sub(r'(@[A-Z0-9]+)', '', line)

    # 2. Apply specific ID mapping
    for old_id, new_id in ID_MAP.items():
        if f'tvg-id="{old_id}"' in line:
            return line.replace(f'tvg-id="{old_id}"', f'tvg-id="{new_id}"')
    
    # 3. Generic fix for camelCase (e.g., DubaiZaman -> Dubai.Zaman)
    if 'tvg-id="' in line:
        line = re.sub(r'([a-z])([A-Z])', r'\1.\2', line)
    return line
  
def process_iptv():
    print("🚀 Running ID_MAP Priority Filter (Targeting 39+)...")
    try:
        # 1. Initialize with your Gold Standard: Every 'value' from your ID_MAP
        # This ensures we search for these 39 IDs regardless of the M3U content
        wanted_ids = set(ID_MAP.values())
        
        # Also keep a set of the 'keys' to check which M3U channels to map
        mapping_keys = set(ID_MAP.keys())
        
        r = requests.get(M3U_URL, timeout=30)
        lines = r.text.splitlines()
        final_m3u = ["#EXTM3U"]
        
        def normalize(s):
            return re.sub(r'[^a-z0-9]', '', s.lower()) if s else ""

        # 2. Process M3U to add extra "bonus" IDs and clean the lines
        for i in range(len(lines)):
            if lines[i].startswith("#EXTINF"):
                line_lower = lines[i].lower()
                if (any(s in line_lower for s in AR_SUFFIXES) or any(k in line_lower for k in AR_KEYWORDS)) and not any(w in line_lower for w in EXCLUDE_WORDS):
                    
                    # Extract the current ID
                    id_match = re.search(r'tvg-id="([^"]+)"', lines[i])
                    if id_match:
                        current_id = id_match.group(1).split('@')[0]
                        # If it's NOT in our map, add it as a "silver" fuzzy search
                        if current_id not in mapping_keys:
                            wanted_ids.add(current_id)
                            wanted_ids.add(normalize(current_id))

                    # Apply your ID_MAP to the line for the final output
                    fixed_line = clean_line(lines[i])
                    
                    if i + 1 < len(lines) and lines[i+1].startswith("http"):
                        final_m3u.append(fixed_line)
                        final_m3u.append(lines[i+1])

        print(f"✅ Search list built. Total unique IDs to scan: {len(wanted_ids)}")

        # 3. EPG Processing (Two-Pass for Stream Reliability)
        response = requests.get(EPG_URL, timeout=120)
        epg_bytes = response.content

      # --- [CALL DIAGNOSTIC HERE] ---
        check_source_quality(epg_bytes)
      
        matched_real_ids = set()
        channel_elements = []

        # Pass 1: Find Channels
        with gzip.GzipFile(fileobj=io.BytesIO(epg_bytes)) as g:
            context = ET.iterparse(g, events=('end',))
            for event, elem in context:
                tag = elem.tag.split('}')[-1]
                if tag == 'channel':
                    cid = elem.get('id')
                    # Match against exact ID_MAP values or M3U variants
                    if cid in wanted_ids or normalize(cid) in wanted_ids:
                        matched_real_ids.add(cid)
                        channel_elements.append(ET.tostring(elem, encoding='utf-8'))
                elem.clear()

       # --- PASS 2: EXTRACT PROGRAMS (Case-Insensitive Match) ---
        # Create a lowercase lookup for the matched IDs to be safe
        matched_ids_lower = {cid.lower(): cid for cid in matched_real_ids}

        with gzip.open("arabic-epg.xml.gz", "wb") as f_out:
            f_out.write(b'<?xml version="1.0" encoding="utf-8"?>\n<tv>\n')
            
            # Write the channel headers first
            for c in channel_elements:
                f_out.write(c)
            
            # Re-scan for programmes
            with gzip.GzipFile(fileobj=io.BytesIO(epg_bytes)) as g:
                context = ET.iterparse(g, events=('end',))
                for event, elem in context:
                    tag = elem.tag.split('}')[-1]
                    if tag == 'programme':
                        p_channel = elem.get('channel')
                        if p_channel:
                            # Match the program's channel ID to our found list (case-insensitive)
                            if p_channel in matched_real_ids or p_channel.lower() in matched_ids_lower:
                                f_out.write(ET.tostring(elem, encoding='utf-8'))
                    
                    elem.clear() # Keep memory usage low
            
            f_out.write(b'</tv>')

        print(f"📊 Final Results: {len(matched_real_ids)} channels with full program data saved.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
      
if __name__ == "__main__":
    process_iptv()
