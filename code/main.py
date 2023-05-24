"""Main script for fetching NBN data for a suburb from the NBN API and writing to a GeoJSON file."""

import argparse
import json
import logging
import os
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

import psycopg2
import requests
from psycopg2.extras import NamedTupleCursor

LOOKUP_URL = "https://places.nbnco.net.au/places/v1/autocomplete?query="
DETAIL_URL = "https://places.nbnco.net.au/places/v2/details/"
HEADERS = {"referer": "https://www.nbnco.com.au/"}


def connect_to_db(database: str, host: str, port: str, user: str, password: str):
    """Connect to the database"""
    global conn
    try:
        conn = psycopg2.connect(
            database=database,
            host=host,
            port=port,
            user=user,
            password=password,
            cursor_factory=NamedTupleCursor
        )
    except psycopg2.OperationalError as err:
        logging.error('Unable to connect to database: %s', err)
        sys.exit(1)

    global cur
    cur = conn.cursor()


def get_addresses(target_suburb: str, target_state: str) -> list:
    """Return a list of addresses for the provided suburb+state from the database."""
    query = f"""
        SELECT address, locality_name, postcode, latitude, longitude
        FROM gnaf_202302.address_principals
        WHERE locality_name = '{target_suburb}' AND state = '{target_state}'
        LIMIT 100000"""

    cur.execute(query)

    addresses = []
    row = cur.fetchone()
    while row is not None:
        address = {
            "name": f"{row.address} {row.locality_name} {row.postcode}",
            "location": [float(row.longitude), float(row.latitude)]
        }
        addresses.append(address)
        row = cur.fetchone()

    return addresses


def get_nbn_data(address: str):
    """Fetch the upgrade+tech details for the provided address from the NBN API and add to the address dict."""
    loc_id = None
    try:
        req = requests.get(
            LOOKUP_URL + urllib.parse.quote(address["name"]), stream=True, headers=HEADERS)
        loc_id = req.json()["suggestions"][0]["id"]
    except requests.exceptions.RequestException as err:
        logging.debug('Error finding NBN locID for %s: %s',
                      address["name"], err)
        return
    if not loc_id.startswith("LOC"):
        return
    try:
        req = requests.get(DETAIL_URL + loc_id, stream=True, headers=HEADERS)
        status = req.json()
    except requests.exceptions.RequestException as err:
        logging.debug('Error fetching NBN data for %s: %s',
                      address["name"], err)
        return

    address["locID"] = loc_id
    address["tech"] = status["addressDetail"]["techType"]
    if "altReasonCode" in status['addressDetail']:
        address["upgrade"] = status['addressDetail']['altReasonCode']
    else:
        address["upgrade"] = "NULL_NA"


def select_suburb(target_suburb: str, target_state: str) -> tuple:
    """Return a (state,suburb) tuple based on the provided input or the next suburb in the list."""
    target_suburb = target_suburb.upper()
    target_state = target_state.upper()
    if target_suburb == "NA":
        # load the list of previously completed suburbs
        with open("results/results.json", "r", encoding="utf-8") as file:
            completed_suburbs = {}  # state -> set-of-suburbs
            for completed in json.load(file)["suburbs"]:
                state, suburb = completed['state'], completed['internal']
                if state not in completed_suburbs:
                    completed_suburbs[state] = set()
                completed_suburbs[state].add(suburb)
        # load the list of all suburbs
        with open("results/suburbs.json", "r", encoding="utf-8") as file:
            suburb_list = json.load(file)
            for state, suburbs in suburb_list["states"].items():
                for suburb in suburbs:
                    if state not in completed_suburbs or suburb not in completed_suburbs[state]:
                        return suburb, state

    return target_suburb, target_state


def get_all_addresses(suburb: str, state: str) -> list:
    """Fetch all addresses for suburb+state from the DB and then fetch the upgrade+tech details for each address."""
    logging.info('Fetching all addresses for %s, %s', suburb.title(), state)
    addresses = get_addresses(suburb, state)
    addresses = sorted(addresses, key=lambda k: k['name'])
    logging.info('Fetched %d addresses from database', len(addresses))

    threads = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        for address in addresses:
            threads.append(executor.submit(get_nbn_data, address))

    return addresses


def format_addresses(addresses: list) -> dict:
    """Convert the list of addresses (with upgrade+tech fields) into a GeoJSON FeatureCollection."""
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


def write_geojson_file(suburb: str, state: str, formatted_addresses: dict):
    """Write the GeoJSON FeatureCollection to a file."""
    if formatted_addresses["features"]:
        if not os.path.exists(f"results/{state}"):
            os.makedirs(f"results/{state}")
        target_suburb_file = suburb.lower().replace(" ", "-")
        with open(f"results/{state}/{target_suburb_file}.geojson", "w", encoding="utf-8") as outfile:
            logging.info('Writing results to %s', outfile.name)
            json.dump(formatted_addresses, outfile)
    else:
        logging.warning('No addresses found for %s, %s', suburb.title(), state)


def process_suburb(target_suburb: str, target_state: str):
    """Query the DB for addresses, augment them with upgrade+tech details, and write the results to a file."""
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

    parser = argparse.ArgumentParser(
        description='Create GeoJSON files containing FTTP upgrade details for the prescribed suburb.')
    parser.add_argument(
        'target_suburb', help='The name of a suburb, for example "bli-bli", or "NA" to process the next suburb')
    parser.add_argument(
        'target_state', help='The name of a state, for example "QLD"')
    parser.add_argument(
        '-u', '--dbuser', help='The name of the database user', default='postgres')
    parser.add_argument(
        '-p', '--dbpassword', help='The password for the database user', default='password')
    parser.add_argument(
        '-H', '--dbhost', help='The hostname for the database', default='localhost')
    parser.add_argument(
        '-P', '--dbport', help='The port number for the database', default='5433')
    args = parser.parse_args()

    connect_to_db("postgres", args.dbhost, args.dbport,
                  args.dbuser, args.dbpassword)
    process_suburb(args.target_suburb, args.target_state)
