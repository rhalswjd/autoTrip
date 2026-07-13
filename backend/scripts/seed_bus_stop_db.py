import os
import csv
import sqlite3
import argparse

def seed_database(csv_path: str, db_path: str):
    """
    Reads the bus_stop.csv and seeds the autotrip_bus.db.
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
            CREATE TABLE IF NOT EXISTS bus_stops (
                id TEXT PRIMARY KEY,
                name_jp TEXT NOT NULL,
                name_en TEXT NOT NULL,
                category TEXT
            )
        ''')
        
        # Read CSV and insert data
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            records = []
            for row in reader:
                records.append((
                    row['id'],
                    row['name_jp'],
                    row['name_en'],
                    row['category']
                ))
            
            conn.executemany('''
                INSERT INTO bus_stops (id, name_jp, name_en, category)
                VALUES (?, ?, ?, ?)
            ''', records)
            
            conn.commit()
            print(f"Successfully seeded {len(records)} bus stops into {db_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Bus Stop Database from CSV")
    parser.add_argument("--csv", type=str, default="backend/data/bus_stop.csv", help="Path to input CSV file")
    parser.add_argument("--db", type=str, default="backend/autotrip_bus.db", help="Path to output SQLite DB file")
    args = parser.parse_args()
    
    seed_database(args.csv, args.db)
