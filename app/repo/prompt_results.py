from django.db import IntegrityError

from app import models as md
from src import services

PROMPT_NAME_DUPLICATE_ERROR = (
    'duplicate key value violates unique constraint "prompt_results_prompt_name_key"'
    "\nDETAIL:  Key (prompt_name)"
)


class PromptResultExistsError(Exception):
    pass


def save(results):
    prompt_name = results["prompt_name"]
    prompt_attributes = {
        "vector_query": results["vector_query"],
        "start_date": results["start_date"],
        "prompt_value": results["prompt_value"],
        "sampling_method": results["sampling_method"],
        "story_limit": results["story_limit"],
        "attribute": results["attribute"],
        "is_vector_search": results["is_vector_search"],
        "is_gpt_ranking": results["is_gpt_ranking"],
    }

    stories = {"data": []}
    for story_id, similarity_score, vector_position in zip(
        results["story_ids"],
        results["similarity_scores"],
        results["vector_positions"],
    ):
        stories["data"].append(
            {
                "id": story_id,
                "similarity_score": similarity_score,
                "vector_position": vector_position,
            }
        )

    prompt_result = md.PromptResult(
        prompt_name=prompt_name,
        prompt_attributes=prompt_attributes,
        stories=stories,
    )
    try:
        prompt_result.save()
    except IntegrityError as e:
        if str(e)[: len(PROMPT_NAME_DUPLICATE_ERROR)] == PROMPT_NAME_DUPLICATE_ERROR:
            raise PromptResultExistsError(
                f"Prompt result with name '{prompt_name}' already exists."
            ) from None
        raise e
    except Exception as e:
        raise e

    return prompt_result


def get_all():
    return md.PromptResult.objects.all()


def get_stories_by_prompt_id(prompt_id):
    stories = md.PromptResult.objects.get(id=prompt_id).stories["data"]
    results = []
    db_stories = services.get_stories_by_id(
        story_ids=[story["id"] for story in stories]
    )["data"]
    for story in stories:
        result = next(
            (
                {
                    "id": db_story["id"],
                    "title": db_story["title"],
                    "text": db_story["text"],
                    "published_at": db_story["published_at"],
                    "publication": db_story["publication"],
                    "author": db_story["author"],
                    "type": db_story["type"],
                    "classification": db_story["classification"],
                    "similarity_score": story["similarity_score"],
                    "vector_position": story["vector_position"],
                }
                for db_story in db_stories
                if db_story["id"] == story["id"]
            ),
            None,
        )
        if result:
            results.append(result)

    results = sorted(results, key=lambda x: x["similarity_score"], reverse=True)
    return results
