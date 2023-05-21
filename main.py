import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.parse
import psycopg2
import json

lookupUrl = "https://places.nbnco.net.au/places/v1/autocomplete?query="
detailUrl = "https://places.nbnco.net.au/places/v2/details/"

conn = psycopg2.connect(
    database="postgres",
    host="localhost",
    user="postgres",
    password="password",
    port="5433"
)

cur = conn.cursor()

def get_addresses():
    cur.execute("SELECT * FROM gnaf_202302.address_principals WHERE locality_name = 'NEW LAMBTON' LIMIT 10000")

    rows = cur.fetchall()

    addresses = []

    for row in rows:
        address = {}
        address["name"] = f"{row[15]} {row[16]} {row[17]}"
        address["location"] = [float(row[25]), float(row[24])]
        addresses.append(address)

    return addresses

def get_data(address):
    locID = None
    try:
        r = requests.get(lookupUrl + urllib.parse.quote(address["name"]), stream=True, headers={"referer":"https://www.nbnco.com.au/"})
        locID = r.json()["suggestions"][0]["id"]
    except requests.exceptions.RequestException as e:
       return e
    if not locID.startswith("LOC"):
        return
    try:
        r = requests.get(detailUrl + locID, stream=True, headers={"referer":"https://www.nbnco.com.au/"})
        status = r.json()
    except requests.exceptions.RequestException as e:
       return e

    address["locID"] = locID
    address["tech"] = status["addressDetail"]["techType"]
    address["upgrade"] = status['addressDetail']['altReasonCode']

    return
 
def runner(addresses):
    threads= []
    with ThreadPoolExecutor(max_workers=20) as executor:
        for address in addresses:
            threads.append(executor.submit(get_data, address))
       
if __name__ == "__main__":
    addresses = get_addresses()
    runner(addresses)
    formatted_addresses = {
        "type": "FeatureCollection",
        "features": []
    }
    for address in addresses:
        if "upgrade" in address and "tech" in address:
            formatted_address = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": address["location"]
                },
                "properties": {
                    "name": address["name"],
                    "locID": address["locID"],
                    "tech": address["tech"],
                    "upgrade": address["upgrade"]
                }
            }
            formatted_addresses["features"].append(formatted_address)
    with open('results/newlambton.geojson', 'w') as outfile:
        json.dump(formatted_addresses, outfile)