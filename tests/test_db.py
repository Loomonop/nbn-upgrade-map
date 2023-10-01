import os
from argparse import ArgumentParser, Namespace

import db

SAMPLE_ADDRESSES_DB_FILE = f"{os.path.dirname(os.path.realpath(__file__))}/data/sample-addresses.sqlite"


def test_get_address():
    address_db = db.connect_to_db(Namespace(dbhost=SAMPLE_ADDRESSES_DB_FILE))
    addresses = address_db.get_addresses("SOMERVILLE", "VIC")
    assert len(addresses) == 30
    assert addresses[0].name == "83 GUELPH STREET SOMERVILLE 3912"
    assert addresses[0].gnaf_pid == "GAVIC421048228"


def test_get_counts_by_suburb():
    address_db = db.connect_to_db(Namespace(dbhost=SAMPLE_ADDRESSES_DB_FILE))
    counts = address_db.get_counts_by_suburb()
    assert counts["VIC"]["SOMERVILLE"] == 30
    assert counts["VIC"]["SOMERS"] == 10
    assert counts["VIC"]["SOMERTON"] == 1
    assert len(counts["NSW"]) == 2
    assert len(counts["SA"]) == 1
    assert len(counts["TAS"]) == 1
    assert len(counts["WA"]) == 1


def test_get_extents_by_suburb():
    address_db = db.connect_to_db(Namespace(dbhost=SAMPLE_ADDRESSES_DB_FILE))
    extents = address_db.get_extents_by_suburb()
    assert extents["VIC"]["SOMERVILLE"] == (
        (-38.23846838, 145.162399),
        (-38.21306546, 145.22678832),
    )


def test_add_db_arguments():
    parser = ArgumentParser()
    db.add_db_arguments(parser)
    args = parser.parse_args([])
    assert args.dbuser == "postgres"
    assert args.dbpassword == "password"
    assert args.dbhost == "localhost"
    assert args.dbport == "5433"
    assert args.create_index


# TODO: test postgres with mocks
