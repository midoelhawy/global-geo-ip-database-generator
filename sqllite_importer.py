

import os
from pathlib import Path
from lib.db import SQLiteHandler
from lib.ripe_parser import RIPE_PARSER

blocks = []
total_blocks_processed= 0
if __name__ == "__main__":
    db_name = 'ripe_data.db'


    default_ripeV4_data = str(Path.joinpath(Path(__file__).parents[0],'db/ripe.db.inetnum'))
    default_ripeV6_data = str(Path.joinpath(Path(__file__).parents[0],'db/ripe.db.inet6num'))
    apnic_ripeV4_data = str(Path.joinpath(Path(__file__).parents[0], 'db/apnic.db.inetnum'))
    os.remove(db_name) if os.path.exists(db_name) else None
    db_handler = SQLiteHandler(db_name)
    db_handler.create_table()

    def on_single_block_process(block):
        global blocks,total_blocks_processed
        
        
        # Country is really world wide
        if "Country is really world wide" not in block["country"]  and "Worldwide" not in block["country"]:
            blocks.append(block)
        else:
            print(f"Ignoring block {block.get('first_ip')}")
        
        if len(blocks) >= 5000:
            
            db_handler.insert_data(blocks)
            total_blocks_processed += len(blocks)
            blocks = []
            print(f"Total blocks processed: {total_blocks_processed}")
    
    RIPE_PARSER.parse_file(default_ripeV4_data,on_single_block_process)
    print(f"Processing Apnic Db")
    RIPE_PARSER.parse_file(apnic_ripeV4_data, on_single_block_process)

    RIPE_PARSER.parse_file(default_ripeV6_data,on_single_block_process)
    

    print("Done")