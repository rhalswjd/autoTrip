import sqlite3
from typing import List
from application.ports.station_repository_port import StationRepositoryPort
from domain.station import Station
from core.logger import logger

class SqliteStationRepository(StationRepositoryPort):
    def __init__(self, db_path: str = "autotrip_stations.db"):
        self.db_path = db_path

    async def search_stations(self, query: str) -> List[Station]:
        if not query.strip():
            return []
            
        logger.debug(f"SQLite Read: Station Search for query '{query}'")
        with sqlite3.connect(self.db_path) as conn:
            like_query = f"%{query}%"
            cursor = conn.execute('''
                SELECT id, name_en, name_jp, prefecture, railway_company, lat, lng, has_midori_office 
                FROM stations 
                WHERE name_en LIKE ? OR name_jp LIKE ?
                LIMIT 200
            ''', (like_query, like_query))
            
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
                if en.startswith(q_lower) or jp.startswith(q_lower): return 2
                if f" {q_lower}" in en or f"-{q_lower}" in en: return 3
                return 4
                
            sorted_rows = sorted(rows, key=lambda r: (get_score(r[1], r[2]), r[1]))
            
            return [
                Station(
                    id=row[0],
                    name=row[1],
                    name_jp=row[2],
                    prefecture=row[3] or "",
                    railway_company=row[4] or "",
                    lat=row[5] or 0.0,
                    lng=row[6] or 0.0,
                    has_midori_office=bool(row[7])
                )
                for row in sorted_rows[:50]
            ]
