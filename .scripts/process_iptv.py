import requests
import re
import gzip
import xml.etree.ElementTree as ET
import io
import os
from collections import defaultdict

M3U_URL = "https://iptv-org.github.io/iptv/languages/ara.m3u"
M3U_OUTPUT = "curated-live.m3u"
EPG_OUTPUT = "arabic-epg.xml"
EPG_SOURCES = [
    "https://epgshare01.online/epgshare01/epg_ripper_ALL_SOURCES1.xml.gz",
    #Combined Egypt, Lebanon, Saudi, UAE, GB, USA
    "https://iptv-epg.org/files/epg-meyqso.xml"
]

LOGO_MAP = {
    # Al Araby Network
    'Al.Araby.TV': 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/96/ALARABY_ARABIC.png/960px-ALARABY_ARABIC.png',
    'Al.Araby.TV2': 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/96/ALARABY_ARABIC.png/960px-ALARABY_ARABIC.png',
    
    # News & Info
    'Al.Ekhbariya': 'https://upload.wikimedia.org/wikipedia/commons/e/e3/%D8%A7%D9%84%D9%82%D9%86%D8%A7.png',
    'Al.Ghad.TV': 'https://upload.wikimedia.org/wikipedia/commons/0/06/AlGhad_TV.png',
    
    # Iraq
    'Al.Iraqiya': 'https://static.wikia.nocookie.net/logopedia/images/1/18/Al_Iraqiya_Logo.png/revision/latest?cb=20210309003710',
    'Al.Iraqia.News': 'https://static.wikia.nocookie.net/logopedia/images/1/18/Al_Iraqiya_Logo.png/revision/latest?cb=20210309003710',
    
    # Al Jazeera Variants
    'Al.Jazeera.Mubasher.ae': 'https://upload.wikimedia.org/wikipedia/ar/c/c3/%D8%B4%D8%B9%D8%A7%D8%B1_%D9%82%D9%86%D8%A7%D8%A9_%D8%A7%D9%84%D8%AC%D8%B2%D9%8I%D8%B1%D8%A9_%D9%85%D8%A8%D8%A7%D8%B4%D8%B1.svg',
    'Al.Jazeera.Mubasher24': 'https://upload.wikimedia.org/wikipedia/ar/c/c3/%D8%B4%D8%B9%D8%A7%D8%B1_%D9%82%D9%86%D8%A7%D8%A9_%D8%A7%D9%84%D8%AC%D8%B2%D9%8I%D8%B1%D8%A9_%D9%85%D8%A8%D8%A7%D8%B4%D8%B1.svg',
    'Al.Jazeera.Mubasher.Broadcast2': 'https://upload.wikimedia.org/wikipedia/ar/c/c3/%D8%B4%D8%B9%D8%A7%D8%B1_%D9%82%D9%86%D8%A7%D8%A9_%D8%A7%D9%84%D8%AC%D8%B2%D9%8I%D8%B1%D8%A9_%D9%85%D8%A8%D8%A7%D8%B4%D8%B1.svg',
    
    # Religious & Others
    'Al.Maaref.TV': 'https://almaaref.ch/wp-content/uploads/2021/10/Almaaref-Logo.png',
    'Al.Mamlaka.TV': 'https://upload.wikimedia.org/wikipedia/en/8/8a/Al-Mamlaka_TV_logo.png',

    # Abu Dhabi TV
    'AbuDhabiTV.ae':            'https://upload.wikimedia.org/wikipedia/commons/d/d7/Abu_Dhabi_TV_logo_2023.png',
    'AbuDhabiEmirates.ae':      'https://upload.wikimedia.org/wikipedia/commons/d/d7/Abu_Dhabi_TV_logo_2023.png',

    # Ajman
    'AjmanTV.ae':               'https://static.wikia.nocookie.net/logopedia/images/b/b3/Ajman_TV_Logo_1996.png/revision/latest?cb=20241210014941',

    # Al Aqsa
    'AlAqsaTV.ps':              'https://cdn.broadbandtvnews.com/wp-content/uploads/2024/01/04120752/Al-Aqsa-TV.jpg',

    # --- MBC Group ---
    'MBC1.ae': 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c0/MBC_1_Logo.svg/960px-MBC_1_Logo.svg.png',
    'MBC1Egypt.eg@HD': 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c0/MBC_1_Logo.svg/960px-MBC_1_Logo.svg.png',
    'MBC3USA.us@SD': 'https://static.wikia.nocookie.net/logopedia/images/f/f1/Mbc_tree.svg/revision/latest?cb=20250711113001',
    'MBC4.ae': 'https://static.wikia.nocookie.net/logopedia/images/7/73/Mbc_for.svg/revision/latest?cb=20250711112900',
    'MBC5.ae@SD': 'https://upload.wikimedia.org/wikipedia/commons/0/0f/MBC5_logo.png?_=20200521144912',
    'MBCMasr.eg': 'https://static.wikia.nocookie.net/logopedia/images/b/bd/Mbc_egypt.svg/revision/latest?cb=20250711110419',
    'MBCMasr2.eg': 'https://static.wikia.nocookie.net/logopedia/images/5/53/MBC_Masr_2_Logo.svg/revision/latest?cb=20250710124414',
    'MBCMasrUSA.us@SD': 'https://static.wikia.nocookie.net/logopedia/images/b/bd/Mbc_egypt.svg/revision/latest?cb=20250711110419',
    'MBCDrama.ae': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTCQuAFbk-Pg3pHSO1xrAxTUJY3ZaGZNgu18Q&s',
    'MBCPlusDrama.sa': 'https://upload.wikimedia.org/wikipedia/commons/2/2a/MBC_Drama_Plus_TV_Channel_Logo.png',
    'MBCDramaUSA.us@SD': 'https://upload.wikimedia.org/wikipedia/commons/e/e9/MBC_Drama_Logo.svg',
    'MBCIraq.iq@SD': 'https://static.wikia.nocookie.net/logopedia/images/6/6e/MBCIraq.jpeg/revision/latest/scale-to-width-down/1000?cb=20191214070733',
    'MBC.Bollywood.ae': 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/4b/MBC_Bollywood_Logo.svg/1280px-MBC_Bollywood_Logo.svg.png',

    # --- Al Jazeera ---
    'AlJazeera.qa@Arabic': 'https://static.wikia.nocookie.net/logopedia/images/0/0f/Al_Jazeera.svg/revision/latest?cb=20171112085348',
    'AlJazeeraMubasher.qa@SD': 'https://static.wikia.nocookie.net/logopedia/images/9/95/Al_Jazeera_Mubasher_II.svg/revision/latest?cb=20231231100551',
    'AlJazeeraMubasher24.qa@SD': 'https://static.wikia.nocookie.net/logopedia/images/9/95/Al_Jazeera_Mubasher_II.svg/revision/latest?cb=20231231100551',
    'AlJazeeraMubasherBroadcast2.qa@SD': 'https://static.wikia.nocookie.net/logopedia/images/9/95/Al_Jazeera_Mubasher_II.svg/revision/latest?cb=20231231100551',
    'AlJazeeraDocumentary.qa@SD': 'https://static.wikia.nocookie.net/logopedia/images/e/e8/Al_Jazeera_Documentary_Channel.png/revision/latest?cb=20120211112107',

    # --- Sports ---
    'AbuDhabiSports1.ae': 'https://static.wikia.nocookie.net/logopedia/images/0/0f/AbuDhabiSportsTV2023.png/revision/latest?cb=20230921160459',
    'AbuDhabiSports2.ae': 'https://static.wikia.nocookie.net/logopedia/images/0/0f/AbuDhabiSportsTV2023.png/revision/latest?cb=20230921160459',
    'BahrainSports1.bh@SD': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR9CEJXbMzbYPUX2ULkYAWmskUVAvYLAETCLQ&s',
    'BahrainSports2.bh@SD': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR9CEJXbMzbYPUX2ULkYAWmskUVAvYLAETCLQ&s',
    'JordanSport.jo@SD': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcT2LTBDvhF-a5CZLFvM65U5TqFSCY0UdEANIA&s',

    # --- News & Regionals ---
    'AlhurraIraq.us@SD': 'https://upload.wikimedia.org/wikipedia/commons/0/06/AlHurra_logo.svg',
    'AlIraqia.iq@SD': 'https://static.wikia.nocookie.net/logopedia/images/1/18/Al__Logo.png/revision/latest?cb=20210309003710',
    'FalastiniTV.ps@SD': 'https://www.falastini.tv/wp-content/uploads/2017/02/logo.png',
    'AlHorreyaTV.us@SD': 'https://yt3.googleusercontent.com/idxhelPtWa-U8GvXsSdMidgl6yGagtDwUspkCMWxz31bTA6FyMFCYKU5xDzXybVw3ZjmGIHY=s900-c-k-c0x00ffffff-no-rj',
    'AlRafidainTV.tr@SD': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSK4NEActEu3lsaYHkDumTXs9jDaMCPDml0YQ&s',
    'AlSunnahAlNabawiyahTV.sa@SD': 'https://www.tvyayinakisi.com/wp-content/uploads/2020/05/al-sunnah-al-nabawiyah-tv-logo.png',
    'SharjahTV.ae@SD': 'https://static.wikia.nocookie.net/logopedia/images/a/a6/Sharjah_TV_Logo_2011.png/revision/latest/scale-to-width-down/300?cb=20241212234207',
    'AlIttihadTV.lb@SD': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS5T8fq0fAxPmJK7XZOOXZRju9DdKgN_N3LmA&s',
    'AlJadeed.lb@SD': 'https://upload.wikimedia.org/wikipedia/en/1/17/Al_Jadeed.PNG',
    'AlRasheedTV.iq@SD': 'https://upload.wikimedia.org/wikipedia/en/b/b5/Al_Rasheed_TV_logo.png',
    'IraqFuture.iq@SD': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSBIJR2f3buhd-IbO9num-iCNbc0LDAaVzrVQ&s',

    'Al.Hadath.ae': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/ae/Al_Hadath_TV_logo_2023.svg/1920px-Al_Hadath_TV_logo_2023.svg.png',
    'AlYaumTV.ae': 'https://upload.wikimedia.org/wikipedia/commons/5/56/%D9%81%D9%86%D8%A7%D8%A9_%D8%A7%D9%84%D9%82%D9%86%D8%A7%D8%A9_%D8%A7%D9%84%D9%8A%D9%82%D8%B8%D8%A9.jpg',
    'AjyalTV.ps': 'https://upload.wikimedia.org/wikipedia/en/2/23/AjyalTVLogo2014.png',

    'AlRayyanTV.qa@SD': 'https://upload.wikimedia.org/wikipedia/commons/e/ed/%D8%B4%D8%B9%D8%A7%D8%B1_%D8%A7%D9%84%D9%82%D9%86%D8%A7%D8%A9_2014-03-24_07-56.png',
    'AlRayyanOldTV.qa@SD': 'https://alrayyan.qa/wp-content/uploads/2023/10/qadeem-logo2-300x134.gif',
    'AlSaudiya.sa@SD': 'https://upload.wikimedia.org/wikipedia/en/d/d6/Al-Saudia_TV_Logo_2018.png',
    'AlShallalTV.ae@SD': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQqmoNes6R_R0yx7nk1E9suapmPYyT4bhS65Q&s',
    'AlSharqiyaMinKabla.ae@SD': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcT3kYi61BFxLNpoz_iqDx6Rk-E3noS6D874Sw&s',
    'AlWoustaTV.ae@SD': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQuqFcmzwsiTK-vLy7olcX0lSPinClIgF716A&s',
    'Al-Sharqiya': 'https://upload.wikimedia.org/wikipedia/commons/1/1e/Al_Sharqiya.png',
    'Althania.sy@SD': 'https://www.fadaatmedia.com/sites/default/files/2025-03/Logo%20syria%202%20Color.png',
    'AmmanTV.jo@SD': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRWI2bNVA0-INJ3WFInusjdyyhgOrVYQYGBDw&s',
    'BahrainInternational.bh@SD': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTH4-rpzsYt37RLrnzP08u9mAd3atzJ31keMA&s',
    'BahrainTV.bh@SD': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSKqVIPA1s5YgGMsk3YiRbTZOierr5Lg0AxEQ&s',
    'CBC.eg@SD': 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/5c/Cbctv.svg/250px-Cbctv.svg.png',
    'ElOussraTV.mr@SD': 'https://www.lyngsat.com/logo/tv/ee/el-oussra-tv-mr.png',
    'ElsharqTV.tr@SD': 'https://elsharq.tv/wp-content/uploads/2025/10/ELSHARQ-TV645646-e1761838412808.png',
    'ERiTV1.er@SD': 'https://upload.wikimedia.org/wikipedia/commons/0/01/EritTV_Logo.png',
    'FutureTV.lb@SD': 'https://upload.wikimedia.org/wikipedia/en/b/bc/Future_tv_logo_2012.jpg',
    'HalaLondon.uk@SD': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTqylrFx4KoPrq4XswHRn6ackepLntyp2cNhQ&s',
    'HalaTV.il@SD': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR9hC8umj_HunhNKbllCtSaCX4pMD9zIamkkw&s',
    'JordanTV.jo@SD': 'https://static.wikia.nocookie.net/iepfanon/images/d/df/Jordan_TV.png/revision/latest?cb=20240121200521',
    'KTV1.kw@SD': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRH1YwZw4L26eNJx51HStZkNIfCbMrXAi9ggA&s',
    'LanaTV.lb@SD': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSGIFIP3-1NLtmkesGoujJ1fpfVzVJ9Og622Q&s',
    'OmanTV.om@SD': 'https://upload.wikimedia.org/wikipedia/commons/4/4a/Saghhjjdegh.jpg',
    'OTV.lb@SD': 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/05/OTV_%28logo%29.svg/1280px-OTV_%28logo%29.svg.png',
    'QatarTelevision.qa@SD': 'https://upload.wikimedia.org/wikipedia/en/8/88/Qatar_TV_logo.png',
    'QatarTelevision2.qa@SD': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSVuRil1BT-pR9h4oy9khMgQxpLFVFI1qqaUg&s',
    'WatanTV.eg@SD': 'https://upload.wikimedia.org/wikipedia/commons/6/68/Watan_tv_logo.jpg',
    'AlHadath.sa': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSTn1QrjoG3q6_ku5D054jCd9vZFPJ2YRDpWg&s',
    'BBCArabic.uk@SD': 'https://upload.wikimedia.org/wikipedia/commons/b/b8/Logo_BBC_Arabic.png',
    'HalabTodayTV.sy@SD': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQa0qcmi0Vtpx5UHjj8c1Jkc4gQEtqjVuGWTg&s',
    'SkyNewsArabia.ae@HD': 'https://play-lh.googleusercontent.com/phi19fJAMvOxBWN4M1lb-EXIybEIaW176n-5uWXyne6IKL0eLUvWVItWhGE3HcqucxMy=w240-h480-rw',
    'SkyNewsArabia.ae@SD': 'https://play-lh.googleusercontent.com/phi19fJAMvOxBWN4M1lb-EXIybEIaW176n-5uWXyne6IKL0eLUvWVItWhGE3HcqucxMy=w240-h480-rw',
    'SyriaTV.sy@SD': 'https://upload.wikimedia.org/wikipedia/en/d/d2/Syria_TV_logo.svg',
    'VoiceofLebanon.lb@SD': 'https://yt3.googleusercontent.com/0g7bspn9-AVSgdMLQNA8unukgzhWBE35dTu0zookmfLpb5wa47DPUDsKndtIc3RAdFz54cvSbg=s900-c-k-c0x00ffffff-no-rj',
    'AlHiwarTV.uk@SD': 'https://m.media-amazon.com/images/I/71fWor-YyUL.png',
    'PalestineEdu.ps@SD': 'https://upload.wikimedia.org/wikipedia/commons/7/7f/Palestine_Satellite_Channel_Logo.png',
    'AsharqDocumentary.sa@SD': 'https://static.wikia.nocookie.net/logopedia/images/a/a8/Asharq_Doc_23.png/revision/latest?cb=20230924082531',
    'NationalGeographicAbuDhabi.ae@HD': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS-RR0tIHK2kmDd4sUOsJ95ijgr4lAsDZ-4XA&s',
    'RotanaAflamPlus.sa@SD': 'https://www.ethnicchannels.com/images/channeldetail/rotana-aflam/rotana-aflam.png',
    'RoyaDrama.jo@SD': 'https://royamediagroup.com/imgs/royat.png',
    'Ch4Teen.kw@SD': 'https://ch14.tv/img/logo.png',
    'ArabicaTV.lb@SD': 'https://play-lh.googleusercontent.com/vJ3tvJIwbdKtQ2cnG8j38hHBHvLXsq59wlG5MGhRfjh8lNpxgvfsush-5v9IabjVCQ',
    'AghaniAghaniTV.lb@SD': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQQ71udLceuolkA09cpq4ingoSzGhexsqFyuw&s',
    'JawharaTV.tn@SD': 'https://m.jawharafm.net/ar/img/logo_jfmtv_fini.png',
    'MarinaTV.kw@SD': 'https://upload.wikimedia.org/wikipedia/commons/0/0d/MarinaTV-Logo-2023.jpg',
    'MelodyHits.ca@SD': 'https://upload.wikimedia.org/wikipedia/en/c/c1/Melody_Hits.png',
    'Wanasah.ae@SD': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQAAwrDpA7J5DQ25STCwHRunmBOiMaZ-KWX4g&s',
    'AlQuranAlKareemTV.sa@SD': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR2pRmfi-mTBumXgbPboYNK3yIBHtX-uw-AKg&s',
    'AlJawadainTV.iq@SD': 'https://yt3.googleusercontent.com/K53EvSf8Pu048rumnr1AVQC4lFaymDtTlS-XEU6jyf5D3ZEzXJ57MByZIZh5EiNvUhqevuaIyg=s900-c-k-c0x00ffffff-no-rj',
    'AlMajdHolyQuran.sa@SD': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR99o10KFH_1PpVaKGdsV5uvsJRkjKP3y1xEg&s',
    'AlerthAlnabawiChannel.jo@SD': 'https://upload.wikimedia.org/wikipedia/id/1/15/Logo_Nabawi_TV.png',
    'AlImanTV.lb@SD': 'https://play-lh.googleusercontent.com/0xzwga2oE-6bUp7tggVMlMKCbPVmfXf0xwKpUF6UQ_qPveg3riA6EeE29COrCXKUhGTN',
    'AlistiqamaTV.om@SD': 'https://www.istiqama.tv/wp-content/uploads/2024/04/channel_logo-1024x557.png',
    'AlmagdTVMiddleEast.us@SD': 'https://play-lh.googleusercontent.com/uwjQhw4MHZ37JCaxTN9Wct3kbqmMOoi7JEdwzviG60uaBSiSrN-Z4-g6XADP3v8rrPc',
    'Alquran.iq@SD': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTandtY_hQQEDBt0aRmndEl4WhBXq3C0mL9VA&s',
    'BahrainQuran.bh@SD': 'https://mir-s3-cdn-cf.behance.net/project_modules/1400_webp/05a1e4174424521.651d0c6f4d98c.png',
    'BeitolAbbasTVChannel.iq@SD': 'https://beitolabbas.tv/wp-content/uploads/2023/01/Logo-1.png',
    'ImamHusseinTV2.iq@SD': 'https://imamhussein.tv/image2021/TV02.png',
    'IqraaArabic.sa@SD': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQbnLd9ilUrcxhSNACnNFmXprT8DwTsvQyz6g&s',
    'IqraaQuran.sa@SD': 'https://upload.wikimedia.org/wikipedia/commons/c/c4/Iqraa_Logo.svg',
    'KTVAlQurain.kw@SD': 'https://static.wikia.nocookie.net/logopedia/images/2/2e/Qurain_TV.jpg/revision/latest?cb=20220327145418',
}

