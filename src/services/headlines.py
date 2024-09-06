import enum
import html
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import httpx
from pydantic import BaseModel
from retry import retry

from src.services import get_stories_by_id, get_vector_search_stories

SUBSCRIPTION_KEY = os.environ["BING_NEWS_API_KEY"]
BING_NEWS_TOPIC_URL = "https://api.bing.microsoft.com/v7.0/news"
BING_NEWS_SEARCH_URL = "https://api.bing.microsoft.com/v7.0/news/search"


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


class HeadlineStoryQueryStrategy(enum.Enum):
    USE_TITLE = enum.auto()
    USE_SUMMARY = enum.auto()
    USE_TITLE_AND_SUMMARY = enum.auto()

    @staticmethod
    def from_user_str(user_str: str) -> "HeadlineStoryQueryStrategy":
        if user_str == "match-on-title":
            return HeadlineStoryQueryStrategy.USE_TITLE
        elif user_str == "match-on-summary":
            return HeadlineStoryQueryStrategy.USE_SUMMARY
        elif user_str == "match-on-both":
            return HeadlineStoryQueryStrategy.USE_TITLE_AND_SUMMARY
        else:
            raise ValueError(
                f"Unrecognized user str for HeadlineStoryQueryStrategy: {user_str}"
            )


HTTP_TOO_MANY_REQUEST = 429
HTTP_SERVER_ERROR = 500


LOG = logging.getLogger(__name__)


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


def _bing_request(url: str, headers: Dict, params: Dict) -> Dict:
    try:
        resp = httpx.get(url=url, headers=headers, params=params)
        resp.raise_for_status()
        if "category" in params:
            return {**resp.json(), "category": params["category"]}
        else:
            return {**resp.json(), "category": "TopGeneralHeadlines"}
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


def get_all_bing_news_headlines(
    market: str,
    use_top_headlines_feed: Optional[bool] = False,
    headline_limit: Optional[int] = 20,
) -> List[Headline]:
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

    if use_top_headlines_feed:
        url = BING_NEWS_SEARCH_URL
        results = retry_policy(
            lambda: _bing_request(
                url, base_headers, {**params, "count": headline_limit, "q": "top news"}
            )
        )()
        results = [results]
    else:
        url = BING_NEWS_TOPIC_URL
        results = ThreadPoolExecutor(max_workers=5).map(
            lambda category: retry_policy(
                lambda: _bing_request(
                    url, base_headers, {**params, "category": category}
                )
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


def match_headlines_to_internal_stories(
    headlines: List[Headline], query_strategy: HeadlineStoryQueryStrategy
) -> List[Optional[Tuple[Dict, float]]]:
    return list(
        ThreadPoolExecutor(max_workers=10).map(
            lambda h: match_headline_to_internal_story(h, query_strategy), headlines
        )
    )


def match_headline_to_internal_story(
    headline: Headline, query_strategy: Optional[HeadlineStoryQueryStrategy] = None
) -> Optional[Tuple[Dict, float]]:
    query_strategy = query_strategy or HeadlineStoryQueryStrategy.USE_SUMMARY
    match query_strategy:
        case HeadlineStoryQueryStrategy.USE_TITLE:
            query_text = headline.title
        case HeadlineStoryQueryStrategy.USE_SUMMARY:
            query_text = headline.summary
        case HeadlineStoryQueryStrategy.USE_TITLE_AND_SUMMARY:
            query_text = f"{headline.title}   {headline.summary}"
        case _:
            raise ValueError(f"Unsupported query strategy {query_strategy}")

    similarity_results = get_vector_search_stories(
        start_date=(datetime.now() - timedelta(days=3)).isoformat(),
        limit=3,
        vector_search=query_text,
    )
    if len(similarity_results) == 0:
        return None
    else:
        best_match_story_id = similarity_results[0]["id"]
        best_match_score = similarity_results[0]["similarity_score"]
        best_match_stories = get_stories_by_id([best_match_story_id])["data"]
        if len(best_match_stories) == 0:
            LOG.warning(
                f"Story with ID {best_match_story_id} exists in vector DB but not in playground DB."
            )
            return {
                "id": best_match_story_id,
                "title": "(An internal story was found but does not yet exist in the Playground DB)",
                "text": "(An internal story was found but does not yet exist in the Playground DB)",
            }, best_match_score
        else:
            return best_match_stories[0], best_match_score
