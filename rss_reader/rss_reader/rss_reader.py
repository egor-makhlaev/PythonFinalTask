import sys
import json
import logging
import argparse
from pathlib import Path
from itertools import islice
from urllib.request import urlopen
import xml.etree.ElementTree as ET

VERSION = "2.0"

logging.basicConfig(level=logging.ERROR, format="%(message)s")
logger = logging.getLogger()


def get_response(url):
    """Returns HTTPResponse from server using provided url."""
    global logger

    try:
        logger.info(f"Try to get response from: {url}")

        response = urlopen(url)

    except Exception as e:
        logger.error("Couldn't get good response")
        sys.exit()

    return response


def process_response(response, limit):
    """Returns dictionary with channel info and items. Items number is determined by provided limit argument."""
    global logger

    try:
        logger.info(f"Try to parse response")

        xmldoc = ET.parse(response)
        root = xmldoc.getroot()

        if root.tag != "rss":
            raise Exception("The document isn't RSS feed")

    except Exception as e:
        logger.error("Couldn't parse response")
        sys.exit()

    channel_title = root.findtext("channel/title")
    channel_items = []

    for i, item in enumerate(islice(root.iterfind("channel/item"), 0, max(0, limit) if limit is not None else limit)):
        logger.info(f"Process item № {i + 1}")

        channel_items.append({
            "Title": item.findtext("title"),
            "Date": item.findtext("pubDate"),
            "Link": item.findtext("link"),
        })

    return {"Title": root.findtext("channel/title"), "Items": channel_items}


def print_news(channel):
    """Prints news to console."""
    logger.info(f"Print news")

    print(f"\nFeed: {channel['Title']}")

    for item in channel["Items"]:
        print("")
        for key, value in item.items():
            print(f"{key}: {value}")


def write_json(channel):
    """Write news into data.json file in directory named data."""
    logger.info(f"Write json")

    base = Path(__file__).resolve().parent.parent / "data"
    jsonpath = base / "news.json"
    base.mkdir(exist_ok=True)
    jsonpath.write_text(json.dumps(channel, indent=4))


def main(argv=sys.argv):
    parser = argparse.ArgumentParser(description="Pure Python command-line RSS reader.")
    parser.add_argument("source", type=str, help="RSS URL")
    parser.add_argument("--version", action="version", version=f'"Version {VERSION}"', help="Print version info")
    parser.add_argument("--json", action="store_true", help="Print result as JSON in stdout")
    parser.add_argument("--verbose", action="store_true", help="Outputs verbose status messages")
    parser.add_argument("--limit", type=int, help="Limit news topics if this parameter provided")

    args = parser.parse_args(argv[1:])

    if args.verbose:
        logger.setLevel(logging.INFO)

    response = get_response(args.source)
    channel_info_and_items = process_response(response, args.limit)
    print_news(channel_info_and_items)

    if args.json:
        write_json(channel_info_and_items)


if __name__ == "__main__":
    main()
