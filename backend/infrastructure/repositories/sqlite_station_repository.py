import sqlite3
from typing import List
from application.ports.station_repository_port import StationRepositoryPort
from domain.station import Station
from core.logger import logger

class SqliteStationRepository(StationRepositoryPort):
    def __init__(self, db_path: str = "autotrip_stations.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS stations (
                    id TEXT PRIMARY KEY,
                    name_en TEXT NOT NULL,
                    name_jp TEXT NOT NULL,
                    prefecture TEXT,
                    railway_company TEXT,
                    lat REAL,
                    lng REAL,
                    has_midori_office INTEGER NOT NULL
                )
            ''')
            # Seed data is handled by external script for full Japan database
            # We just ensure the table exists here.

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
