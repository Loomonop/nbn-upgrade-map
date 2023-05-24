import argparse
import logging
import requests
from concurrent.futures import ThreadPoolExecutor
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


def get_addresses(target_suburb, target_state):
    """return a list of addresses for the provided suburb+state from the database"""
    cur.execute(f"SELECT * FROM gnaf_202302.address_principals WHERE locality_name = '{target_suburb}' AND state = '{target_state}' LIMIT 100000")

    rows = cur.fetchall()

    addresses = []
    for row in rows:
        address = {
            "name": f"{row[15]} {row[16]} {row[17]}",
            "location": [float(row[25]), float(row[24])]
        }
        addresses.append(address)

    return addresses


def get_data(address):
    """fetch the upgrade+tech details for the provided address from the NBN API and add to the address dict"""
    locID = None
    try:
        r = requests.get(lookupUrl + urllib.parse.quote(address["name"]), stream=True, headers={"referer": "https://www.nbnco.com.au/"})
        locID = r.json()["suggestions"][0]["id"]
    except requests.exceptions.RequestException as e:
        return e
    if not locID.startswith("LOC"):
        return
    try:
        r = requests.get(detailUrl + locID, stream=True, headers={"referer": "https://www.nbnco.com.au/"})
        status = r.json()
    except requests.exceptions.RequestException as e:
        return e

    address["locID"] = locID
    address["tech"] = status["addressDetail"]["techType"]
    address["upgrade"] = status['addressDetail']['altReasonCode']


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


def get_all_addresses(suburb, state):
    """Fetch all addresses for suburb+state from the DB and then fetch the upgrade+tech details for each address"""
    logging.info('Fetching all addresses for %s, %s', suburb.title(), state)
    addresses = get_addresses(suburb, state)
    addresses = sorted(addresses, key=lambda k: k['name'])
    logging.info('Fetched %d addresses from database', len(addresses))

    threads = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        for address in addresses:
            threads.append(executor.submit(get_data, address))

    return addresses


def format_addresses(addresses):
    """convert the list of addresses (with upgrade+tech fields) into a GeoJSON FeatureCollection"""
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

    return formatted_addresses


def write_geojson_file(suburb, state, formatted_addresses):
    """write the GeoJSON FeatureCollection to a file"""
    if formatted_addresses["features"]:
        if not os.path.exists(f"results/{state}"):
            os.makedirs(f"results/{state}")
        target_suburb_file = suburb.lower().replace(" ", "-")
        with open(f"results/{state}/{target_suburb_file}.geojson", "w") as outfile:
            logging.info('Writing results to %s', outfile.name)
            json.dump(formatted_addresses, outfile)
    else:
        logging.warning('No addresses found for %s, %s', suburb.title(), state)


def process_suburb(target_suburb, target_state):
    suburb, state = select_suburb(target_suburb, target_state)
    if suburb == 'NA':
        logging.error('No more suburbs to process')
    else:
        addresses = get_all_addresses(suburb, state)
        formatted_addresses = format_addresses(addresses)
        write_geojson_file(suburb, state, formatted_addresses)


if __name__ == "__main__":
    LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
    logging.basicConfig(level=LOGLEVEL)

    parser = argparse.ArgumentParser(description='Create GeoJSON files containing FTTP upgrade details for the prescribed suburb.')
    parser.add_argument('target_suburb', help='The name of a suburb, for example "bli-bli", or "NA" to process the next suburb')
    parser.add_argument('target_state', help='The name of a state, for example "QLD"')
    args = parser.parse_args()

    process_suburb(args.target_suburb, args.target_state)
