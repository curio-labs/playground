import datetime
import json
import logging
import os
from math import exp
from typing import List, Optional, Tuple

import numpy as np
from openai import OpenAI
from openai.types.chat.chat_completion_token_logprob import TopLogprob
from pydantic import BaseModel, Field

from app.types import Headline, RelevancyScoredHeadline, TokenLogprob

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


class LLMTransformStoriesResponse(BaseModel):
    text: str


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


def _headlines_prompt_from_relevancy_prompt(
    relevancy_prompt: str, headline_content: str
) -> str:
    return f"""
    Is this a relevant headline, according to the below prompt/instruction?
    Output a small list of tags/attributes you could associate with the headline, and nothing else e.g the likely
    topics and subjects of the headline.
    Then with those tags in mind, finally answer either "true" or "false", and nothing else.
    Your final output should be "true" or "false".

    Headline:
    {headline_content}

    Instruction:
    {relevancy_prompt}
    """


def _is_truthy_token(token: str) -> bool:
    return "true" in token.lower() or "yes" in token.lower()


def _is_falsy_token(token: str) -> bool:
    return "false" in token.lower() or "no" in token.lower()


def _extract_top_logprob_token_and_score(top_logprob: TopLogprob) -> Tuple[str, float]:
    return top_logprob.token, top_logprob.logprob


def _extract_true_false_probs(scored_tokens: List[TokenLogprob]) -> Tuple[float, float]:
    truthy_token_logprobs = [
        logprob for token, logprob in scored_tokens if _is_truthy_token(token)
    ]
    falsy_token_logprobs = [
        logprob for token, logprob in scored_tokens if _is_falsy_token(token)
    ]

    true_prob = sum([exp(logprob) for logprob in truthy_token_logprobs])
    false_prob = sum([exp(logprob) for logprob in falsy_token_logprobs])

    if (true_prob + false_prob) == 0:
        return 0.5, 0.5
    else:
        adjusted_true_prob = true_prob / (true_prob + false_prob)
        adjusted_false_prob = false_prob / (true_prob + false_prob)

        return adjusted_true_prob, adjusted_false_prob


def make_llm_request_for_headline_scoring(
    headline: Headline, relevancy_prompt: str
) -> RelevancyScoredHeadline:
    prompt = _headlines_prompt_from_reranking_prompt(relevancy_prompt)
    result = client.chat.completions.create(
        model=OPEN_AI_DEFAULT_MODEL,
        messages=[
            {
                "role": "user",
                "content": _headlines_prompt_from_relevancy_prompt(
                    prompt, headline.model_dump_json()
                ),
            },
        ],
        temperature=ZERO_TEMPERATURE,
        seed=42,
        logprobs=True,
        top_logprobs=5,
    )
    top_logprobs = result.choices[0].logprobs.content[-1].top_logprobs
    top_scored_tokens = [
        _extract_top_logprob_token_and_score(top_logprob)
        for top_logprob in top_logprobs
    ]
    true_prob, false_prob = _extract_true_false_probs(top_scored_tokens)
    return (
        headline,
        true_prob,
    )


def make_concurrent_llm_request_for_headline_scoring(
    headlines: list[Headline], relevancy_prompt: str
) -> List[RelevancyScoredHeadline]:
    tasks: TaskList = [
        (
            make_llm_request_for_headline_scoring,
            (
                headline,
                relevancy_prompt,
            ),
        )
        for headline in headlines
    ]
    results = execute_in_thread_pool(tasks, max_workers=10)
    results = sorted(results, key=lambda x: x[1], reverse=True)
    return results


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


def transform_stories(stories, prompt):
    content = []
    for story in stories:
        data = {
            "title": story["title"],
            "text": story["text"],
        }
        content.append(data)

    result = client.beta.chat.completions.parse(
        model=OPEN_AI_DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(content)},
        ],
        response_format=LLMTransformStoriesResponse,
    )
    data = result.choices[0].message.parsed.json()
    result = json.loads(data)
    return result["text"]


def openai_text_intra_similarity(texts: List[str]) -> np.ndarray:
    embedding_model = "text-embedding-3-small"

    embeddings = [
        res.embedding
        for res in client.embeddings.create(input=texts, model=embedding_model).data
    ]
    embeddings_matrix = np.array(embeddings)
    intra_similarity_matrix = np.dot(embeddings_matrix, embeddings_matrix.T)
    return intra_similarity_matrix
