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
                    has_midori_office INTEGER NOT NULL
                )
            ''')
            # Seed test data for auto-complete API testing
            conn.execute("INSERT OR IGNORE INTO stations VALUES ('s1', 'Osaka', '大阪', 1)")
            conn.execute("INSERT OR IGNORE INTO stations VALUES ('s2', 'Shin-Osaka', '新大阪', 1)")
            conn.execute("INSERT OR IGNORE INTO stations VALUES ('s3', 'Kyoto', '京都', 1)")
            conn.execute("INSERT OR IGNORE INTO stations VALUES ('s4', 'Tokyo', '東京', 1)")

    async def search_stations(self, query: str) -> List[Station]:
        if not query.strip():
            return []
            
        logger.debug(f"SQLite Read: Station Search for query '{query}'")
        with sqlite3.connect(self.db_path) as conn:
            like_query = f"%{query}%"
            cursor = conn.execute('''
                SELECT id, name_en, name_jp, has_midori_office 
                FROM stations 
                WHERE name_en LIKE ? OR name_jp LIKE ?
                ORDER BY name_en ASC
            ''', (like_query, like_query))
            
            rows = cursor.fetchall()
            
            return [
                Station(
                    id=row[0],
                    name=row[1],
                    name_jp=row[2],
                    has_midori_office=bool(row[3])
                )
                for row in rows
            ]
