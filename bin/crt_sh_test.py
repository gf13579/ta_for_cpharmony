# crt_sh_test.py

import requests
from loguru import logger
import sys
from datetime import datetime

CRTSH_BASE_URL = "https://crt.sh/"


class crtsh:
    def __init__(self):
        pass

    def _do_query_crt_sh(self, domain, entity, label, max_days_old=None):
        session = requests.session()
        url = CRTSH_BASE_URL
        params = {"q": domain, "output": "json"}
        logger.debug(f"url is {url}. params is {params}")

        response = session.get(url=url, params=params)
        resp_json = response.json()
        results = []

        for result in resp_json:
            entry_timestamp = date_object = datetime.strptime(
                result["entry_timestamp"][:18], "%Y-%m-%dT%H:%M:%S"
            )
            time_between_discovery = datetime.now() - entry_timestamp
            if max_days_old and (time_between_discovery.days > max_days_old):
                continue
            result["dork_metadata"] = {
                "label": label,
                "entity": entity,
                "query": domain,
            }
            results.append(result)

        logger.info(f"Returning {len(results)} results")
        return results


def main() -> int:
    my_crtsh = crtsh()
    my_crtsh._do_query_crt_sh(
        domain="intalock.com.au",
        entity="intalock",
        label="subs_from_certs",
        # max_days_old=30,
    )


if __name__ == "__main__":
    sys.exit(main())
