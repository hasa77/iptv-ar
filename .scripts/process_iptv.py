import requests
import re

M3U_URL = "https://iptv-org.github.io/iptv/languages/ara.m3u"
EPG_URL = "https://iptv-org.github.io/epg/guides/ar/epgshare01.xml.gz"

# Words to remove junk channels
EXCLUDE_WORDS = (
    'radio', 'fm', 'chaine', 'distro.tv', 'kurd', 'kurdistan', 'rojava', 
    'tchad', 'turkmenistan', 'iran', 'farsi'
)

# SYNC MAP: Translates M3U IDs to match your specific EPG file exactly
ID_MAP = {
    'AbuDhabiSports1.ae': 'AD.Sports.1.HD.ae',
    'AbuDhabiSports2.ae': 'AD.Sports.2.HD.ae',
    'AbuDhabiEmirates.ae': 'Abu.Dhabi.HD.ae',
    'DubaiSports1.ae': 'Dubai.Sports.1.HD.ae',
    'DubaiSports2.ae': 'Dubai.Sports.2.ae',
    'DubaiRacing1.ae': 'Dubai.Racing.1.HD.ae',
    'MBCMasr.eg': 'MBC.Masr.HD.ae',
    'MBCMasr2.eg': 'MBC.Masr.2.HD.ae',
    'AlArabiya.net': 'Al.Arabiya.HD.ae',
    'SkyNewsArabia.ae': 'Sky.News.Arabia.HD.ae',
    'SamaDubai.ae': 'Sama.Dubai.HD.ae',
    'DubaiOne.ae': 'Dubai.One.HD.ae'
}

def process_iptv():
    print("🚀 Starting M3U to EPG Synchronization...")
    try:
        r = requests.get(M3U_URL, timeout=30)
        lines = r.text.splitlines()
        final_m3u = ["#EXTM3U"]
        
        for i in range(len(lines)):
            if lines[i].startswith("#EXTINF"):
                line = lines[i]
                
                # 1. Filter out junk
                if any(word in line.lower() for word in EXCLUDE_WORDS):
                    continue
                
                # 2. Sync IDs using the map
                for old_id, new_id in ID_MAP.items():
                    if f'tvg-id="{old_id}"' in line:
                        line = line.replace(f'tvg-id="{old_id}"', f'tvg-id="{new_id}"')
                
                if i + 1 < len(lines) and lines[i+1].startswith("http"):
                    final_m3u.append(line)
                    final_m3u.append(lines[i+1])
        
        with open("curated-live.m3u", "w", encoding="utf-8") as f:
            f.write("\n".join(final_m3u))
            
        # Download the EPG
        r_epg = requests.get(EPG_URL)
        with open("arabic-epg.xml.gz", "wb") as f:
            f.write(r_epg.content)
            
        print("✅ Success! M3U and EPG are now synchronized.")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    process_iptv()
