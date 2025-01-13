import os
import requests
import sqlite3


url = "https://ftp.ripe.net/ripe/asnames/asn.txt"
response = requests.get(url)
response.raise_for_status()
data = response.text

current_dir_path = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(current_dir_path, "../output/asn_database.sqlite")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()


cursor.execute("""
CREATE TABLE IF NOT EXISTS asn_data (
    asn_number INTEGER PRIMARY KEY,
    asn_name TEXT,
    asn_country_code TEXT
)
""")

for line in data.splitlines():
    parts = line.split(maxsplit=1)
    if len(parts) == 2:
        asn_number = int(parts[0])
        name_country = parts[1].rsplit(",", 1)
        asn_name = name_country[0].strip()
        asn_country_code = name_country[1].strip() if len(name_country) > 1 else None
        cursor.execute("""
        INSERT OR IGNORE INTO asn_data (asn_number, asn_name, asn_country_code)
        VALUES (?, ?, ?)
        """, (asn_number, asn_name, asn_country_code))

conn.commit()
conn.close()

print(f"Database creato: {db_path}")
