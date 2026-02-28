import requests
import re

M3U_URL = "https://iptv-org.github.io/iptv/languages/ara.m3u"
EPG_URL = "https://iptv-org.github.io/epg/guides/ar/epgshare01.xml.gz"

EXCLUDE_WORDS = ('radio', 'fm', 'chaine', 'distro.tv', 'kurd', 'kurdistan', 'tchad')

# COMPREHENSIVE MAP: Based on your uploaded file contents
ID_MAP = {
    # Abu Dhabi & Sports
    'AbuDhabiSports1.ae': 'AD.Sports.1.HD.ae',
    'AbuDhabiSports2.ae': 'AD.Sports.2.HD.ae',
    'AbuDhabiEmirates.ae': 'Abu.Dhabi.HD.ae',
    'YasTV.ae': 'Yas.TV.HD.ae',
    
    # Dubai Network
    'DubaiTV.ae': 'Dubai.HD.ae',
    'SamaDubai.ae': 'Sama.Dubai.HD.ae',
    'DubaiOne.ae': 'Dubai.One.HD.ae',
    'DubaiSports1.ae': 'Dubai.Sports.1.HD.ae',
    'DubaiSports2.ae': 'Dubai.Sports.2.ae',
    'DubaiRacing1.ae': 'Dubai.Racing.1.HD.ae',
    'DubaiZaman.ae': 'Dubai.Zaman.ae',
    
    # MBC Network
    'MBC1.ae': 'MBC.1.ae',
    'MBC2.ae': 'MBC.2.ae',
    'MBC3.ae': 'MBC.3.ae',
    'MBC4.ae': 'MBC.4.ae',
    'MBCAction.ae': 'MBC.Action.ae',
    'MBCDrama.ae': 'MBC.Drama.ae',
    'MBCBollywood.ae': 'MBC.Bollywood.ae',
    'MBCMasr.eg': 'MBC.Masr.HD.ae',
    'MBCMasr2.eg': 'MBC.Masr.2.HD.ae',
    
    # Rotana Network
    'RotanaCinema.sa': 'Rotana.Cinema.KSA.ae',
    'RotanaCinemaEgypt.eg': 'Rotana.Cinema.Egypt.ae',
    'RotanaClassic.sa': 'Rotana.Classic.ae',
    'RotanaDrama.sa': 'Rotana.Drama.ae',
    'RotanaKhalijia.sa': 'Rotana.Khalijia.ae',
    'RotanaMousica.sa': 'Rotana.Music.ae',
    
    # News & Others
    'AlArabiya.net': 'Al.Arabiya.HD.ae',
    'AlHadath.net': 'Al.Hadath.ae',
    'SkyNewsArabia.ae': 'Sky.News.Arabia.HD.ae',
    'AlJazeera.qa': 'Aljazeera.id',
    'BBCArabic.uk': 'BBC.Arabic.ae',
    'France24Arabic.fr': 'France.24.Arabic.ae',
    'RTArabic.ru': 'RT.Arabic.HD.ae'
}

def clean_line(line):
    # Auto-fix dots for any channel not in the map
    # Example: SaudiEkhbariya -> Saudi.Ekhbariya
    for old_id, new_id in ID_MAP.items():
        if f'tvg-id="{old_id}"' in line:
            return line.replace(f'tvg-id="{old_id}"', f'tvg-id="{new_id}"')
    
    # Generic fix: Add dots between camelCase words
    if 'tvg-id="' in line:
        line = re.sub(r'([a-z])([A-Z])', r'\1.\2', line)
    return line

def process_iptv():
    print("🚀 Starting M3U to EPG Synchronization...")
    try:
        r = requests.get(M3U_URL, timeout=30)
        lines = r.text.splitlines()
        final_m3u = ["#EXTM3U"]
        
        for i in range(len(lines)):
            if lines[i].startswith("#EXTINF"):
                if not any(word in lines[i].lower() for word in EXCLUDE_WORDS):
                    fixed_line = clean_line(lines[i])
                    if i + 1 < len(lines) and lines[i+1].startswith("http"):
                        final_m3u.append(fixed_line)
                        final_m3u.append(lines[i+1])
        
        with open("curated-live.m3u", "w", encoding="utf-8") as f:
            f.write("\n".join(final_m3u))
            
        r_epg = requests.get(EPG_URL)
        with open("arabic-epg.xml.gz", "wb") as f:
            f.write(r_epg.content)
        print("✅ Success! Mapping expanded.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    process_iptv()