# ── Explicit bridges: M3U tvg-id  →  EPG channel id ──────────────────────────
# Left side  = exact tvg-id value as it appears in the iptv-org M3U
# Right side = exact channel id as it appears in the EPG source
ID_MAP = {

    'Al.Arabiya.Programs': 'AlArabiya.net',
    'Al.Araby.TV2': 'Al.Araby.2.HD.ae',
    'Al.Iraqia.News': 'Al.Iraqiya.HD.ae',
    'Al.Maaref.TV': 'AlMaaref.bh',
    
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

FORBIDDEN_SUFFIXES = (
    '.hk', '.kr', '.dk', '.fi', '.no', '.se', '.be', '.es', '.fr', 
    '.ca', '.ca2', '.gr', '.de', ".dk", '.cz', '.cy', '.ch', '.it', '.us', '.bb',
    '.distro', '.us_locals1', '.pluto'
)

EXCLUDE_WORDS = (
    'radio', 'fm', 'chaine', 'distro.tv', 'argentina', 'colombia', 'telefe', 'eltrece', 'Aghapy',
    'kurd', 'kurdistan', 'rudaw', 'waar', 'duhok', 'rojava', 'ronahi', 'channel8',        # Kurdish
    'morocco', 'maroc', 'maghreb', '2m',                                                  # Morocco
    'tunisia', 'tunisie', 'ttv', 'hannibal',                                              # Tunisia
    'libya', 'libye', '218 tv',                                                           # Libya
    'iran', 'persian', 'farsi', 'gem tv', 'mbcpersia',                                    # Iran
    'afghanistan', 'afghan', 'pashto', 'tolo', 'afghani',                                 # Afghanistan
    'babyfirst',                                                                          # US English Kids
    'eritrea', 'eri-tv',                                                                  # Eritrea
    'i24news',                                                                            # Israel-based news
    'india', 'hindi', 'tamil', 'telugu', 'malayalam',                                     # India
    'korea', 'korean', 'kbs', 'sbs', 'tvn',                                               # Korea
    'zealand', 'nz', 'australia', 'canterbury',                                           # NZ/AU
    'turk', 'trrt', 'atv.tr', 'fox.tr',                                                   # Turkish
    'canada', 'cbc.ca', 'cbcmusic', 'halifax', 'ottawa', 'winnipeg', 'calgary', 'vancouver', 'montreal',                 # Canadian CBC
    'kmbc', 'wmbc', 'tmbc', 'mbc1usa', 'samsung',                                         # US MBC Look-alikes
    'milb', 'ncaa', 'broncos', 'lobos', 'santa-clara',                                    # US Sports
    'mlb-', 'cubs', 'guardians', 'white-sox', 'reds',                                     # Baseball specific
    'espanol', 'wellbeing',                                                               # Spanish / Health junk
    'engelsk',                                                                            # Denmark
    'argentina', 'colombia',                                                              # Argentina + Colombia
    'brazil', 'portuguese', 'france', 'italy', 'deutsch', 'german', 'spanish', 'espana',  # Other languages
    'charity', 'coptic', 'logos', 'llbn', 'canalalgerie', 'tv2.dz', 'cna.dz',     
    'aghapy', 'aghania_ghani', 'godstands', 'teletchad',
    'dabanga', 'sudanese', 'northafricaine', 'cnadz',
    'cnadzsd', 'tv2dzsd', 'cnadz', 'tv2dz',
    'almaghribia',                                                                       # Catch the Moroccan Darija channel
    'alalam.ir',                                                                         # Catch the Iranian news channel
    'alwilayah',                                                                         # Catch the Iranian religious channel
    'eritreatv',                                                                         # Catch the Eritrean multi-lang channel
    'alfady', 'alkarma', 'atvsat', 'abnsat', 'elbeshara', 'alhorreya', 'IqraaAfricaEurope.sa@SD',       
)

# ── Helpers ──────────────────────────────────────────────────────────────────
def strip_quality(s):
    return re.sub(r'(@\S+)|(\s*\(.*\))', '', s or '').strip()

def norm(s):
    s = strip_quality(s)
    return re.sub(r'[^a-z0-9]', '', s.lower())

def is_excluded(tvg_id, name=''):
    # 1. Check for forbidden regional suffixes (like .us, .fr, .kr)
    if any(tvg_id.lower().endswith(s) for s in FORBIDDEN_SUFFIXES):
        return True

    # 2. Check for keywords (like 'kurd', 'dabanga', etc.)
    combined = (norm(tvg_id) + ' ' + norm(name)).lower()
    return any(x.lower() in combined for x in EXCLUDE_WORDS)

def apply_logo(extinf_line, tvg_id, tvg_name):
    # Normalize everything for comparison
    n_id = norm(tvg_id)
    n_name = norm(tvg_name)
    
    logo_url = None
    
    for key, url in LOGO_MAP.items():
        n_key = norm(key)
        
        # Check if the map key is inside the ID (e.g., "alarabiyabusiness" in "alarabiyabusinessae")
        # OR if the ID is inside the key.
        if (n_key in n_id and n_key != '') or (n_id in n_key and n_id != ''):
            logo_url = url
            break
        # Fallback to name check
        if (n_key in n_name and n_key != '') or (n_name in n_key and n_name != ''):
            logo_url = url
            break

    if logo_url:
        # Forcefully replace the existing tvg-logo link
        if 'tvg-logo=' in extinf_line:
            # This regex finds the tvg-logo attribute and replaces the URL inside the quotes
            return re.sub(r'tvg-logo="[^"]*"', f'tvg-logo="{logo_url}"', extinf_line)
        else:
            # If no logo tag exists, insert it after the #EXTINF:-1
            return re.sub(r'(#EXTINF:[^,]*)', rf'\1 tvg-logo="{logo_url}"', extinf_line, count=1)
            
    return extinf_line

def load_epg_channels():
    epg_exact = set()
    epg_norm = {}
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
    print(f"   ✅ EPG has {len(epg_exact)} unique channel ids\n")
    return epg_exact, epg_norm, epg_programmes

def fetch_and_resolve_m3u(epg_exact, epg_norm):
    id_map_norm = {norm(k): v for k, v in ID_MAP.items()}
    r = requests.get(M3U_URL, timeout=30)
    lines = r.text.splitlines()
    channels = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('#EXTINF'):
            extinf = line
            url = lines[i + 1] if i + 1 < len(lines) else ''
            i += 2
            tid_m = re.search(r'tvg-id="([^"]*)"', extinf)
            name_m = re.search(r'tvg-name="([^"]*)"', extinf)
            tvg_id = tid_m.group(1) if tid_m else ''
            tvg_name = name_m.group(1) if name_m else ''
            n = norm(tvg_id)
            epg_id = None
            if n in id_map_norm:
                epg_id = id_map_norm[n]
            elif tvg_id in epg_exact:
                epg_id = tvg_id
            elif n in epg_norm:
                epg_id = epg_norm[n]
            channels.append({'extinf': extinf, 'url': url, 'tvg_id': tvg_id, 'tvg_name': tvg_name, 'epg_id': epg_id})
        else:
            i += 1
    return channels

def write_outputs(channels, epg_exact, epg_norm, epg_programmes):
    kept_channels = []
    epg_ids_needed = set()
    no_epg = []
    
    for ch in channels:
        if is_excluded(ch['tvg_id'], ch['tvg_name']):
            continue
        kept_channels.append(ch)
        
        if ch['epg_id']:
            epg_ids_needed.add(ch['epg_id'])
        else:
            no_epg.append(ch)

    with open(M3U_OUTPUT, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        for ch in kept_channels:
            # 1. APPLY LOGO FIRST (while the original IDs are still present)
            line = apply_logo(ch['extinf'], ch['tvg_id'], ch['tvg_name'])
            
            # 2. THEN OVERWRITE TVG-ID FOR EPG (if a match exists)
            if ch['epg_id']:
                line = re.sub(r'tvg-id="[^"]*"', f'tvg-id="{ch["epg_id"]}"', line)
                
            f.write(line + '\n' + ch['url'] + '\n')

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

    print(f"\n❓ Channels WITHOUT EPG match ({len(no_epg)}):")
    for ch in sorted(no_epg, key=lambda x: x['tvg_name']):
        print(f"   tvg-id={ch['tvg_id']!r:45s}  name={ch['tvg_name']!r}")
    print(f"\n✅ Done! → {M3U_OUTPUT} + {EPG_OUTPUT}")

def main():
    print("🚀 Arabic IPTV Sync\n")
    epg_exact, epg_norm, epg_programmes = load_epg_channels()
    channels = fetch_and_resolve_m3u(epg_exact, epg_norm)
    write_outputs(channels, epg_exact, epg_norm, epg_programmes)

if __name__ == '__main__':
    main()
