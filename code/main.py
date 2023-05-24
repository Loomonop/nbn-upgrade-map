import argparse
import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.parse
import psycopg2
import json
import os

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

def get_addresses(target_location):
    cur.execute(f"SELECT * FROM gnaf_202302.address_principals WHERE locality_name = '{target_location[0]}' AND state = '{target_location[1]}' LIMIT 100000")

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


def select_suburb(target_suburb, target_state):
    """return a (state,suburb) tuple based on the provided input or the next suburb in the list"""
    target_suburb = target_suburb.upper()
    target_state = target_state.upper()
    if target_suburb == "NA":
        # load the list of previously completed suburbs
        with open("results/results.json", "r") as f:
            completed_suburbs = {}  # state -> set-of-suburbs
            for completed in json.load(f)["suburbs"]:
                state, suburb = completed['state'], completed['internal']
                if state not in completed_suburbs:
                    completed_suburbs[state] = set()
                completed_suburbs[state].add(suburb)
        # load the list of all suburbs
        with open("results/suburbs.json", "r") as f:
            suburb_list = json.load(f)
            for state, suburbs in suburb_list["states"].items():
                for suburb in suburbs:
                    if state not in completed_suburbs or suburb not in completed_suburbs[state]:
                        return suburb, state

    return target_suburb, target_state


if __name__ == "__main__":
    LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
    logging.basicConfig(level=LOGLEVEL)

    parser = argparse.ArgumentParser(description='Create GeoJSON files containing FTTP upgrade details for the prescribed suburb.')
    parser.add_argument('target_suburb', help='The name of a suburb, for example "bli-bli", or "NA" to process the next suburb')
    parser.add_argument('target_state', help='The name of a state, for example "QLD"')
    args = parser.parse_args()

    target_suburb, target_state = target_location = select_suburb(args.target_suburb, args.target_state)
    target_suburb_display = target_suburb.title()
    target_suburb_file = target_suburb.lower().replace(" ", "-")

    logging.info('Processing %s, %s', target_suburb_display, target_state)
    addresses = get_addresses(target_location)
    addresses = sorted(addresses, key=lambda k: k['name'])
    logging.info('Fetched %d addresses from database', len(addresses))
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
    if len(formatted_addresses["features"]) > 0:
        if not os.path.exists(f"results/{target_state}"):
            os.makedirs(f"results/{target_state}")
        with open(f"results/{target_state}/{target_suburb_file}.geojson", "w") as outfile:
            logging.info('Writing results to %s', outfile.name)
            json.dump(formatted_addresses, outfile)