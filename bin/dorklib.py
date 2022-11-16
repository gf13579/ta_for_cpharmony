import sys
import argparse
import os

import requests
from loguru import logger
from datetime import datetime
import time
import random

import googlesearch
from duckduckgo_search import ddg

CSE_BASE_URL = "https://customsearch.googleapis.com"
CSE_ENDPOINT_URI = "/customsearch/v1"
CRTSH_BASE_URL = "https://crt.sh/"
GOOGLE_GET_MAX_RESULTS = 20


class dorklib:
    def __init__(self, cse_api_key, cse_id, query_date_range=0, google_get_max_wait=5):
        self._cse_id = cse_id
        self._api_key = cse_api_key
        self._query_date_range = int(query_date_range)
        self._google_get_max_wait = int(google_get_max_wait)

    def do_queries(self, entities, queries):
        results = []

        # Get enabled queries only
        queries = [
            q for q in queries if q["disabled"] not in ("1", "true", "True")
        ] or []

        # Get enabled entities only
        entities = [
            e for e in entities if e["disabled"] not in ("1", "true", "True")
        ] or []

        logger.debug(entities)
        logger.debug(queries)

        crtsh_queries = [q for q in queries if q["service"] == "crt.sh"] or []

        for q in crtsh_queries:
            for entity in entities:
                # results.extend(
                yield self._do_query_crt_sh(
                    entity["site"],
                    entity=entity["entity"],
                    label=q["label"],
                    max_days_old=self._query_date_range,
                )
                # )

        # Get google dorks
        google_cse_queries = [q for q in queries if q["service"] == "google_cse"] or []

        for q in google_cse_queries:
            logger.debug(f"query {q['query']}")
            for entity in entities:
                # if we can fully format the query, add it to our prepared queries
                formatted_query = None
                try:
                    formatted_query = q["query"].format(**entity)
                except KeyError as e:
                    pass
                if formatted_query:
                    # results.extend(
                    yield self._do_query_google_cse(
                        formatted_query, q["label"], entity["entity"]
                    )
                # )

        # Get google dorks
        google_get_queries = [q for q in queries if q["service"] == "google_get"] or []

        for q in google_get_queries:
            logger.debug(f"query {q['query']}")
            for entity in entities:
                # if we can fully format the query, add it to our prepared queries
                formatted_query = None
                try:
                    formatted_query = q["query"].format(**entity)
                except KeyError as e:
                    pass
                if formatted_query:
                    # results.extend(
                    yield self._do_query_google_get(
                        formatted_query, q["label"], entity["entity"]
                    )
                # )
            time.sleep(random.randint(3, self._google_get_max_wait + 3))

        # Get DDG dorks
        ddg_queries = [
            q for q in queries if q["service"].startswith("duckduckgo_")
        ] or []

        for q in ddg_queries:
            logger.debug(f"query {q['query']}")
            for entity in entities:
                # if we can fully format the query, add it to our prepared queries
                formatted_query = None
                try:
                    formatted_query = q["query"].format(**entity)
                except KeyError as e:
                    pass
                if formatted_query:
                    # results.extend(
                    yield self._do_query_duckduckgo_get(
                        formatted_query, q["label"], entity["entity"]
                    )
                # )
            time.sleep(random.randint(3, self._google_get_max_wait + 3))

        return results

    def _do_query_crt_sh(self, domain, entity, label, max_days_old=None):
        results = []
        session = requests.session()
        url = CRTSH_BASE_URL
        params = {"q": domain, "output": "json"}
        logger.debug(
            f"url is {url}. params is {params}. max_days_old is {max_days_old}"
        )

        response = None
        for x in range(5):
            response = session.get(url=url, params=params)
            # logger.debug("status code is {}".format(response.status_code))
            if response.status_code == 200:
                break
            time.sleep(random.randint(3, 8))
        if response.status_code != 200:
            return results

        resp_json = response.json()
        # logger.debug(resp_json)

        for result in resp_json:
            entry_timestamp = date_object = datetime.strptime(
                result["entry_timestamp"][:18], "%Y-%m-%dT%H:%M:%S"
            )
            # logger.debug(f"entry_timestamp is {entry_timestamp}")
            time_between_discovery = datetime.now() - entry_timestamp
            # logger.debug(
            #     f"time_between_discovery.days is {time_between_discovery.days}"
            # )
            if max_days_old and (time_between_discovery.days > max_days_old):
                continue
            result["dork_metadata"] = {
                "label": label,
                "entity": entity,
                "query": domain,
            }
            results.append(result)
            # yield result

        logger.info(f"Returning {len(results)} results")
        return results

    def _do_query_duckduckgo_get(self, formatted_query, label, entity):
        logger.debug(
            f"formatted_query: {formatted_query}, label: {label}, entity: {entity}."
        )
        results = {}

        qdr = self._query_date_range

        if qdr == 1:
            ddg_time = "d"
        if qdr == 365:
            ddg_time = "y"
        elif 28 <= qdr <= 31:
            ddg_time = "m"
        elif 5 <= qdr >= 7:
            ddg_time = "w"
        else:
            ddg_time = None

        logger.debug("About to call ddg")
        ddg_results = ddg(
            keywords=formatted_query,
            region="wt-wt",
            safesearch="Off",
            time=ddg_time,
            max_results=GOOGLE_GET_MAX_RESULTS,
        )
        print(results)

        results = []
        for search_result in ddg_results:
            result = search_result
            result["dork_metadata"] = {
                "label": label,
                "entity": entity,
                "results_retrieved": f"{len(ddg_results)} of {GOOGLE_GET_MAX_RESULTS} requested",
                "query": formatted_query,
            }
            result["url"] = result.pop("href")
            result["description"] = result.pop("body")

            results.append(result)

        logger.info(f"Returning {len(results)} results")
        return results

    def _do_query_google_get(self, formatted_query, label, entity):
        logger.debug(
            f"formatted_query: {formatted_query}, label: {label}, entity: {entity}. query_date_range is {str(self._query_date_range)}"
        )
        results = {}

        googlesearch_results = googlesearch.Search(
            query=formatted_query,
            retry_count=5,
            number_of_results=GOOGLE_GET_MAX_RESULTS,
            query_date_range="d" + str(self._query_date_range),
        )

        logger.info(f"Response code: {googlesearch_results.last_response_code}")

        results = []
        for gsr in googlesearch_results.results:
            result = gsr.__dict__
            result["dork_metadata"] = {
                "label": label,
                "entity": entity,
                "results_retrieved": f"{len(googlesearch_results.results)} of {GOOGLE_GET_MAX_RESULTS-1} requested",
                "query": formatted_query,
            }
            results.append(result)

        logger.info(f"Returning {len(results)} results")
        return results

    def _do_query_google_cse(self, formatted_query, label, entity):
        logger.debug(
            f"formatted_query: {formatted_query}, label: {label}, entity: {entity}, formatted_query: {formatted_query}"
        )
        results = {}

        params = {
            "cx": {self._cse_id},
            "key": {self._api_key},
            "q": {formatted_query},
            "safe": "off",
            "sort": "date",
        }

        if self._query_date_range and self._query_date_range > 0:
            params["dateRestrict"] = f"d{self._query_date_range}"

        session = requests.session()
        url = CSE_BASE_URL + CSE_ENDPOINT_URI
        params_clean = {i: params[i] for i in params if i != "key"}
        params_clean["key"] = "redacted"
        logger.debug(f"url is {url}. params is {params_clean}")

        total_results = -1
        response = session.get(url=url, params=params)

        if response.status_code >= 400:
            logger.error(f"Response: {response.status_code}. Reason: {response.reason}")

        if "items" in response.json():
            results = response.json()["items"]
            total_results = response.json()["queries"]["request"][0]["totalResults"]

            for result in results:
                result["dork_metadata"] = {
                    "label": label,
                    "entity": entity,
                    "results_retrieved": len(results),
                    "total_results": total_results,
                }

        logger.info(f"Returning {len(results)} results")
        return results


