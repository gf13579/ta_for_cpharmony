# cpharmony.py

import requests
from getpass import getpass
from datetime import datetime, timezone, timedelta
import json
import argparse
from loguru import logger
from pprint import pformat

import cpharmony_consts

class cpharmony_connector:
    session = requests.Session()

    def __init__(self, username, password, region="ap", verify=True):
        self.username = username
        self.password = password
        self.csrf_token = None

        self.session.verify = verify
        self.cloudinfra_gw_url = f"https://cloudinfra-gw.{region}.portal.checkpoint.com"
        self.portal_url = f"https://{region}.portal.checkpoint.com"
    
    def login(self):
        login_uri = "/auth/user"

        payload = {
            "email": self.username,
            "password": self.password,
            "captchaKey": "null"
        }

        # Login
        url = self.cloudinfra_gw_url + login_uri
        response = self.session.post(url=url, verify=False, json=payload)
        logger.info(f"Status code from login: {response.status_code}")
        logger.debug(response.text)
        assert(response.status_code == 200)

        self.csrf_token = response.json()["csrf"]
        self.session.headers.update({"X-Access-Token": self.csrf_token})

    def query_active_attacks(self):
        threat_hunt_uri = "/app/threathunting/prod-gcp-apollo/"
        threat_dash_uri = "/dashboard/endpoint/threathunting#/search"
    
        # Access the Threat Hunting page
        url = self.portal_url + threat_dash_uri
        response = self.session.get(url=url, verify=False)

        # Prepare the query endpoint URL
        url = self.cloudinfra_gw_url + threat_hunt_uri

        # Prepare query date ranges
        current_time = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
        earliest_time = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(timespec="milliseconds").replace("+00:00","Z")

        # Get stats
        stats_payload = cpharmony_consts.TH_STATS_PAYLOAD
        stats_payload["variables"]["queryParam"]["dateRange"]["from"] = earliest_time
        stats_payload["variables"]["queryParam"]["dateRange"]["to"] = current_time

        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(url=url, verify=False, json=stats_payload)
        print(response.status_code)
        print(response.text)

        # Prepare query
        payload = cpharmony_consts.TH_ACTIVE_ATTACKS_PAYLOAD
        payload["variables"]["queryParam"]["dateRange"]["from"] = earliest_time
        payload["variables"]["queryParam"]["dateRange"]["to"] = current_time

        # Get detections
        payload_str = json.dumps(payload, separators=(',', ':'))
        payload_str = payload_str.replace('"null"', 'null')
        response = self.session.post(url=url, verify=False, data=payload_str)

        logger.info(f"Status code from active attack query: {response.status_code}")
        logger.debug(response.text)
        assert(response.status_code == 200)
        return response.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", type=str)
    parser.add_argument("--password", type=str)

    args = parser.parse_args()
    username = args.username
    password = args.password

    cp_connector = cpharmony_connector(username=username, password=password, region="ap", verify=False)

    cp_connector.login()
    results = cp_connector.query_active_attacks()
    
    logger.debug(pformat(results))


if __name__ == "__main__":
    main()
