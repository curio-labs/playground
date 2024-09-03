import copy
import random


def sample_stories(stories, limit, sampling_method):
    if sampling_method == "top-n":
        return stories[:limit]
    if sampling_method == "random":
        stories = copy.deepcopy(stories)
        random.shuffle(stories)
        return stories[:limit]
    if sampling_method == "repeat":
        return stories[:limit]
    raise ValueError(f"Invalid sampling method: {sampling_method}")
