import psycopg2
import json

conn = psycopg2.connect(
    database="postgres",
    host="localhost",
    user="postgres",
    password="password",
    port="5433"
)

cur = conn.cursor()

# get all unique localities and their state from gnaf_202302.address_principals
cur.execute(f"SELECT DISTINCT locality_name, state FROM gnaf_202302.address_principals")

rows = cur.fetchall()

suburbs = {
    "states": {
        "NSW": [],
        "VIC": [],
        "QLD": [],
        "SA": [],
        "WA": [],
        "TAS": [],
        "NT": [],
        "ACT": []
    }
}

for row in rows:
    if row[1] in suburbs["states"] and row[0] not in suburbs["states"][row[1]]:
        suburbs["states"][row[1]].append(row[0])

with open("results/suburbs.json", "w") as outfile:
    json.dump(suburbs, outfile, indent=4)