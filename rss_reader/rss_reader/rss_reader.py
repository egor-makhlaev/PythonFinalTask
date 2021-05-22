import sys
import json
import logging
import argparse
from pathlib import Path
from urllib.error import URLError
from urllib.error import HTTPError
from urllib.request import urlopen
import xml.etree.ElementTree as ET

try:
    from logger_config import get_logger
    from local_storage import LocalStorage
    from format_converter import ToPdfConverter
    from format_converter import ToHtmlConverter
except ImportError:
    from .logger_config import get_logger
    from .local_storage import LocalStorage
    from .format_converter import ToPdfConverter
    from .format_converter import ToHtmlConverter

from pathvalidate.argparse import validate_filepath_arg

VERSION = "3.0"

logger = get_logger()
local_storage = LocalStorage("localstorage")


def get_response(url):
    """
    Returns HTTPResponse from server using provided url. Exits program if can't return good response.

    Parameters:
        url (str): URL to RSS feed content

    Returns:
        response (http.client.HTTPResponse): Response from server
    """
    try:
        response = urlopen(url)

    except HTTPError as e:
        logger.error(f"The server couldn't fulfill the request.\nError code: {e.code}")
        sys.exit()
    except URLError as e:
        logger.error(f"Failed to reach a server.\nReason: {e.reason}")
        sys.exit()
    except Exception as e:
        logger.error(f"Generic exception: {e}")
        sys.exit()

    logger.info(f"Got response from: {url}")

    return response


def parse_response(response):
    """
    Returns list with news items. Exits program if can't parse response.

    Parameters:
        response (http.client.HTTPResponse): Response from server provided by get_response function

    Returns:
        [{"Feed": (str), "Title", (str), "Date": (srt), "Link": (str), "image_url": (str)}]: List of dicts
    """
    try:
        xmldoc = ET.parse(response)
        root = xmldoc.getroot()

        if root.tag != "rss":
            raise Exception("The document isn't RSS feed")

    except Exception as e:
        logger.error("Couldn't parse response")
        sys.exit()

    channel_title = root.findtext("channel/title")
    news_items = []

    for index_of_news_item, news_item in enumerate(root.iterfind("channel/item")):
        image_element = news_item.find('{http://search.yahoo.com/mrss/}content')

        news_items.append({
            "Feed": channel_title,
            "Title": news_item.findtext("title"),
            "Date": news_item.findtext("pubDate"),
            "Link": news_item.findtext("link"),
            "image_url": image_element.get("url") if image_element is not None else None
        })

    logger.info(f"Parsed {index_of_news_item + 1} items from response")

    response.close()

    return news_items


def limit_news_items(news_items, limit):
    """
    Returns limited list with news items. Items number is determined by provided limit argument.

    Parameters:
        news_items [{"Feed": (str), "Title", (str), "Date": (srt), "Link": (str), "image_url": (str)}]: List of dicts
        limit (None) or (int): Max number of items in result dictionary, if (None) all items are included

    Returns:
        [{"Feed": (str), "Title", (str), "Date": (srt), "Link": (str), "image_url": (str)}]: Limited list of dicts
    """
    calculated_limit = max(0, limit) if limit is not None else limit

    if limit != calculated_limit:
        logger.warning(f"You provided wrong --limit argument, your output set to {calculated_limit} news items")
    else:
        logger.info(f"Set output to {len(news_items) if calculated_limit is None else calculated_limit} news items")

    return news_items[:calculated_limit]


def print_news(news_items):
    """
    Prints news to stdout.

    Parameters:
        news_items [{"Feed": (str), "Title", (str), "Date": (srt), "Link": (str), "image_url": (str)}]: List of dicts
    """
    logger.info(f"Print news items")

    for news_item in news_items:
        print()
        print(f"Feed: {news_item['Feed']}")
        print(f"Title: {news_item['Title']}")
        print(f"Date: {news_item['Date']}")
        print(f"Link: {news_item['Link']}")


def print_json(news_items):
    """
    Prints news as JSON in stdout.

    Parameters:
        news_items [{"Feed": (str), "Title", (str), "Date": (srt), "Link": (str), "image_url": (str)}]: List of dicts
    """
    logger.info(f"Print news items as JSON")

    print(json.dumps(news_items, indent=4, ensure_ascii=False))


def main(argv=sys.argv):
    parser = argparse.ArgumentParser(description="Pure Python command-line RSS reader.")
    parser.add_argument("source", nargs="?" if "--date" in argv else None, type=str, help="RSS URL")
    parser.add_argument("--version", action="version", version=f'"Version {VERSION}"', help="Print version info")
    parser.add_argument("--json", action="store_true", help="Print result as JSON in stdout")
    parser.add_argument("--verbose", action="store_true", help="Outputs verbose status messages")
    parser.add_argument("--limit", type=int, help="Limit news topics if this parameter provided")
    parser.add_argument("--date", type=str, help="Return news topics which were published in specific date")
    parser.add_argument("--to-html", type=validate_filepath_arg, help="Save news in .html format by provided path")
    parser.add_argument("--to-pdf", type=validate_filepath_arg, help="Save news in .pdf format by provided path")

    args = parser.parse_args(argv[1:])

    if args.verbose:
        logger.setLevel(logging.INFO)

    if args.date:

        if args.source:
            news_items = local_storage.get_news_items_by_url_and_date(args.source, args.date)
        else:
            news_items = local_storage.get_news_items_by_url_and_date(None, args.date)

        if not news_items:
            logger.error("Couldn't find news topics which were published in specific date")
            sys.exit()

    else:
        response = get_response(args.source)
        news_items = parse_response(response)
        news_items = local_storage.set_news_items_by_url(args.source, news_items)

    news_items = limit_news_items(news_items, args.limit)
    print_news(news_items)

    if args.json:
        print_json(news_items)

    if args.to_html:
        html_converter = ToHtmlConverter(directory_path=args.to_html, file_name="rss-news.html")
        html_converter.convert(news_items)

    if args.to_pdf:
        pdf_converter = ToPdfConverter(directory_path=args.to_pdf, file_name="rss-news.pdf")
        pdf_converter.convert(news_items)


if __name__ == "__main__":
    main()
