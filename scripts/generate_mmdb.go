package main

import (
	"database/sql"
	"fmt"
	"log"
	"net"
	"os"

	_ "github.com/mattn/go-sqlite3"
	"github.com/maxmind/mmdbwriter"
	"github.com/maxmind/mmdbwriter/mmdbtype"
	"github.com/oschwald/maxminddb-golang"
)

type IPData struct {
	ID            int
	FirstIP       string
	LastIP        string
	FirstIPInt    string
	LastIPInt     string
	IPVersion     int
	Subnet        int
	NetworkPrefix sql.NullString
	Netname       string
	Country       string
	Description   string
	MntBy         sql.NullString
}

func main() {
	// Apri il database SQLite
	sqlite_db, err := sql.Open("sqlite3", "../geolocation_db.db")
	if err != nil {
		log.Fatal(err)
	}
	defer sqlite_db.Close()

	// Crea un nuovo writer per il database MMDB
	writer, err := mmdbwriter.New(mmdbwriter.Options{
		RecordSize:              32,
		IncludeReservedNetworks: true,
	})
	if err != nil {
		log.Fatal(err)
	}

	// Apri il database ASN di MaxMind
	asn_db, err := maxminddb.Open("../db/base_mmdb/GeoLite2-ASN.mmdb")
	if err != nil {
		log.Fatal(err)
	}
	defer asn_db.Close()

	// Apri il database City di MaxMind
	city_db, err := maxminddb.Open("../db/base_mmdb/GeoLite2-City.mmdb")
	if err != nil {
		log.Fatal(err)
	}
	defer city_db.Close()

	// Esegui la query per ottenere i dati IP
	rows, err := sqlite_db.Query(`
        SELECT * FROM ip_data 
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
		
		`)
	if err != nil {
		log.Fatal(err)
	}
	defer rows.Close()

	var counter = 0
	for rows.Next() {
		var ipData IPData
		err := rows.Scan(&ipData.ID, &ipData.FirstIP, &ipData.LastIP, &ipData.FirstIPInt, &ipData.LastIPInt, &ipData.IPVersion, &ipData.Subnet, &ipData.NetworkPrefix, &ipData.Netname, &ipData.Country, &ipData.Description, &ipData.MntBy)
		if err != nil {
			log.Fatal(err)
		}

		// Verifica se l'IP è privato o riservato
		checkIP := net.ParseIP(ipData.FirstIP)
		if checkIP == nil || checkIP.IsPrivate() {
			log.Printf("FirstIP is Reserved or Invalid: %s", ipData.FirstIP)
			continue
		}

		// Costruisci il record per il database MMDB
		record, err := buildMMDBRecord(ipData, asn_db, city_db)
		if err != nil {
			log.Fatal(err)
		}

		// Ottieni la rete corretta
		network, err := getNetworkFromRecord(ipData)
		if err != nil {
			log.Fatal(err)
		}

		// Inserisci il record nel writer MMDB
		err = writer.Insert(network, record)
		if err != nil {
			log.Fatal(err)
		}

		counter++
		if counter%1000 == 0 {
			fmt.Printf("Processed %d records\n", counter)
		}
	}

	// Crea il file MMDB di output
	fh, err := os.Create("../output/ASN_COUNTRY_AND_CITY.mmdb")
	if err != nil {
		log.Fatal(err)
	}
	defer fh.Close()

	// Scrivi il database MMDB
	_, err = writer.WriteTo(fh)
	if err != nil {
		log.Fatal(err)
	}

	log.Println("Database generated in ../output/ASN_COUNTRY_AND_CITY.mmdb")
}

// buildMMDBRecord costruisce un record MMDB a partire dai dati IP
func buildMMDBRecord(ipData IPData, asnDB, cityDB *maxminddb.Reader) (mmdbtype.Map, error) {
	record := mmdbtype.Map{}

	ip := net.ParseIP(ipData.FirstIP)

	// Ottieni i dati ASN
	var asnRecord map[string]interface{}
	if err := asnDB.Lookup(ip, &asnRecord); err != nil {
		return record, err
	}

	// Aggiungi il numero ASN
	if asnNumber, ok := asnRecord["autonomous_system_number"].(uint64); ok {
		record["asn_number"] = mmdbtype.Uint32(uint32(asnNumber))
	}

	// Aggiungi il nome ASN
	if asnName, ok := asnRecord["autonomous_system_organization"].(string); ok {
		record["asn_name"] = mmdbtype.String(asnName)
	}

	// Aggiungi il campo mnt_by
	var mntByValue string
	if ipData.MntBy.Valid {
		mntByValue = ipData.MntBy.String
	} else {
		mntByValue = "Unknown"
	}
	record["mnt_by"] = mmdbtype.String(mntByValue)

	// Aggiungi il netname
	record["netname"] = mmdbtype.String(ipData.Netname)

	// Aggiungi la subnet corretta
	record["subnet"] = mmdbtype.String(fmt.Sprintf("%s/%d", ipData.FirstIP, ipData.Subnet))

	// Ottieni i dati della città
	var cityRecord map[string]interface{}
	if err := cityDB.Lookup(ip, &cityRecord); err != nil {
		return nil, err
	}

	// Aggiungi il nome della città
	if city, ok := cityRecord["city"].(map[string]interface{}); ok {
		if names, ok := city["names"].(map[string]interface{}); ok {
			if cityName, ok := names["en"].(string); ok {
				record["city_name"] = mmdbtype.String(cityName)
			}
		}
	}

	// Aggiungi il nome del paese e il codice ISO
	if country, ok := cityRecord["country"].(map[string]interface{}); ok {
		if names, ok := country["names"].(map[string]interface{}); ok {
			if countryName, ok := names["en"].(string); ok {
				record["country_name"] = mmdbtype.String(countryName)
			}
		}

		if isoCode, ok := country["iso_code"].(string); ok {
			record["iso_code"] = mmdbtype.String(isoCode)
		}
	}

	return record, nil
}

// getNetworkFromRecord restituisce la rete corretta
func getNetworkFromRecord(ipData IPData) (*net.IPNet, error) {
	// Verifica che la subnet mask sia valida
	if ipData.Subnet < 0 || (ipData.IPVersion == 4 && ipData.Subnet > 32) || (ipData.IPVersion == 6 && ipData.Subnet > 128) {
		return nil, fmt.Errorf("invalid subnet mask: %d for IP version: %d", ipData.Subnet, ipData.IPVersion)
	}

	// Crea la rete utilizzando la subnet mask corretta
	ip := net.ParseIP(ipData.FirstIP)
	if ip == nil {
		return nil, fmt.Errorf("invalid IP address: %s", ipData.FirstIP)
	}

	mask := net.CIDRMask(ipData.Subnet, len(ip)*8)
	if mask == nil {
		return nil, fmt.Errorf("invalid subnet mask: %d", ipData.Subnet)
	}

	network := &net.IPNet{
		IP:   ip.Mask(mask),
		Mask: mask,
	}

	return network, nil
}
