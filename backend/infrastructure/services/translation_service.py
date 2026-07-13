import logging
import re
import sqlite3
import os

logger = logging.getLogger("autotrip")

class TranslationService:
    """
    Infrastructure service responsible for handling station and train name translations.
    """
    def __init__(self):
        from core.config import settings
        self.db_path = settings.sqlite_station_db_path

        # 1. Custom Dictionary (Manual Override - Priority 1)
        self._custom_dict = {
            "清水道": "Kiyomizu-michi",
            "祇園": "Gion",
            "金閣寺道": "Kinkakuji-michi",
            "銀閣寺道": "Ginkakuji-michi",
            "四条河原町": "Shijo-Kawaramachi",
            "天神橋筋六丁目": "Tenjimbashisuji 6-chome",
            "神宮前": "Jingu-mae",
            "名鉄名古屋": "Meitetsu-Nagoya",
            "岐阜": "Gifu",
            "空港": "Airport",
            "金山": "Kanayama",
            "栄": "Sakae"
        }
        
        # 8. Runtime Cache
        self._runtime_cache = {}

        # Initialize Romanization (pykakasi)
        try:
            import pykakasi
            self.kks = pykakasi.kakasi()
        except ImportError:
            logger.warning("pykakasi not found. Romanization fallback disabled.")
            self.kks = None

        # 5. Train Dictionary (Company)
        self._companies = {
            "ＪＲ": "JR",
            "JR": "JR",
            "近鉄": "Kintetsu",
            "名鉄": "Meitetsu",
            "京阪": "Keihan",
            "阪急": "Hankyu",
            "阪神": "Hanshin",
            "南海": "Nankai",
            "京王": "Keio",
            "小田急": "Odakyu",
            "東急": "Tokyu",
            "京急": "Keikyu",
            "西武": "Seibu",
            "東武": "Tobu",
            "京成": "Keisei",
            "相鉄": "Sotetsu",
            "東京メトロ": "Tokyo Metro",
            "都営": "Toei",
            "大阪メトロ": "Osaka Metro",
            "名古屋市営": "Nagoya Subway",
            "福岡市地下鉄": "Fukuoka Subway",
            "京都市営": "Kyoto Subway",
            "札幌市営": "Sapporo Subway",
            "仙台市地下鉄": "Sendai Subway",
            "神戸市営": "Kobe Subway",
            "横浜市営": "Yokohama Subway"
        }

        # 5. Train Dictionary (Lines)
        self._lines = {
            "山手線": "Yamanote Line",
            "中央線": "Chuo Line",
            "総武線": "Sobu Line",
            "京浜東北線": "Keihin-Tohoku Line",
            "埼京線": "Saikyo Line",
            "湘南新宿ライン": "Shonan-Shinjuku Line",
            "上野東京ライン": "Ueno-Tokyo Line",
            "東海道本線": "Tokaido Main Line",
            "東海道線": "Tokaido Line",
            "横須賀線": "Yokosuka Line",
            "南武線": "Nambu Line",
            "横浜線": "Yokohama Line",
            "武蔵野線": "Musashino Line",
            "京葉線": "Keiyo Line",
            "常磐線": "Joban Line",
            "宇都宮線": "Utsunomiya Line",
            "高崎線": "Takasaki Line",
            "名古屋本線": "Nagoya Main Line",
            "大阪環状線": "Osaka Loop Line",
            "京都線": "Kyoto Line",
            "神戸線": "Kobe Line",
            "宝塚線": "Takarazuka Line",
            "奈良線": "Nara Line",
            "本線": "Main Line",
            "空港線": "Airport Line",
            "御堂筋線": "Midosuji Line",
            "谷町線": "Tanimachi Line",
            "四つ橋線": "Yotsubashi Line",
            "千日前線": "Sennichimae Line",
            "堺筋線": "Sakaisuji Line",
            "長堀鶴見緑地線": "Nagahori Tsurumi-ryokuchi Line",
            "今里筋線": "Imazatosuji Line",
            "ニュートラム": "New Tram",
            "烏丸線": "Karasuma Line",
            "東西線": "Tozai Line",
            "銀座線": "Ginza Line",
            "丸ノ内線": "Marunouchi Line",
            "日比谷線": "Hibiya Line",
            "千代田線": "Chiyoda Line",
            "有楽町線": "Yurakucho Line",
            "半蔵門線": "Hanzomon Line",
            "南北線": "Namboku Line",
            "副都心線": "Fukutoshin Line",
            "浅草線": "Asakusa Line",
            "三田線": "Mita Line",
            "新宿線": "Shinjuku Line",
            "大江戸線": "Oedo Line"
        }

        # 5. Train Dictionary (Services & Brand Names)
        self._services = {
            "新幹線": "Shinkansen",
            "のぞみ": "Nozomi",
            "ひかり": "Hikari",
            "こだま": "Kodama",
            "みずほ": "Mizuho",
            "さくら": "Sakura",
            "つばめ": "Tsubame",
            "はやぶさ": "Hayabusa",
            "はやて": "Hayate",
            "やまびこ": "Yamabiko",
            "なすの": "Nasuno",
            "こまち": "Komachi",
            "つばさ": "Tsubasa",
            "かがやき": "Kagayaki",
            "はくたか": "Hakutaka",
            "あさま": "Asama",
            "つるぎ": "Tsurugi",
            "サンダーバード": "Thunderbird",
            "はるか": "Haruka",
            "くろしお": "Kuroshio",
            "しらさぎ": "Shirasagi",
            "ひたち": "Hitachi",
            "ときわ": "Tokiwa",
            "あずさ": "Azusa",
            "かいじ": "Kaiji",
            "成田エクスプレス": "Narita Express",
            "踊り子": "Odoriko",
            "サフィール踊り子": "Saphir Odoriko",
            "ソニック": "Sonic",
            "ひだ": "Hida",
            "スーパーはくと": "Super Hakuto",
            "スーパーいなば": "Super Inaba",
            "スーパーおき": "Super Oki",
            "スーパーまつかぜ": "Super Matsukaze",
            "ミュースカイ": "Mu-Sky",
            "しまかぜ": "Shimakaze",
            "ひのとり": "Hinotori",
            "アーバンライナー": "Urban Liner",
            "ラピート": "Rapi:t",
            "ロマンスカー": "Romancecar",
            "スペーシア": "Spacia",
            "スカイライナー": "Skyliner",
            "特別快速": "Special Rapid",
            "関空快速": "Kansai Airport Rapid",
            "紀州路快速": "Kishuji Rapid",
            "新快速": "Special Rapid",
            "通勤快速": "Commuter Rapid",
            "快速": "Rapid",
            "特急": "Limited Express",
            "急行": "Express",
            "区間急行": "Semi-Express",
            "準急": "Semi-Express",
            "普通": "Local",
            "各駅停車": "Local"
        }

        # 6.5 Facility Dictionary (For Google Maps UX)
        self._facilities = {
            "バスターミナル": "Bus Terminal",
            "駅前": "Station",
            "駅": "Station",
            "空港": "Airport",
            "港": "Port",
            "市役所前": "City Hall",
            "市役所": "City Hall"
        }

        self._companies_sorted = sorted(self._companies.items(), key=lambda x: len(x[0]), reverse=True)
        self._lines_sorted = sorted(self._lines.items(), key=lambda x: len(x[0]), reverse=True)
        self._services_sorted = sorted(self._services.items(), key=lambda x: len(x[0]), reverse=True)
        self._facilities_sorted = sorted(self._facilities.items(), key=lambda x: len(x[0]), reverse=True)

    def _hyphenate_prefix(self, name: str) -> str:
        fixes = {
            "Shinosaka": "Shin-Osaka",
            "Shinkobe": "Shin-Kobe",
            "Shinyokohama": "Shin-Yokohama",
            "Shinsapporo": "Shin-Sapporo",
            "Shinaomori": "Shin-Aomori",
            "Shinhakodatehokuto": "Shin-Hakodate-Hokuto",
            "Higashiosaka": "Higashi-Osaka",
            "Nishinippori": "Nishi-Nippori",
            "Kitasenju": "Kita-Senju",
            "Minamifunabashi": "Minami-Funabashi"
        }
        if name.title() in fixes:
            return fixes[name.title()]

        prefixes = ["Shin", "Higashi", "Nishi", "Kita", "Minami", "Naka"]
        res = name
        for p in prefixes:
            if res.startswith(p) and len(res) > len(p) and res[len(p)] != '-':
                if res in ["Shinjuku", "Shinagawa", "Shibuya", "Shimbashi", "Shinano", "Shinonome", "Minatomirai"]:
                    continue
                res = p + "-" + res[len(p):].capitalize()
                break
        return res

    def _romanize_mixed(self, mixed_text: str) -> str:
        if not hasattr(self, 'kks') or not self.kks:
            return mixed_text
            
        result = self.kks.convert(mixed_text)
        romaji_parts = []
        for item in result:
            orig = item['orig']
            # If it's pure ASCII, leave it as is (prevent lowercasing of our English replacements)
            if all(ord(c) < 128 for c in orig):
                romaji_parts.append(orig)
            else:
                converted = item['passport']
                if converted:
                    romaji_parts.append(converted.capitalize())
                else:
                    romaji_parts.append(orig)
                    
        res = "".join(romaji_parts)
        # Fix missing spaces between Lowercase and Uppercase (e.g. MeitetsuNagoya -> Meitetsu Nagoya)
        res = re.sub(r'([a-z])([A-Z])', r'\1 \2', res)
        return res

    def get_english_name(self, jp_name: str) -> str:
        if not jp_name:
            return ""
            
        # 1. Check Custom Dictionary (Highest Priority)
        if jp_name in self._custom_dict:
            return self._custom_dict[jp_name]
            
        # 8. Check Runtime Cache (to prevent DB hits for repeated names)
        if jp_name in self._runtime_cache:
            return self._runtime_cache[jp_name]

        clean_name = re.sub(r'[\(（].*?[\)）]', '', jp_name)
        clean_name = re.sub(r'【.*?】', '', clean_name)
        clean_name = re.sub(r'\[.*?\]', '', clean_name)
        clean_name = clean_name.strip()
        
        en_name = None
        
        # 2. Check Station DB
        if os.path.exists(self.db_path):
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute("SELECT name_en FROM stations WHERE name_jp = ? LIMIT 1", (clean_name,))
                    row = cursor.fetchone()
                    if row:
                        en_name = self._hyphenate_prefix(row[0])
                        logger.debug(f"[Translation] '{jp_name}' -> '{en_name}' (Layer: Station DB)")
            except Exception as e:
                logger.error(f"Failed to query SQLite for translation: {e}")
                
        # 3. Query Bus Stop DB
        if not en_name:
            from infrastructure.repositories.sqlite_bus_stop_repository import SqliteBusStopRepository
            bus_repo = SqliteBusStopRepository()
            bus_en_name = bus_repo.get_english_name(clean_name)
            if bus_en_name:
                en_name = bus_en_name
                logger.debug(f"[Translation] '{jp_name}' -> '{en_name}' (Layer: Bus Stop DB)")
            
        # 4. Query POI DB
        if not en_name:
            from core.config import settings
            poi_db = settings.poi_db_path
            if os.path.exists(poi_db):
                try:
                    with sqlite3.connect(poi_db) as conn:
                        cursor = conn.execute("SELECT name_en FROM pois WHERE name_jp = ? LIMIT 1", (clean_name,))
                        row = cursor.fetchone()
                        if row:
                            en_name = row[0]
                            logger.debug(f"[Translation] '{jp_name}' -> '{en_name}' (Layer: POI DB)")
                except Exception as e:
                    logger.error(f"Failed to query POI SQLite for translation: {e}")
                
        # 7. Fallback to Romanization
        if not en_name:
            # 6.5 Apply Facility Dictionary before Romanization to mimic Google Maps UX
            facility_replaced = clean_name
            for jp, en in self._facilities_sorted:
                if jp in facility_replaced:
                    facility_replaced = facility_replaced.replace(jp, f" {en} ")
                    
            en_name = self._romanize_mixed(facility_replaced)
            # Clean up excessive spaces introduced by replacements
            en_name = re.sub(r'\s+', ' ', en_name).strip()
            logger.debug(f"[Translation] '{jp_name}' -> '{en_name}' (Layer: Romanization Fallback)")
            
        # 8. Save to Runtime Cache
        if en_name:
            self._runtime_cache[jp_name] = en_name
            return en_name
            
        return jp_name

    def translate_train(self, jp_train: str) -> str:
        if not jp_train:
            return ""
        if jp_train == "徒歩" or jp_train == "同駅内徒歩":
            return "Walk"
            
        # 1. Custom Dictionary Check
        if jp_train in self._custom_dict:
            return self._custom_dict[jp_train]
            
        # 8. Check Runtime Cache
        if jp_train in self._runtime_cache:
            return self._runtime_cache[jp_train]
            
        res = jp_train
        
        # Remove destination info in parentheses like (神宮前−岐阜) or （神宮前−空港）
        res = re.sub(r'[\(（].*?[-−].*?[\)）]', '', res)
        res = re.sub(r'[\(（][^\)）]+[\)）]', '', res)
        
        # 6. Bus Dictionary Patterns
        bus_companies = {
            "京都市営": "Kyoto City",
            "京阪": "Keihan",
            "西日本ＪＲ": "West Japan JR",
            "ＪＲ東海": "JR Tokai",
            "近鉄": "Kintetsu",
            "阪急": "Hankyu",
            "南海": "Nankai",
            "名鉄": "Meitetsu",
            "東京空港交通": "Airport Transport Service",
            "関西空港交通": "Kansai Airport Transportation"
        }
        
        bus_types = {
            "高速バス": "Highway Bus",
            "夜行バス": "Night Bus",
            "リムジンバス": "Limousine Bus",
            "バス": "Bus"
        }
        
        for jp, en in sorted(bus_companies.items(), key=lambda x: len(x[0]), reverse=True):
            if jp in res and ("バス" in res or "系統" in res):
                res = res.replace(jp, f" {en} ")
                
        for jp, en in sorted(bus_types.items(), key=lambda x: len(x[0]), reverse=True):
            if jp in res:
                res = res.replace(jp, f" {en} ")
                
        # Translate Route XX (e.g., ２０６系統 -> Route 206)
        res = re.sub(r'([０-９0-9]+)系統', lambda m: f" Route {m.group(1).translate(str.maketrans('０１２３４５６７８９', '0123456789'))} ", res)
        
        # 5. Train Dictionary Patterns
        for jp, en in self._companies_sorted:
            if jp in res:
                res = res.replace(jp, f" {en} ")
                
        for jp, en in self._lines_sorted:
            if jp in res:
                res = res.replace(jp, f" {en} ")
                
        for jp, en in self._services_sorted:
            if jp in res:
                res = res.replace(jp, f" {en} ")
                
        # Apply Directions
        directions = {
            "外回り": "Outer Loop",
            "内回り": "Inner Loop"
        }
        for jp, en in directions.items():
            if jp in res:
                res = res.replace(jp, f" {en} ")
                
        # Remove "当駅始発" or other noise
        res = res.replace("当駅始発", "")
        
        # Format Train Numbers (e.g. 15号 -> 15)
        res = re.sub(r'(\d+)号', r' \1 ', res)
        
        # 7. Fallback to Romanization for any remaining Japanese text (e.g., unknown line name)
        if re.search(r'[ぁ-んァ-ン一-龥]', res):
            res = self._romanize_mixed(res)
            
        # Clean up excessive spaces
        res = re.sub(r'\s+', ' ', res).strip()
        
        # 8. Save to Runtime Cache
        self._runtime_cache[jp_train] = res
        return res
