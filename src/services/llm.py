import datetime
import json
import logging
import os
from typing import List, Optional

from openai import OpenAI
from pydantic import BaseModel, Field

from .headlines import Headline
from .utils import TaskList, execute_in_thread_pool

OPEN_AI_DEFAULT_MODEL = "gpt-4o-2024-08-06"
OPEN_AI_API_URL = "https://api.openai.com/v1/chat/completions"
OPEN_AI_API_KEY = os.environ["OPENAI_API_KEY"]

client = OpenAI()

LOG = logging.getLogger(__name__)

ZERO_TEMPERATURE = 0.000000001


class Story(BaseModel):
    id: str
    title: str


class LLMMultiStoryResponse(BaseModel):
    stories: list[Story]


class LLMSingleStoryValueResponse(BaseModel):
    value: float


class HeadlineIdentifier(BaseModel):
    id: str = Field(description="The identifier of the originally supplied headline.")


class LLMHeadlineRerankingResponse(BaseModel):
    headlines: list[HeadlineIdentifier] = Field(
        description="The list of headline ids reranked according to the provided instruction."
    )


def _headlines_prompt_from_reranking_prompt(reranking_prompt: str) -> str:
    return f"""
    Rerank these headlines in accordance with the below instruction:

    {reranking_prompt}
    """


def make_llm_request_for_headline_reranking(
    headlines: List[Headline], reranking_prompt: str
) -> List[Headline]:
    headlines_id_mapping = {h.id: h for h in headlines}
    prompt = _headlines_prompt_from_reranking_prompt(reranking_prompt)
    result: LLMHeadlineRerankingResponse = client.beta.chat.completions.parse(
        model=OPEN_AI_DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": json.dumps([headline.dict() for headline in headlines]),
            },
        ],
        response_format=LLMHeadlineRerankingResponse,
        temperature=ZERO_TEMPERATURE,
    )
    parsed_result: LLMHeadlineRerankingResponse = result.choices[0].message.parsed
    reranked_headlines = []
    for reranked_headline in parsed_result.headlines:
        reranked_headline_id = reranked_headline.id
        if reranked_headline_id in headlines_id_mapping:
            reranked_headlines.append(headlines_id_mapping[reranked_headline_id])
        else:
            warn_message = f"""
            LLM hallucinated a headline identifier: {reranked_headline_id}
            Possible ids: {list(headlines_id_mapping.keys())}
            """
            LOG.warning(warn_message)
    return reranked_headlines


def make_llm_request_for_story_batch(stories, prompt: str, limit=10):
    # remove publication date from stories
    story_llm_ids_lookup = {}
    content = []
    for idx, story in enumerate(stories):
        story_llm_ids_lookup[idx] = story.id
        data = {
            "id": idx,
            "title": story.title,
            "text": story.text,
        }
        content.append(data)
    result = client.beta.chat.completions.parse(
        model=OPEN_AI_DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(content)},
        ],
        response_format=LLMMultiStoryResponse,
    )

    result = result.choices[0].message.parsed.json()
    result = json.loads(result)
    stories = result["stories"]
    for story in stories:
        idx = story["id"]
        story["id"] = story_llm_ids_lookup[int(idx)]
    return stories


def make_llm_request_for_single_story(story, prompt: str, attributes):
    content = {}

    for attribute in attributes:
        value = getattr(story, attribute, None)
        if isinstance(value, datetime.datetime):
            content[attribute] = value.isoformat()
        else:
            content[attribute] = value

    result = client.beta.chat.completions.parse(
        model=OPEN_AI_DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(content)},
        ],
        response_format=LLMSingleStoryValueResponse,
    )

    result = result.choices[0].message.parsed.json()
    result = json.loads(result)
    result["id"] = story.id
    result["title"] = story.title
    result["value"] = result["value"] if result["value"] is not None else 0
    result["similarity_score"] = story.similarity_score
    result["position"] = story.position
    result["publication"] = story.publication
    result["published_at"] = story.published_at
    return result


def make_concurrent_llm_requests_for_stories(
    prompt: str,
    stories: list[Story],
    attributes: Optional[list[str]] = None,
):
    tasks: TaskList = [
        (
            make_llm_request_for_single_story,
            (
                story,
                prompt,
                attributes,
            ),
        )
        for story in stories
    ]
    results = execute_in_thread_pool(tasks, max_workers=10)
    results = sorted(results, key=lambda x: x["value"], reverse=True)
    del stories
    return results
