from pathlib import Path
import sys
path_root = Path(__file__).parents[1]
sys.path.append(str(path_root))
print(sys.path)

from lib.ripe_parser import RIPE_PARSER

file_path = str(Path.joinpath(Path(__file__).parents[1],'db/arin_db.txt'))


def on_single_block_process(block):
    print(block)

parse_data = RIPE_PARSER.parse_arin_file(file_path,on_single_block_process)
print(parse_data)