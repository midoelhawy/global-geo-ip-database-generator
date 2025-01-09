# global-geo-ip-database-generator

> ⚠️ : Every contribution is welcome

## Introduction

`global-geo-ip-database-generator` is a tool designed to parse the RIPE database of IP address assignments (`ripe.db.inetnum`) and import the data into a SQLite database for easy querying and analysis. This tool also provides flexibility for users to create their custom parsers to generate JSON or any other schema/database format.




### Releases:

*You will find all db(sql,mmdb) in the repository release section , do you need to use the repo only if you need to coastumize something*

#### Download latest DB's

###### To download latest `SQLITE_DB`:

```bash
    wget -O "./geolocation_db.db.zip" "https://github.com/midoelhawy/global-geo-ip-database-generator/releases/latest/download/db.sqlite.zip"
    unzip -o ".geolocation_db.db.zip" -d "./"
    rm "./geolocation_db.db.zip"

```

###### To download latest `MMDB`:

```bash
    wget -O "./geolocation_db.db.zip" "https://github.com/midoelhawy/global-geo-ip-database-generator/releases/latest/download/ASN_COUNTRY_AND_CITY.mmdb
"
    unzip -o ".geolocation_db.db.zip" -d "./"
    rm "./geolocation_db.db.zip"

```


[see Releases](https://github.com/midoelhawy/global-geo-ip-database-generator/releaseshttps:/)

## How to Use

### Prerequisites

Before using the tool, ensure that you have the following prerequisites installed:

- Python 3.x
- pip (Python package manager)

### Setup

1. Clone the repository to your local machine:

   ```bash
   git clone https://github.com/midoelhawy/global-geo-ip-database-generator.git
   ```
2. Navigate to the project directory:

   ```bash
   cd global-geo-ip-database-generator
   ```
3. Install the required Python packages:

   ```bash
   pip install -r requirements.txt
   ```

### Parsing the RIPE Database

*NOTE: you can run all process's in one step directly by running this command `./scripts/parse_all_ripe_db_and_generate_mmdb.sh`*

1. download Ripe and apnic DB by running the following script:

   ```bash
   ./scripts/download-ripe-data.sh
   ```
2. Run the SQL generator to import the parsed data into a SQLite database:

   ```bash
   python3 sqllite_importer.py
   ```

### Custom Parser

You can also write your custom parser to generate JSON or another type of schema/database format. Follow these steps:

1. Create a file named `myCustomParser.py`.
2. Paste the following code into `myCustomParser.py`:

   ```python
   from pathlib import Path
   from lib.db import SQLiteHandler
   from lib.ripe_parser import RIPE_PARSER

   if __name__ == "__main__":
       default_ripe_data = str(Path.joinpath(Path(__file__).parents[0],'db/ripe.db.inetnum')) # PUT HERE YOUR FILE PATH
       def on_single_block_process(block):
           pass
           # THIS FUNCTION WILL BE EXECUTED WITH EVERY BLOCK OF IPS 
           # YOU CAN PUT IT TO A JSON FILE FOR EXAMPLE 

       RIPE_PARSER.parse_file(default_ripe_data, on_single_block_process)
       print("Done")
   ```
3. Customize the `on_single_block_process` function to handle each IP block as per your requirements.
4. Run the `myCustomParser.py` script to execute your custom parsing logic.

### How to generate `MMDB` database

*NOTE: YOU NEED SQLITE DB TO GENERATE MMDB*

1. install and configure `go-lang`
2. Run `cd ./scripts && go run generate_mmdb.go`
