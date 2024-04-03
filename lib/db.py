import os
import sqlite3

class SQLiteHandler:
    def __init__(self, db_name):
        self.db_name = db_name

    def create_table(self):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS ip_data
                    (id INTEGER PRIMARY KEY,
                    first_ip TEXT,
                    last_ip TEXT,
                    first_ip_int INTEGER,
                    last_ip_int INTEGER,
                    ip_version INTEGER,
                    network_prefix TEXT,
                    netname TEXT,
                    country TEXT,
                    descr TEXT,
                    mnt_by TEXT)''')
        c.execute('''CREATE INDEX IF NOT EXISTS idx_first_ip_int ON ip_data (first_ip_int)''')
        c.execute('''CREATE INDEX IF NOT EXISTS idx_last_ip_int ON ip_data (last_ip_int)''')
        c.execute('''CREATE INDEX IF NOT EXISTS idx_ip_version ON ip_data (ip_version)''')
        c.execute('''CREATE INDEX IF NOT EXISTS idx_network_prefix ON ip_data (network_prefix)''')
        conn.commit()
        conn.close()


    def insert_data(self, data):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        for entry in data:
            first_ip_int = entry.get('first_ip_int')
            last_ip_int = entry.get('last_ip_int')

            query = '''INSERT INTO ip_data 
                    (first_ip, last_ip, ip_version, network_prefix,
                        netname, country, descr, mnt_by'''
            values = [entry['first_ip'], entry['last_ip'], entry['ip_version'],
                    entry.get('network_prefix', None), entry.get('netname', None),
                    entry['country'], entry.get('descr', None), entry.get('mnt-by', None)]

            if first_ip_int is not None:
                query += ', first_ip_int'
                values.append(first_ip_int)
            if last_ip_int is not None:
                query += ', last_ip_int'
                values.append(last_ip_int)

            query += ') VALUES (?' + ', ?' * (len(values) - 1) + ')'

            c.execute(query, values)

        conn.commit()
        conn.close()
