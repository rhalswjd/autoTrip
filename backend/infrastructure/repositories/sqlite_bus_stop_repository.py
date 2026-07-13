import sqlite3
import os
from typing import Optional
from core.logger import logger
from core.config import settings

class SqliteBusStopRepository:
    """
    Read-only repository for querying Bus Stop names from the SQLite database.
    Does NOT create tables or seed data.
    """
    def __init__(self, db_path: str = None):
        if db_path is None:
            # When initialized from TranslationService without specific path, use settings
            # We use an absolute path relative to the project root or rely on CWD.
            # Actually, using an absolute path relative to this file is safer for TranslationService.
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            self.db_path = os.path.join(base_dir, settings.bus_stop_db_path)
        else:
            self.db_path = db_path

    def get_english_name(self, name_jp: str) -> Optional[str]:
        if not os.path.exists(self.db_path):
            return None
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT name_en FROM bus_stops WHERE name_jp = ? LIMIT 1", (name_jp,))
                row = cursor.fetchone()
                if row:
                    return row[0]
        except Exception as e:
            logger.error(f"Failed to query SQLite for bus stop translation: {e}")
        return None
