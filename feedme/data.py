from os import environ, path
from random import choice, sample

from dotenv import load_dotenv
from yaml import Loader, load

from feedme.models.agents import AgentsModel, InterestModel
from feedme.models.keywords import KeywordsModel
from feedme.models.misc import MiscData
from feedme.models.prompts import PromptsModel

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

# load and validate
agents = AgentsModel(**agent_data)
keywords = KeywordsModel(**keyword_data)
misc = MiscData(**misc_data)
prompts = PromptsModel(**prompt_data)


# TODO: get rid of this, move to data or env
save_path = "/tmp"


def get_save_path() -> str:
    return save_path


def set_save_path(path: str) -> None:
    global save_path
    save_path = path


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

    for key, interest in agents.interests.items():
        if isinstance(interest, (list, str)):
            extend_category(key, [key])
        elif isinstance(interest, dict):
            category = interest.get("category", key)
            extend_category(category, [key])
        elif isinstance(interest, InterestModel):
            category = interest.category or key
            extend_category(category, [key])
        else:
            raise ValueError(f"Invalid interest type: {interest}")

    # print(f"Grouped interests: {grouped_interests}")
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

    # print(f"Random interests: {interests}")
    return interests


def get_interest_story(interest):
    interest_data = agents.interests[interest]
    if isinstance(interest_data, dict):
        interest_story = interest_data["backstory"]
    elif isinstance(interest_data, InterestModel):
        interest_story = interest_data.backstory
    else:
        interest_story = interest_data

    if isinstance(interest_story, list):
        interest_story = choice(interest_story)

    return interest_story


# initialize
group_interests()
