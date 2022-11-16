from urllib.parse import quote
import sys
from requests import get, request
from bs4 import BeautifulSoup
from pyuseragents import random

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36 Edg/100.0.1185.44"
PARSER = "html.parser"
RETRY_COUNT = 5


def do_query(base_url="https://www.google.com", query="", user_agent=USER_AGENT):
    params = {"q": query}
    response = get(url=base_url, params=params)
    print(response.text)
    pass


def main():
    do_query(query="python")


if __name__ == "__main__":
    sys.exit(main())
