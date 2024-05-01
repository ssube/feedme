from logging import getLogger
from random import sample
from re import sub

from packit.formats import format_bullet_list
from packit.loops import loop_retry
from traceloop.sdk.decorators import task

from feedme.data import keywords, misc, prompts
from feedme.utils.gpt2 import generate_text
from feedme.utils.misc import cleanup_sentence

logger = getLogger(__name__)


@task()
def generate_keywords(agent, description):
    return agent(
        prompts.generate_keywords,
        description=description,
        example_concepts=format_bullet_list(keywords.remove),
    )


@task()
def elaborate_characters(agent, description, base_keywords):
    return agent(
        prompts.elaborate_characters,
        description=description,
        keywords=base_keywords,
    )


@task()
def elaborate_scene(agent, scene):
    return agent(
        prompts.elaborate_scene,
        scene=scene,
    )


@task()
def elaborate_quality(agent, base_keywords):
    return agent(
        prompts.elaborate_quality,
        keywords=base_keywords,
        quality_keywords=base_keywords.quality,
    )


@task()
def remove_abstract_concepts(agent, base_keywords):
    return loop_retry(
        agent,
        prompts.remove_concepts,
        context={
            "keywords": base_keywords,
        },
        result_parser=one_line_parser,
    )


@task()
def generate_examples(base_keywords, length=180, n=5, k=3):
    keyword_list = base_keywords.split(",")
    keyword_list = [keyword.strip() for keyword in keyword_list]

    example_prompts = []
    for _ in range(n):
        selected_keywords = sample(keyword_list, k=min(k, len(keyword_list)))
        logger.info("generating example prompt with keywords: %s", selected_keywords)
        prompt = generate_text(misc.llms.gpt2, ",".join(selected_keywords), length)
        prompt = sub(r"^(.+)(?:,.*)$", r"\1", prompt)
        example_prompts.append(cleanup_prompt(prompt))

    return example_prompts


@task()
def generate_prompt(agent, description, qk=6):
    base_keywords = cleanup_prompt(generate_keywords(agent, description))
    characters = elaborate_characters(agent, description, base_keywords)
    scene = elaborate_scene(agent, description)

    example_prompts = generate_examples(base_keywords)

    prompt = loop_retry(
        agent,
        prompts.generate_prompt,
        context={
            "example_prompts": format_bullet_list(example_prompts),
            "characters": characters,
            "keywords": base_keywords,
            "scene": scene,
        },
        result_parser=one_line_parser,
    )
    prompt = remove_abstract_concepts(agent, prompt)
    prompt = cleanup_prompt(prompt)

    quality = sample(keywords.quality, k=qk)
    return prompt + ", " + ", ".join(quality)


def cleanup_prompt(prompt):
    # remove common prefixes
    for prefix in ["Prompt:", "Keywords:", "Characters:", "Scene:"]:
        prompt = prompt.replace(prefix, "")

    # remove repeated commas, with or without spaces
    prompt = sub(r",\s*,", ",", prompt)

    return cleanup_sentence(prompt, trailing_period=False)


def one_line_parser(text: str, **kwargs):
    if text.count("\n") > 0:
        raise ValueError(prompts.generate_prompt_retry)

    return text
