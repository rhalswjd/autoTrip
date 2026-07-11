import os
import csv
import sqlite3
import argparse

def seed_database(csv_path: str, db_path: str):
    """
    Reads the station.csv and seeds the autotrip_stations.db.
    """
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        return

    # Remove existing db if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed existing database at {db_path}")

    # Connect to db and create table
    with sqlite3.connect(db_path) as conn:
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
        
        # Read CSV and insert data
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            records = []
            for row in reader:
                records.append((
                    row['id'],
                    row['name_en'],
                    row['name_jp'],
                    row['prefecture'],
                    row['railway_company'],
                    float(row['lat']) if row['lat'] else 0.0,
                    float(row['lng']) if row['lng'] else 0.0,
                    int(row['has_midori_office']) if row['has_midori_office'] else 0
                ))
            
            conn.executemany('''
                INSERT INTO stations (id, name_en, name_jp, prefecture, railway_company, lat, lng, has_midori_office)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', records)
            
            conn.commit()
            print(f"Successfully seeded {len(records)} stations into {db_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Station Database from CSV")
    parser.add_argument("--csv", type=str, default="backend/data/station.csv", help="Path to input CSV file")
    parser.add_argument("--db", type=str, default="backend/autotrip_stations.db", help="Path to output SQLite DB file")
    args = parser.parse_args()
    
    seed_database(args.csv, args.db)
