import ipaddress
import json
import re
from typing import Callable


class RIPE_PARSER:
    def __init__(self):
        pass

    
    def get_ip_v6_first_and_last_ip(sub_net):
        ip,subnet = sub_net.split("/",1)
        first_ip = ipaddress.IPv6Address(ip)
        last_ipv6 = (ipaddress.IPv6Address(first_ip) + (2 ** (128 - int(subnet)) - 1))
        return first_ip.exploded,last_ipv6.exploded,ip,int(first_ip),int(last_ipv6),subnet
        

    def format_block(block):
        new_block = {}
        if block.get("ipVersion",4) == 6:
            first_ip,last_ip,prefex,first_ip_int,last_ip_int,subnet  = RIPE_PARSER.get_ip_v6_first_and_last_ip(block["inetnum"])
            new_block["first_ip"] = first_ip
            new_block["last_ip"] = last_ip
            new_block["network_prefix"] = prefex
            new_block["first_ip_int"] = first_ip_int
            new_block["last_ip_int"] = last_ip_int
            new_block["subnet"] = subnet
        else:
            cidr_pattern = r"^\d{1,3}(\.\d{1,3}){1,3}\/\d{1,2}$"
            if "inetnum" in block:
                if " - " in block["inetnum"]:  
                    inetnum_splited = block["inetnum"].split(" - ")
                    new_block["first_ip"] = inetnum_splited[0].strip()
                    new_block["last_ip"] = inetnum_splited[1].strip() if len(inetnum_splited) > 1 else inetnum_splited[0].strip()
                elif re.match(cidr_pattern, block["inetnum"]):  
                   
                    # inetnum 5.183.80/22
                    
                    [cidr,netmusk] = block["inetnum"].split("/")
                    cidr_parts = cidr.split(".")
                    while len(cidr_parts) < 4:
                        cidr_parts.append("0")

                    cidr = ".".join(cidr_parts)
                    
                    ip_network = ipaddress.ip_network(f"{cidr}/{netmusk}", strict=False)
                    new_block["first_ip"] = str(ip_network.network_address)
                    new_block["last_ip"] = str(ip_network.broadcast_address)
                else:
                    raise ValueError(f"inetnum IS NOT STANDARD {block['inetnum']}")
            else:
                raise KeyError("Il blocco non contiene 'inetnum'.")
            
            firstIp = ipaddress.ip_address(new_block["first_ip"])
            lastIp = ipaddress.ip_address(new_block["last_ip"])
            new_block["first_ip_int"] = int(firstIp)
            new_block["last_ip_int"] = int(lastIp)
        new_block["netname"] = block.get("netname", "Unknown")
        new_block["country"] = block.get("country", "Unknown")
        new_block["descr"] = block.get("descr", "Unknown")
        new_block["mnt-by"] = block.get("mnt-by", "Unknown")
        new_block["ip_version"] = block.get("ipVersion", 4)
        
        return new_block
    @staticmethod
    def normalize_ip(ip):
        try:
            return str(ipaddress.ip_address(".".join(str(int(octet)) for octet in ip.split("."))))
        except ValueError:
            return None
    def parse_transfer_json_file(file_path,cb:Callable[[dict],None]):

        with open(file_path, "r") as f:
            arin_data = json.load(f)


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

                new_block["first_ip"] = RIPE_PARSER.normalize_ip(raw_first_ip)
                new_block["last_ip"] = RIPE_PARSER.normalize_ip(raw_last_ip)

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
                cb(new_block)

    
    def parse_file(file_path,cb:Callable[[dict],None], parseRoute:bool=False):
        data = []
        with open(file_path, 'r',-1,"latin-1") as file:
            block = {}
            for line in file:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if parseRoute and (line.startswith("route:") or line.startswith("route6:") ) :
                    key, value = line.split(":", 1)
                    line = f"inetnum:{value}" if key == "route" else f"inet6num:{value}" if key == "route6" else line

                    
                    
                if line.startswith("inetnum:") or line.startswith("inet6num:"):
                    if block:
                        # data.append(RIPE_PARSER.format_block(block))
                        if "inet6num" in block or "inetnum" in block:
                            cb(RIPE_PARSER.format_block(block))
                        else:
                            print(f"Invalid block {block}")
                        block = {}
                    if line.startswith("inet6num:"):
                        block["inetnum"] = line[8:]
                if line and line.find(":") >= 0:
                    key, value = line.split(":", 1)
                    if key == "inet6num":
                        block["inetnum"] = value.strip()
                        block["ipVersion"] = 6
                        continue
                    elif key == "inetnum":
                        block["inetnum"] = value.strip()
                        block["ipVersion"] = 4
                        continue
                    
                    #Note : This block is to avoid overwrite the information like mnt-by 
                    if key in block:
                        if key == "descr":
                            block[key.strip()] += "\n" + value.strip()
                    else:
                        block[key.strip()] = value.strip()
            if block:  
                cb(RIPE_PARSER.format_block(block))
                # data.append(RIPE_PARSER.format_block(block))
        return data
    