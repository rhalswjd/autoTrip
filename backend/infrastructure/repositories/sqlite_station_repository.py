import sqlite3
import re
import unicodedata
from typing import List
from application.ports.station_repository_port import StationRepositoryPort
from domain.station import Station
from domain.station_identity import qualified_station_name, station_base_name
from core.logger import logger
from infrastructure.services.station_display_names import station_display_name, station_display_names

class SqliteStationRepository(StationRepositoryPort):
    @staticmethod
    def _roman_key(value: str) -> str:
        normalized = unicodedata.normalize('NFKC', value or '').casefold()
        compact = re.sub(r"[\s\-'’]", '', normalized)
        # Imported romanizations sometimes omit the doubled vowel at word boundaries.
        return re.sub(r'([aeiou])\1+', r'\1', compact)

    @staticmethod
    def _one_edit(left: str, right: str) -> bool:
        if abs(len(left) - len(right)) > 1:
            return False
        if len(left) == len(right):
            return sum(a != b for a, b in zip(left, right)) <= 1
        short, long = sorted((left, right), key=len)
        return any(short == long[:i] + long[i + 1:] for i in range(len(long)))

    def __init__(self, db_path: str = "autotrip_stations.db"):
        self.db_path = db_path

    async def get_station_by_id(self, station_id: str) -> Station | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute('SELECT id,name_en,name_jp,prefecture,railway_company,lat,lng,has_midori_office FROM stations WHERE id=?', (station_id,)).fetchone()
            if row:
                return self._station(row)
        if station_id.startswith('poi_'):
            from core.config import settings
            import os
            if os.path.exists(settings.poi_db_path):
                with sqlite3.connect(settings.poi_db_path) as conn:
                    poi = conn.execute('SELECT target_station_id FROM pois WHERE id=?', (station_id[4:],)).fetchone()
                if poi:
                    return await self.get_station_by_id(str(poi[0]))
        return None

    @staticmethod
    def _station(row) -> Station:
        return Station(id=str(row[0]), name=row[1], name_jp=row[2], prefecture=row[3] or '',
            display_name_en=station_display_name(str(row[0]), row[2], row[3] or '', row[1]),
            railway_company=row[4] or '', lat=row[5] or 0., lng=row[6] or 0., has_midori_office=bool(row[7]),
            provider_aliases={'yahoo': qualified_station_name(row[2]), 'jr_odekake': station_base_name(row[2])})

    async def search_stations(self, query: str) -> List[Station]:
        if not query.strip():
            return []
            
        logger.debug(f"SQLite Read: Station Search for query '{query}'")
        with sqlite3.connect(self.db_path) as conn:
            like_query = f"%{query}%"
            q_key = self._roman_key(query)
            display_ids = [identity for identity, entry in station_display_names().items()
                           if q_key and q_key in self._roman_key(entry['display_name_en'])]
            fuzzy = q_key.isascii() and q_key.isalpha() and len(q_key) >= 4
            conn.create_function('roman_key', 1, self._roman_key, deterministic=True)
            cursor = conn.execute('''
                SELECT id, name_en, name_jp, prefecture, railway_company, lat, lng, has_midori_office 
                FROM stations 
                WHERE name_en LIKE ? OR name_jp LIKE ? OR roman_key(name_en) LIKE ?
                OR (? AND roman_key(name_en) LIKE ?)
                OR id IN (''' + ','.join('?' for _ in (display_ids or [''])) + ''')
                ORDER BY CASE WHEN lower(name_en)=lower(?) OR name_jp=? THEN 0 ELSE 1 END
                LIMIT 500
            ''', (like_query, like_query, f'%{q_key}%', fuzzy, q_key[:2] + '%', *(display_ids or ['']), query, query))
            
            rows = cursor.fetchall()
            
            # Add POI logic
            import os
            from core.config import settings
            poi_db = settings.poi_db_path
            poi_rows = []
            if os.path.exists(poi_db):
                try:
                    with sqlite3.connect(poi_db) as conn_poi:
                        poi_cursor = conn_poi.execute('''
                            SELECT id, name_en, name_jp, target_station_id, category
                            FROM pois
                            WHERE name_en LIKE ? OR name_jp LIKE ?
                        ''', (like_query, like_query))
                        
                        for p_row in poi_cursor.fetchall():
                            target_id = p_row[3]
                            t_cursor = conn.execute('''
                                SELECT id, name_en, name_jp, prefecture, railway_company, lat, lng, has_midori_office 
                                FROM stations WHERE id = ?
                            ''', (target_id,))
                            t_row = t_cursor.fetchone()
                            if t_row:
                                # Return POI name with the target station's data (including its real name_jp for Yahoo)
                                poi_rows.append((f"poi_{p_row[0]}", p_row[1], t_row[2], t_row[3], t_row[4], t_row[5], t_row[6], t_row[7]))
                except Exception as e:
                    logger.error(f"Failed to query POI DB: {e}")
                    
            rows.extend(poi_rows)
            
            # Sort by relevance: Exact > Prefix > Word Boundary > Contains
            q_lower = query.lower()
            
            def get_score(name_en: str, name_jp: str) -> int:
                en = name_en.lower()
                jp = name_jp.lower()
                
                if q_lower == en or q_lower == jp: return 1
                key = self._roman_key(en)
                if key == q_key: return 2
                if en.startswith(q_lower) or jp.startswith(q_lower) or key.startswith(q_key): return 3
                if fuzzy and any(self._one_edit(q_key, key[:length]) for length in (len(q_key) - 1, len(q_key), len(q_key) + 1)): return 4
                if q_lower in en or q_lower in jp or q_key in key: return 5
                return 99
                
            def row_score(row):
                display = station_display_name(str(row[0]), row[2], row[3] or '', row[1])
                return min(get_score(row[1], row[2]), get_score(display, row[2]))

            sorted_rows = sorted((r for r in rows if row_score(r) < 99),
                key=lambda r: (row_score(r) + (1 if str(r[0]).startswith('poi_') else 0), r[1]))
            
            return [
                self._station(row)
                for row in sorted_rows[:50]
            ]
