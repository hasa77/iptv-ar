import requests
import re

M3U_URL = "https://iptv-org.github.io/iptv/languages/ara.m3u"
EPG_URL = "https://iptv-org.github.io/epg/guides/ar/epgshare01.xml.gz"

EXCLUDE_WORDS = (
    'radio', 'fm', 'chaine', 'distro.tv', 'kurd', 'kurdistan', 'rojava', 
    'iran', 'farsi', 'babyfirst', 'eritrea', 'i24news', 'tchad', 'turkmenistan'
)

def fix_id(line):
    # This replaces common IDs with the dotted EPG format
    # Example: AbuDhabiSports1.ae -> Abu.Dhabi.Sports.1.ae
    if 'AbuDhabiSports' in line:
        line = re.sub(r'AbuDhabiSports(\d)', r'Abu.Dhabi.Sports.\1', line)
    if 'AbuDhabiTV' in line:
        line = line.replace('AbuDhabiTV', 'Abu.Dhabi.TV')
    if 'AlArabiya' in line:
        line = line.replace('Alarabiya', 'Al.Arabiya')
    return line

def process_iptv():
    print("Syncing M3U IDs to match EPG...")
    try:
        r_m3u = requests.get(M3U_URL, timeout=30)
        lines = r_m3u.text.splitlines()
        filtered_m3u = ["#EXTM3U"]
        
        for i in range(len(lines)):
            if lines[i].startswith("#EXTINF"):
                line_content = lines[i]
                # 1. Apply Rejection Filter
                if not any(word in line_content.lower() for word in EXCLUDE_WORDS):
                    # 2. Fix the ID to match EPG dots
                    fixed_line = fix_id(line_content)
                    
                    if i + 1 < len(lines) and lines[i+1].startswith("http"):
                        filtered_m3u.append(fixed_line)
                        filtered_m3u.append(lines[i+1])
        
        with open("curated-live.m3u", "w", encoding="utf-8") as f:
            f.write("\n".join(filtered_m3u))
        
        # Download EPG directly
        r_epg = requests.get(EPG_URL)
        with open("arabic-epg.xml.gz", "wb") as f:
            f.write(r_epg.content)
            
        print("Success! IDs synchronized.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    process_iptv()
