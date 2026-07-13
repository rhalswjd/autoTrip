import sqlite3
import os
from typing import Optional
from domain.poi import Poi
from core.config import settings

class SqlitePoiRepository:
    def __init__(self):
        self.db_path = settings.poi_db_path

    def get_target_station_id(self, name_en: str) -> Optional[str]:
        if not os.path.exists(self.db_path):
            return None
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT target_station_id FROM pois WHERE name_en COLLATE NOCASE = ? LIMIT 1", (name_en,))
                row = cursor.fetchone()
                if row:
                    return str(row[0])
        except Exception:
            pass
        return None
