import sqlite3
import csv
import os
import sys

def seed():
    # Find backend dir
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(current_dir)
    sys.path.append(backend_dir)
    
    from core.config import settings
    from core.logger import logger

    db_path = settings.poi_db_path
    if os.path.exists(db_path):
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pois'")
                if cursor.fetchone():
                    count = conn.execute("SELECT COUNT(*) FROM pois").fetchone()[0]
                    if count > 0:
                        logger.info("POI DB already seeded. Skipping.")
                        return
        except Exception:
            pass

    csv_path = os.path.join(backend_dir, "data", "poi.csv")
    if not os.path.exists(csv_path):
        logger.error(f"POI CSV not found at {csv_path}")
        return

    logger.info("Seeding POI DB...")
    
    if os.path.exists(db_path):
        os.remove(db_path)

    with sqlite3.connect(db_path) as conn:
        conn.execute('''
            CREATE TABLE pois (
                id INTEGER PRIMARY KEY,
                name_en TEXT,
                name_jp TEXT,
                target_station_id TEXT,
                category TEXT
            )
        ''')
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                conn.execute(
                    '''
                    INSERT INTO pois (id, name_en, name_jp, target_station_id, category)
                    VALUES (?, ?, ?, ?, ?)
                    ''',
                    (
                        row['id'],
                        row['name_en'],
                        row['name_jp'],
                        row['target_station_id'],
                        row['category']
                    )
                )
        conn.commit()
    logger.info("POI DB seeded successfully.")

if __name__ == "__main__":
    seed()
