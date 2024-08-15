import json
import os

from openai import OpenAI
from pydantic import BaseModel

from .tables import get_stories

OPEN_AI_DEFAULT_MODEL = "gpt-4o-2024-08-06"
OPEN_AI_API_URL = "https://api.openai.com/v1/chat/completions"
OPEN_AI_API_KEY = os.environ["OPENAI_API_KEY"]

client = OpenAI()


class Story(BaseModel):
    id: str
    title: str


class LLMResponse(BaseModel):
    stories: list[Story]


def make_llm_request(stories, prompt: str, limit=10):
    # remove publication date from stories
    content = [
        {
            "id": str(story.id),
            "title": story.title,
            "text": story.text,
        }
        for story in stories
    ]
    result = client.beta.chat.completions.parse(
        model=OPEN_AI_DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(content)},
        ],
        response_format=LLMResponse,
    )

    result = result.choices[0].message.parsed.json()
    result = json.loads(result)
    return result
