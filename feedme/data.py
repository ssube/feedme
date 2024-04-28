from os import environ, path
from random import choice, sample

from dotenv import load_dotenv
from yaml import Loader, load

load_dotenv(environ.get("FEEDME_ENV", ".env"), override=True)

data_base = environ.get("FEEDME_DATA", "feedme/data")

with open(path.join(data_base, "agents.yaml"), "r") as f:
    agent_data = load(f, Loader)

with open(path.join(data_base, "keywords.yaml"), "r") as f:
    keyword_data = load(f, Loader)

with open(path.join(data_base, "misc.yaml"), "r") as f:
    misc_data = load(f, Loader)

with open(path.join(data_base, "prompts.yaml"), "r") as f:
    prompt_data = load(f, Loader)

# don't look at this part, it's not good
agent_backstory = agent_data["backstory"]
special_interests = agent_data["interests"]
quality_keywords = keyword_data["quality"]
remove_concepts = keyword_data["remove"]
modifiers = misc_data["modifiers"]
post_formats = misc_data["formats"]
checkpoint_models = misc_data["checkpoints"]
size_presets = misc_data["sizes"]
prompts = prompt_data  # ["prompts"]
llms = misc_data["llms"]
onnx = misc_data["onnx"]
bot = misc_data["bot"]


save_path = "/tmp"


def get_save_path() -> str:
    return save_path


def set_save_path(path: str) -> None:
    global save_path
    save_path = path


def get_bot_name() -> str:
    return bot["name"]


# grouped interests
grouped_interests = {}


def group_interests():
    """
    Group interests by category. If the interest is a string, assume the key is the category and put it into its own
    group.
    """
    global grouped_interests

    def extend_category(category, interests):
        if category in grouped_interests:
            grouped_interests[category].extend(interests)
        else:
            grouped_interests[category] = interests

    for key, interest in special_interests.items():
        if isinstance(interest, (list, str)):
            extend_category(key, [key])
        elif isinstance(interest, dict):
            category = interest.get("category", key)
            extend_category(category, [key])
        else:
            raise ValueError(f"Invalid interest type: {interest}")

    print(f"Grouped interests: {grouped_interests}")
    return grouped_interests


def random_interest(k=6, interests=None):
    """
    Get k random interests from the grouped interests, one from each category.
    """

    keys = interests or list(grouped_interests.keys())

    # make sure k is valid
    k = min(k, len(keys))

    # select k random categories
    categories = sample(keys, k)

    # select one interest from each category
    interests = []
    for category in categories:
        group = grouped_interests[category]
        interests.append(choice(group))

    print(f"Random interests: {interests}")
    return interests


def get_interest_story(interest):
    interest_data = special_interests[interest]
    if isinstance(interest_data, dict):
        interest_story = interest_data["backstory"]
    else:
        interest_story = interest_data

    if isinstance(interest_story, list):
        interest_story = choice(interest_story)

    return interest_story


# initialize
group_interests()
