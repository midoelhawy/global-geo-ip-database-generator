import os
import sqlite3
import ipaddress
import maxminddb
import logging
import gc  # For garbage collection
from typing import Optional, Dict, Any
from mmdb_writer import MMDBWriter
from netaddr import IPSet

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IPData:
    def __init__(
        self,
        first_ip: str,
        last_ip: str,
        subnet: int,
        netname: str,
        mnt_by: Optional[str],
    ):
        self.first_ip = first_ip
        self.last_ip = last_ip
        self.subnet = subnet
        self.netname = netname
        self.mnt_by = mnt_by


def main():
    # Get current directory path
    current_dir_path = os.path.dirname(os.path.abspath(__file__))

    # Open SQLite database
    sqlite_db = sqlite3.connect(os.path.join(current_dir_path, "../geolocation_db.db"))
    sqlite_db.row_factory = sqlite3.Row  # Allows accessing columns as attributes
    cursor = sqlite_db.cursor()

    # Open MaxMind databases
    asn_db = maxminddb.open_database(
        os.path.join(current_dir_path, "../db/base_mmdb/GeoLite2-ASN.mmdb")
    )
    city_db = maxminddb.open_database(
        os.path.join(current_dir_path, "../db/base_mmdb/GeoLite2-City.mmdb")
    )

    # Create a new MMDB writer
    writer = MMDBWriter(
        ip_version=6,
        ipv4_compatible=True,
    )

    # Execute the query to fetch IP data
    cursor.execute(
        """
        SELECT first_ip, last_ip, subnet, netname, mnt_by FROM ip_data 
        WHERE subnet > 0 
        AND (descr NOT LIKE '%Early registration addresses%' 
            AND netname != 'ERX-NETBLOCK' 
            AND netname != 'SBCIS-SBIS-6BLK' 
            AND descr NOT LIKE '%These addresses have been further assigned to users%' 
            AND descr NOT LIKE 'This IP address range is not registered in the%' 
            AND netname != 'SPECIAL-IPV4-LOCAL-ID-IANA-RESERVED'
            AND netname != 'IANA-THIS-HOST-ON-THIS-NETWORK'
            AND netname != 'SHARED-ADDRESS-SPACE-RFC6598-IANA-RESERVED'
            AND netname != 'SPECIAL-IPV4-BENCHMARK-TESTING-IANA-RESERVED'
            AND netname != 'LINKLOCAL-RFC3927-IANA-RESERVED'
            AND netname != 'PRIVATE-ADDRESS-CBLK-RFC1918-IANA-RESERVED'
            AND netname != 'SPECIAL-IPV4-REGISTRY-IANA-RESERVED'
            AND netname != '6TO4-RELAY-ANYCAST-IANA-RESERVED'
            AND netname != 'DS-LITE-RFC-6333-11-IANA-RESERVED'
        ) 
        ORDER BY CAST(first_ip_int AS UNSIGNED) ASC, subnet DESC;
    """
    )

    counter = 0
    batch_size = 1000  # Process rows in batches of 1000

    while True:
        # Fetch rows in batches
        rows = cursor.fetchmany(batch_size)
        if not rows:
            break  # Exit loop if no more rows

        for row in rows:
            ip_data = IPData(
                first_ip=row["first_ip"],
                last_ip=row["last_ip"],
                subnet=row["subnet"],
                netname=row["netname"],
                mnt_by=row["mnt_by"],
            )

            # Check if the IP is private or reserved
            try:
                check_ip = ipaddress.ip_address(ip_data.first_ip)
                if check_ip.is_private:
                    logger.info(f"FirstIP is Reserved or Invalid: {ip_data.first_ip}")
                    continue
            except ValueError:
                logger.error(f"Invalid IP address: {ip_data.first_ip}")
                continue

            # Build the MMDB record
            record = build_mmdb_record(ip_data, asn_db, city_db)
            if record is None:
                continue

            # Get the correct network
            network = get_network_from_record(ip_data)
            if network is None:
                continue

            # Insert the record into the MMDB writer
            writer.insert_network(IPSet([str(network)]), record)

            counter += 1
            if counter % batch_size == 0:
                logger.info(f"Processed {counter} records")
                # gc.collect()  # Force garbage collection after each batch

    # Close databases
    asn_db.close()
    city_db.close()
    sqlite_db.close()

    # Write the MMDB database to file
    writer.to_db_file(os.path.join(current_dir_path, "../output/ASN_COUNTRY_AND_CITY.mmdb"))

    logger.info(
        f"Database generated in {os.path.join(current_dir_path, '../output/ASN_COUNTRY_AND_CITY.mmdb')}"
    )


def build_mmdb_record(
    ip_data: IPData, asn_db: maxminddb.Reader, city_db: maxminddb.Reader
) -> Optional[Dict[str, Any]]:
    record = {}

    try:
        ip = ipaddress.ip_address(ip_data.first_ip)
    except ValueError:
        logger.error(f"Invalid IP address: {ip_data.first_ip}")
        return None

    # Get ASN data
    asn_record = asn_db.get(ip)
    if asn_record:
        if "autonomous_system_number" in asn_record:
            record["asn_number"] = asn_record["autonomous_system_number"]
        if "autonomous_system_organization" in asn_record:
            record["asn_name"] = asn_record["autonomous_system_organization"]

    # Add mnt_by field
    record["mnt_by"] = ip_data.mnt_by if ip_data.mnt_by else "Unknown"

    # Add netname
    record["netname"] = ip_data.netname

    # Add correct subnet
    record["subnet"] = f"{ip_data.first_ip}/{ip_data.subnet}"

    # Get city data
    city_record = city_db.get(ip)
    if city_record:
        if "city" in city_record and "names" in city_record["city"] and "en" in city_record["city"]["names"]:
            record["city_name"] = city_record["city"]["names"]["en"]
        if "country" in city_record:
            if "names" in city_record["country"] and "en" in city_record["country"]["names"]:
                record["country_name"] = city_record["country"]["names"]["en"]
            if "iso_code" in city_record["country"]:
                record["iso_code"] = city_record["country"]["iso_code"]

    return record


def get_network_from_record(
    ip_data: IPData,
) -> Optional[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    try:
        ip = ipaddress.ip_address(ip_data.first_ip)
    except ValueError:
        logger.error(f"Invalid IP address: {ip_data.first_ip}")
        return None

    # Validate subnet mask
    if ip_data.subnet < 0 or (ip.version == 4 and ip_data.subnet > 32) or (ip.version == 6 and ip_data.subnet > 128):
        logger.error(f"Invalid subnet mask: {ip_data.subnet} for IP version: {ip.version}")
        return None

    # Create the network
    try:
        network = ipaddress.ip_network(f"{ip_data.first_ip}/{ip_data.subnet}", strict=False)
        return network
    except ValueError as e:
        logger.error(f"Failed to create network: {e}")
        return None


if __name__ == "__main__":
    main()