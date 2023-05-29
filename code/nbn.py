import logging
import urllib.parse

import diskcache
import requests


class NBNApi:
    """Interacts with NBN's unofficial API."""
    LOOKUP_URL = "https://places.nbnco.net.au/places/v1/autocomplete?query="
    DETAIL_URL = "https://places.nbnco.net.au/places/v2/details/"
    HEADERS = {
        "referer": "https://www.nbnco.com.au/"
    }

    def __init__(self):
        # 1GB LRU cache of gnaf_pid->loc_id and loc_id->details
        self.cache = diskcache.Cache('cache', statistics=True)

    def close(self):
        # TODO Each thread that accesses a cache should also call close on the cache.
        self.cache.close()
        hits, misses = self.cache.stats(reset=True)
        logging.info('Cache stats: %d hits, %d misses', hits, misses)

    def get_nbn_data_json(self, url):
        """Gets a JSON response from a URL."""
        return requests.get(url, stream=True, headers=self.HEADERS).json()

    def get_nbn_loc_id(self, key: str, address: str) -> str:
        """Return the NBN locID for the provided address, or None if there was an error."""
        if key in self.cache:
            return self.cache[key]
        loc_id = self.get_nbn_data_json(self.LOOKUP_URL + urllib.parse.quote(address))["suggestions"][0]["id"]
        self.cache[key] = loc_id  # cache indefinitely
        return loc_id

    def extended_get_nbn_loc_id(self, key: str, address: str) -> str:
        """Return the NBN locID for the provided address, following the addressSplitDetails if required."""
        loc_id = self.get_nbn_loc_id(key, address)
        if not loc_id.startswith("LOC"):
            details = self.get_nbn_loc_details(loc_id)
            new_address = ' '.join(details['addressSplitDetails'].values())
            if new_address.lower() != address.lower():
                loc_id = self.get_nbn_loc_id("X" + key, new_address)
        return loc_id

    def get_nbn_loc_details(self, id: str) -> dict:
        """Return the NBN details for the provided id, or None if there was an error."""
        if id in self.cache:
            return self.cache[id]
        details = self.get_nbn_data_json(self.DETAIL_URL + id)
        self.cache.set(id, details, expire=60 * 60 * 24 * 7)  # cache for 7 days
        return details
