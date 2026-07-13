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
        self.db_path = os.path.join(os.path.dirname(__file__), '../../autotrip_stations.db')
        
        self._station_map = {
            "東京": "Tokyo",
            "品川": "Shinagawa",
            "新横浜": "Shin-Yokohama",
            "名古屋": "Nagoya",
            "京都": "Kyoto",
            "新大阪": "Shin-Osaka",
            "大阪": "Osaka",
            "三島": "Mishima",
            "静岡": "Shizuoka",
            "浜松": "Hamamatsu",
            "豊橋": "Toyohashi",
            "大垣": "Ogaki",
            "米原": "Maibara",
            "博多": "Hakata",
            "高槻": "Takatsuki",
            "高槻市": "Takatsuki-shi",
            "熱海": "Atami",
            "大阪梅田": "Osaka-Umeda",
            "大阪空港": "Itami Airport",
            "関西空港": "Kansai Airport",
            "中部国際空港": "Chubu Centrair International Airport",
            "羽田空港": "Haneda Airport",
            "成田空港": "Narita Airport"
        }
        
        # 1. Company replacements (sorted internally by length descending)
        self._companies = {
            "OsakaMetro": "Osaka Metro ",
            "大阪メトロ": "Osaka Metro ",
            "東京メトロ": "Tokyo Metro ",
            "ＪＲ": "JR ",
            "阪急": "Hankyu ",
            "阪神": "Hanshin ",
            "京阪": "Keihan ",
            "近鉄": "Kintetsu ",
            "南海": "Nankai ",
            "西武": "Seibu ",
            "東武": "Tobu ",
            "東急": "Tokyu ",
            "京王": "Keio ",
            "小田急": "Odakyu ",
            "京成": "Keisei ",
            "都営": "Toei ",
            "名鉄": "Meitetsu "
        }

        # 2. Line replacements
        self._lines = {
            "東海道・山陽本線": "Tokaido-Sanyo Main Line",
            "東海道本線": "Tokaido Main Line",
            "山陽本線": "Sanyo Main Line",
            "山陰本線": "Sanin Main Line",
            "関西本線": "Kansai Main Line",
            "学研都市線": "Gakkentoshi Line",
            "湖西線": "Kosei Line",
            "琵琶湖線": "Biwako Line",
            "京都線": "Kyoto Line",
            "神戸線": "Kobe Line",
            "ゆめ咲線": "Yumesaki Line",
            "大阪環状線": "Osaka Loop Line",
            "阪和線": "Hanwa Line",
            "奈良線": "Nara Line",
            "大和路線": "Yamatoji Line",
            "宝塚線": "Takarazuka Line",
            "東西線": "Tozai Line",
            "中央線": "Chuo Line",
            "山手線": "Yamanote Line",
            "京浜東北線": "Keihin-Tohoku Line",
            "総武線": "Sobu Line",
            "埼京線": "Saikyo Line",
            "御堂筋線": "Midosuji Line",
            "谷町線": "Tanimachi Line",
            "四つ橋線": "Yotsubashi Line",
            "千日前線": "Sennichimae Line",
            "堺筋線": "Sakaisuji Line",
            "長堀鶴見緑地線": "Nagahori Tsurumi-ryokuchi Line",
            "今里筋線": "Imazatosuji Line",
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
            "大江戸線": "Oedo Line",
            "京都本線": "Kyoto Line",
            "神戸本線": "Kobe Line",
            "宝塚本線": "Takarazuka Line",
            "名古屋本線": "Nagoya Main Line",
            "犬山線": "Inuyama Line",
            "常滑線": "Tokoname Line",
            "空港線": "Airport Line",
            "名鉄名古屋本線": "Meitetsu Nagoya Main Line",
            "本線": "Main Line",
            "高野線": "Koya Line",
            "大阪線": "Osaka Line",
            "南大阪線": "Minami-Osaka Line"
        }

        # 3. Service and Train Name replacements
        self._services = {
            "新幹線": "Shinkansen",
            "のぞみ": "Nozomi",
            "ひかり": "Hikari",
            "こだま": "Kodama",
            "みずほ": "Mizuho",
            "さくら": "Sakura",
            "くろしお": "Kuroshio",
            "はるか": "Haruka",
            "サンダーバード": "Thunderbird",
            "スーパーいなば": "Super Inaba",
            "ソニック": "Sonic",
            "ひだ": "Hida",
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

        # Sort dictionaries by length descending to prevent partial match overwrites
        self._companies_sorted = sorted(self._companies.items(), key=lambda x: len(x[0]), reverse=True)
        self._lines_sorted = sorted(self._lines.items(), key=lambda x: len(x[0]), reverse=True)
        self._services_sorted = sorted(self._services.items(), key=lambda x: len(x[0]), reverse=True)

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

    def get_english_name(self, jp_name: str) -> str:
        clean_name = re.sub(r'[\(（].*?[\)）]', '', jp_name)
        clean_name = re.sub(r'【.*?】', '', clean_name)
        clean_name = re.sub(r'\[.*?\]', '', clean_name)
        clean_name = clean_name.strip()
        
        # 1. Check Station DB
        if os.path.exists(self.db_path):
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute("SELECT name_en FROM stations WHERE name_jp = ? LIMIT 1", (clean_name,))
                    row = cursor.fetchone()
                    if row:
                        en_name = row[0]
                        result = self._hyphenate_prefix(en_name)
                        logger.debug(f"[Translation] '{jp_name}' -> '{result}' (Layer: Station DB)")
                        return result
            except Exception as e:
                logger.error(f"Failed to query SQLite for translation: {e}")
                
        # 2. Query Bus Stop DB
        from infrastructure.repositories.sqlite_bus_stop_repository import SqliteBusStopRepository
        bus_repo = SqliteBusStopRepository()
        bus_en_name = bus_repo.get_english_name(jp_name)
        if bus_en_name:
            logger.debug(f"[Translation] '{jp_name}' -> '{bus_en_name}' (Layer: Bus Stop DB)")
            return bus_en_name
            
        # 3. Query POI DB
        from core.config import settings
        poi_db = settings.poi_db_path
        if os.path.exists(poi_db):
            try:
                with sqlite3.connect(poi_db) as conn:
                    cursor = conn.execute("SELECT name_en FROM pois WHERE name_jp = ? LIMIT 1", (clean_name,))
                    row = cursor.fetchone()
                    if row:
                        logger.debug(f"[Translation] '{jp_name}' -> '{row[0]}' (Layer: POI DB)")
                        return row[0]
            except Exception as e:
                logger.error(f"Failed to query POI SQLite for translation: {e}")
                
        # 4. External Translator Cache
        if not hasattr(self, '_translator_cache'):
            self._translator_cache = {
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
        
        if jp_name in self._translator_cache:
            en_name = self._translator_cache[jp_name]
            logger.debug(f"[Translation] '{jp_name}' -> '{en_name}' (Layer: Translator)")
            return en_name
                
        # 5. Fallback
        logger.debug(f"[Translation] '{jp_name}' -> '{jp_name}' (Layer: Fallback)")
        return jp_name

    def translate_train(self, jp_train: str) -> str:
        if not jp_train:
            return ""
        if jp_train == "徒歩" or jp_train == "同駅内徒歩":
            return "Walk"
            
        res = jp_train
        
        # Remove destination info in parentheses like (神宮前−岐阜) or （神宮前−空港）
        res = re.sub(r'[\(（].*?[-−].*?[\)）]', '', res)
        # Also remove any standalone parentheses at the end if they contain Japanese text that wasn't stripped
        res = re.sub(r'[\(（][^\)）]+[\)）]', '', res)
        
        # Apply Bus Patterns
        bus_companies = {
            "京都市営": "Kyoto City ",
            "京阪": "Keihan ",
            "西日本ＪＲ": "West Japan JR ",
            "ＪＲ東海": "JR Tokai ",
            "近鉄": "Kintetsu ",
            "阪急": "Hankyu ",
            "南海": "Nankai ",
            "名鉄": "Meitetsu ",
            "東京空港交通": "Airport Transport Service ",
            "関西空港交通": "Kansai Airport Transportation "
        }
        
        bus_types = {
            "高速バス": "Highway Bus",
            "夜行バス": "Night Bus",
            "リムジンバス": "Limousine Bus",
            "バス": "Bus"
        }
        
        for jp, en in sorted(bus_companies.items(), key=lambda x: len(x[0]), reverse=True):
            if jp in res and ("バス" in res or "系統" in res):
                res = res.replace(jp, f"{en}")
                
        for jp, en in sorted(bus_types.items(), key=lambda x: len(x[0]), reverse=True):
            if jp in res:
                res = res.replace(jp, f" {en} ")
                
        # Translate Route XX (e.g., ２０６系統 -> Route 206)
        # Convert full-width numbers to half-width for routes
        res = re.sub(r'([０-９0-9]+)系統', lambda m: f" Route {m.group(1).translate(str.maketrans('０１２３４５６７８９', '0123456789'))} ", res)
        
        # Apply Companies
        for jp, en in self._companies_sorted:
            if jp in res:
                res = res.replace(jp, f" {en} ")
                
        # Apply Lines
        for jp, en in self._lines_sorted:
            if jp in res:
                res = res.replace(jp, f" {en} ")
                
        # Apply Services
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
        
        # Clean up excessive spaces
        res = re.sub(r'\s+', ' ', res).strip()
        
        return res
