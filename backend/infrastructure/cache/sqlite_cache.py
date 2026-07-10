import sqlite3
import json
import time
import importlib
from typing import Any, Optional
from application.ports.cache_port import CachePort
from core.logger import logger

class SqliteCacheAdapter(CachePort):
    def __init__(self, db_path: str = "cache.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    type_info TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                )
            ''')

    def _serialize(self, obj: Any) -> tuple[str, str]:
        """Serializes Domain objects using Pydantic JSON to hide details from Application."""
        if isinstance(obj, list):
            if not obj:
                return json.dumps([]), "list"
            first = obj[0]
            if hasattr(first, "model_dump_json"):
                type_info = f"list:{first.__class__.__module__}.{first.__class__.__name__}"
                return json.dumps([item.model_dump() for item in obj]), type_info
            return json.dumps(obj), "list"
        elif hasattr(obj, "model_dump_json"):
            type_info = f"object:{obj.__class__.__module__}.{obj.__class__.__name__}"
            return obj.model_dump_json(), type_info
        else:
            return json.dumps(obj), "primitive"

    def _deserialize(self, value_str: str, type_info: str) -> Any:
        data = json.loads(value_str)
        if type_info == "primitive" or type_info == "list":
            return data
            
        if type_info.startswith("list:"):
            _, cls_path = type_info.split(":", 1)
            module_name, class_name = cls_path.rsplit(".", 1)
            module = importlib.import_module(module_name)
            cls = getattr(module, class_name)
            return [cls.model_validate(item) for item in data]
            
        if type_info.startswith("object:"):
            _, cls_path = type_info.split(":", 1)
            module_name, class_name = cls_path.rsplit(".", 1)
            module = importlib.import_module(module_name)
            cls = getattr(module, class_name)
            return cls.model_validate(data)
            
        return data

    async def get(self, key: str) -> Optional[Any]:
        logger.debug(f"SQLite Read: Cache GET for key {key}")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT value, type_info, expires_at FROM cache WHERE key = ?", (key,))
            row = cursor.fetchone()
            
            if not row:
                return None
                
            value, type_info, expires_at = row
            
            if time.time() > expires_at:
                # TTL Expiration: delete auto on get
                conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                return None
                
            return self._deserialize(value, type_info)

    async def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        logger.debug(f"SQLite Write: Cache SET for key {key}")
        value_str, type_info = self._serialize(value)
        now = time.time()
        expires_at = now + ttl_seconds
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO cache (key, value, type_info, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    type_info = excluded.type_info,
                    created_at = excluded.created_at,
                    expires_at = excluded.expires_at
            ''', (key, value_str, type_info, now, expires_at))

    async def delete(self, key: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM cache WHERE key = ?", (key,))

    async def clear(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM cache")
