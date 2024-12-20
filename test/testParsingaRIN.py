import json
import ipaddress

arin_transfare_dataJson = "/mnt/work/work/personal/ripe-ip-parser/db/transfers_latest.json"
blocks = []

def normalize_ip(ip):
    try:
        return str(ipaddress.ip_address(".".join(str(int(octet)) for octet in ip.split("."))))
    except ValueError:
        return None

with open(arin_transfare_dataJson, "r") as f:
    arin_data = json.load(f)

processed_blocks = []

for block in arin_data["transfers"]:
    if not block.get("ip4nets"):
        print(f"Skipping block because it has no ip4nets")
        continue

    if not block.get("recipient_organization"):
        print(f"Skipping block because it has no recipient_organization")
        continue

    for net in block["ip4nets"].get("transfer_set", []):
        new_block = {}
        raw_first_ip = net.get("start_address", "Unknown")
        raw_last_ip = net.get("end_address", "Unknown")

        new_block["first_ip"] = normalize_ip(raw_first_ip)
        new_block["last_ip"] = normalize_ip(raw_last_ip)

        if not new_block["first_ip"] or not new_block["last_ip"]:
            print(f"Invalid IP addresses in block: {new_block}")
            continue

        first_ip = ipaddress.ip_address(new_block["first_ip"])
        last_ip = ipaddress.ip_address(new_block["last_ip"])
        new_block["first_ip_int"] = int(first_ip)
        new_block["last_ip_int"] = int(last_ip)

        new_block["netname"] = block["recipient_organization"].get("name", "Unknown")
        new_block["country"] = block["recipient_organization"].get("country_code", "Unknown")
        new_block["descr"] = block.get("description", "Unknown")
        new_block["mnt-by"] = block.get("mnt-by", "Unknown")
        new_block["ip_version"] = 4

        processed_blocks.append(new_block)

print(f"Processed {len(processed_blocks)} blocks")
