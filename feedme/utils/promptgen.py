from logging import getLogger
from random import sample
from re import sub

from packit.formats import format_bullet_list
from traceloop.sdk.decorators import task

from feedme.data import llms, prompts, quality_keywords, remove_concepts
from feedme.utils.gpt2 import generate_text
from feedme.utils.misc import cleanup_sentence

logger = getLogger(__name__)


@task()
def generate_keywords(agent, description):
    return agent(
        prompts["generate_keywords"],
        description=description,
        example_concepts=format_bullet_list(remove_concepts),
    )


@task()
def elaborate_characters(agent, description, keywords):
    return agent(
        prompts["elaborate_characters"],
        description=description,
        keywords=keywords,
    )


@task()
def elaborate_scene(agent, scene):
    return agent(
        prompts["elaborate_scene"],
        scene=scene,
    )


@task()
def elaborate_quality(agent, keywords):
    return agent(
        prompts["elaborate_quality"],
        keywords=keywords,
        quality_keywords=quality_keywords,
    )


@task()
def remove_abstract_concepts(agent, keywords):
    return agent(
        prompts["remove_concepts"],
        keywords=keywords,
    )


@task()
def generate_examples(keywords, length=120, n=5, k=3):
    keyword_list = keywords.split(",")
    keyword_list = [keyword.strip() for keyword in keyword_list]

    example_prompts = []
    for _ in range(n):
        selected_keywords = sample(keyword_list, k=min(k, len(keyword_list)))
        logger.info("generating example prompt with keywords: %s", selected_keywords)
        prompt = generate_text(llms["gpt2"], ",".join(selected_keywords), length)
        prompt = sub(r"^(.+)(?:,.*)$", r"\1", prompt)
        example_prompts.append(prompt)

    return example_prompts


@task()
def generate_prompt(agent, description, qk=6):
    keywords = generate_keywords(agent, description)
    characters = elaborate_characters(agent, description, keywords)
    scene = elaborate_scene(agent, description)

    example_prompts = generate_examples(keywords)

    prompt = agent(
        prompts["generate_prompt"],
        example_prompts=format_bullet_list(example_prompts),
        characters=characters,
        keywords=keywords,
        scene=scene,
    )
    prompt = remove_abstract_concepts(agent, prompt)
    prompt = cleanup_sentence(prompt, trailing_period=False)

    quality = sample(quality_keywords, k=qk)
    return prompt + ", " + ", ".join(quality)
