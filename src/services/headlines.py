import html
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List

import httpx
from pydantic import BaseModel
from retry import retry

SUBSCRIPTION_KEY = os.environ["BING_NEWS_API_KEY"]
BING_NEWS_TOPIC_URL = "https://api.bing.microsoft.com/v7.0/news"


class RateLimitedError(Exception):
    pass


class BingAPIServerError(Exception):
    pass


class Headline(BaseModel):
    id: str
    title: str
    summary: str
    publication: str
    category: str


HTTP_TOO_MANY_REQUEST = 429
HTTP_SERVER_ERROR = 500


def _bing_categories_gb() -> List[str]:
    return [
        "Business",
        "Entertainment",
        "Health",
        "Politics",
        "ScienceAndTechnology",
        "Sports",
        "UK",
        "World",
    ]


def _bing_categories_us() -> List[str]:
    return [
        "Business",
        "Entertainment",
        "Health",
        "Politics",
        "Products",
        "ScienceAndTechnology",
        "Technology",
        "Science",
        "Sports",
        "US",
        "World",
    ]


def _bing_request(headers: Dict, params: Dict) -> Dict:
    try:
        resp = httpx.get(url=BING_NEWS_TOPIC_URL, headers=headers, params=params)
        resp.raise_for_status()
        return {**resp.json(), "category": params["category"]}
    except httpx.HTTPStatusError as err:
        if err.response.status_code == HTTP_TOO_MANY_REQUEST:
            raise RateLimitedError() from err
        elif err.response.status_code >= HTTP_SERVER_ERROR:
            raise BingAPIServerError(f"{err.response.text}") from err
        else:
            raise err


def _id_from_bing_headline(headline_result: Dict) -> str:
    headline_description = headline_result["description"]
    headline_description = html.unescape(headline_description)
    split_headline_description = headline_description.split(" ")
    reasonable_word_length = 3
    first_5_words = [
        word.lower()
        for word in split_headline_description
        if len(word) > reasonable_word_length
    ][:5]
    return "-".join(first_5_words)


def get_all_bing_news_headlines(market: str) -> List[Headline]:
    market_str = "en-GB" if market == "GB" else "en-US"
    categories = _bing_categories_gb() if market == "GB" else _bing_categories_us()
    base_headers = {"Ocp-Apim-Subscription-Key": SUBSCRIPTION_KEY}
    params = {
        "textDecorations": True,
        "textFormat": "HTML",
        "sortBy": "Relevance",
        "freshness": "day",
        "mkt": market_str,
    }
    retry_policy = retry(
        exceptions=(RateLimitedError, BingAPIServerError),
        tries=3,
        delay=2,
        backoff=4,
        max_delay=20,
    )

    results = ThreadPoolExecutor(max_workers=5).map(
        lambda category: retry_policy(
            lambda: _bing_request(base_headers, {**params, "category": category})
        )(),
        categories,
    )
    headlines = {}
    for result in results:
        for headline_result in result["value"]:
            id_for_headline = _id_from_bing_headline(headline_result)
            if id_for_headline not in headlines:
                headlines[id_for_headline] = Headline(
                    id=id_for_headline,
                    title=html.unescape(headline_result["name"]),
                    summary=html.unescape(headline_result["description"]),
                    publication=headline_result["provider"][0]["name"],
                    category=result["category"],
                )
    return list(headlines.values())
