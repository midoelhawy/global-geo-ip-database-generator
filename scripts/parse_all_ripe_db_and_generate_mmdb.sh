#!/bin/sh
set -e

# Download RIPE data
echo "Downloading RIPE data..."
./scripts/download-ripe-data.sh
echo "Download RIPE data complete."

echo "Start Parsing..."
python3 sqllite_importer.py
echo "Parsing complete."


echo "Downloaing latest mmdb base db"
./scripts/download_latest_mmdb.sh
echo "Downloaded latest mmdb base db"


echo "Generate MMDB file..."
cd ./scripts && python generate_mmdb.py
echo "MMDB file generated."