#################################################


def main() -> int:
    parser = argparse.ArgumentParser(description="Query Splunk via API")
    parser.add_argument("--cse_id", nargs=1, required=True)
    parser.add_argument("--query_date_range", nargs=1, required=True)
    args = parser.parse_args()

    cse_id = args.cse_id[0]
    query_date_range = args.query_date_range[0]

    if "CSE_API_KEY" in os.environ:
        api_key = os.environ["CSE_API_KEY"]
    else:
        logger.error("Store API key in env var for testing: CSE_API_KEY")
        logger.error("e.g. export CSE_API_KEY=your_api_key_here")
        return 1

    dorker = dorklib(
        cse_id=cse_id, cse_api_key=api_key, query_date_range=query_date_range
    )

    results = dorker.do_queries(entities=entities, queries=queries)

    # results = api_search.do_query_google_get(
    #     query=query, target=target, target_type=target_type, label="blah"
    # )
    print(results)


def main_ddg(entities, queries):
    dorker = dorklib(
        cse_id=None, cse_api_key=None, query_date_range=28, google_get_max_wait=5
    )
    results = dorker.do_queries(entities=entities, queries=queries)


def main_google_get():
    dorker = dorklib(
        cse_id=None, cse_api_key=None, query_date_range=7, google_get_max_wait=5
    )

    # query = "site:suncorp.com.au inurl:login"
    query = "uber eats"

    results = dorker._do_query_google_get(
        formatted_query=query, label="login_pages", entity="Suncorp"
    )
    # print(results)


if __name__ == "__main__":
    queries = [
        {
            "disabled": "0",
            "label": "login_pages",
            "query": 'site:github.com "{org_name}"',
            "service": "google_cse",
        }
    ]
    entities = [
        {
            "copyright_statement": "Copyright Suncorp-Metway Ltd ABN 66 010 831 722",
            "disabled": "0",
            "entity": "suncorp",
            "org_name": "Suncorp",
            "site": "suncorp.com.au",
        }
    ]
    sys.exit(main())
    # sys.exit(main_ddg(entities, queries))
    # sys.exit(main_google_get())
