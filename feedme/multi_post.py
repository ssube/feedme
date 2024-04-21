from collections import Counter
from json import dumps
from os import environ, makedirs, path
from random import choice, randint, sample
from shutil import move, rmtree
from time import monotonic

from packit.agent import Agent, agent_easy_connect
from packit.groups import Panel
from packit.results import int_result
from packit.tracing import set_tracer, trace
from packit.utils import logger_with_colors
from traceloop.sdk import Traceloop
from traceloop.sdk.decorators import task

from feedme.data import (
    agent_backstory,
    get_bot_name,
    llms,
    modifiers,
    post_formats,
    prompts,
    set_save_path,
    special_interests,
)
from feedme.tools.civitai_tools import close_page, create_post, launch_login
from feedme.tools.html_tools import template_post
from feedme.tools.image_tools import get_image_data
from feedme.tools.onnx_tools import download_input_images, generate_image_tool
from feedme.utils.misc import (
    cleanup_sentence,
    format_bullet_list,
    hash_post,
    monotonic_delta,
    parse_ranking,
    rank_list,
    sanitize_name,
    str_parser,
)
from feedme.utils.promptgen import generate_prompt

# set up logging and tracing
logger = logger_with_colors(__name__, level="DEBUG")

Traceloop.init(disable_batch=True)
set_tracer("traceloop")


# start the debugger, if needed
if environ.get("DEBUG", "false").lower() == "true":
    import debugpy

    debugpy.listen(5679)
    logger.info("waiting for debugger to attach...")
    debugpy.wait_for_client()


# set up paths
root_path = environ["ROOT_PATH"]
approval_path = path.join(root_path, "approval")
approved_path = path.join(root_path, "approved")
rejected_path = path.join(root_path, "rejected")
working_path = path.join(root_path, "working")


# configure LLMs
manager_llm = agent_easy_connect(
    model=llms["manager"],
    temperature=float(llms["manager_temperature"]),
)
creative_llm = agent_easy_connect(
    model=llms["creative"],
    temperature=float(llms["creative_temperature"]),
)


def random_interest(k=6):
    interests = list(special_interests.keys())
    return sample(interests, k=k)


def InterestAgent(interest: str, **kwargs):
    backstory = agent_backstory["Interest Scientist"]
    interest_story = special_interests[interest]

    return Agent(
        f"{interest} scientist",
        f"{backstory} {interest_story}",
        {
            **kwargs,
            "interest": interest,
        },
        creative_llm,
    )


def make_post_paths():
    makedirs(working_path, exist_ok=True)
    makedirs(working_path, exist_ok=True)
    makedirs(working_path, exist_ok=True)


def append_post_notice(body: str, hash: str):
    bot_name = get_bot_name()
    notice_template = prompts["post_notice"]
    return notice_template.format(body=body, bot_name=bot_name, hash=hash)


def do_post(post_slug, post_description, post_hash, post, tool="html"):
    description = append_post_notice(post_description, post_hash)
    if tool == "civitai":
        # post to Civitai
        try:
            launch_login()
            post_id = create_post(
                [
                    path.join(approved_path, post_slug, filename)
                    for filename in post["files"]
                ],
                mature=True,
                title=post["title"],
                description=description,
            )
            logger.info("created post: %s", post_id)
        except Exception:
            logger.exception("failed to post to Civitai")
        finally:
            try:
                close_page()
            except Exception:
                logger.exception("failed to close Civitai page")
    elif tool == "html":
        # generate an HTML page
        template_post(
            post["files"],
            description=description,
            title=post["title"],
            mature=True,
            destination=path.join(approved_path, post_slug, "post.html"),
        )
    else:
        logger.error("unknown post tool: %s", tool)


@task()
def generate_concepts(interest_agents, min_words=2, max_words=4):
    interest_panel = Panel(list(interest_agents.values()), name="concepts")
    panel_results = interest_panel.sample(
        prompts["generate_concepts"],
        {
            "min_words": min_words,
            "max_words": max_words,
        },
        result_parser=str_parser,
    )

    logger.info("concept results: %s", panel_results)

    return panel_results


@task()
def concept_ranking_each_bool(interest_agents, concepts):
    total_ranking = Counter()

    for concept in concepts.values():
        interest_panel = Panel(list(interest_agents.values()), "concepts")
        panel_results = interest_panel.sample(
            prompts["rank_concepts_binary"],
            {
                "concept": concept,
            },
        )

        for interest, ranking in panel_results.items():
            logger.info("ranking for %s interest: %s", interest, ranking)
            if ranking:
                total_ranking[concept] += 1

    logger.info("total concept ranking: %s", total_ranking.most_common())

    # select the top concepts
    top_concepts = total_ranking.most_common(1)
    logger.info("top concepts: %s", top_concepts)

    return top_concepts


@task()
def concept_ranking_each_scale(
    interest_agents,
    concepts,
    ranking_threshold=3,  # TODO: move to data
    max_score=5,  # TODO: move to data
    count=1,
):
    selected_concepts = []
    selected_rankings = Counter()

    for concept in concepts.values():
        interest_panel = Panel(list(interest_agents.values()), name="concepts")
        try:
            panel_results = interest_panel.sample(
                prompts["rank_concepts_scale"],
                {
                    "concept": concept,
                    "max_score": max_score,
                },
                result_parser=int_result,
            )
            image_rankings = list(panel_results.values())
        except Exception:
            logger.exception("failed to parse ranking")
            image_rankings = []

        if len(image_rankings) > 0:
            average_ranking = sum(image_rankings) / len(image_rankings)
        else:
            average_ranking = 0

        if average_ranking >= ranking_threshold:
            logger.info(
                "concept %s met threshold: %s >= %s",
                concept,
                average_ranking,
                ranking_threshold,
            )
            selected_concepts.append(concept)

            # counter can only handle integers, so multiply by 10
            selected_rankings[concept] = int(average_ranking * 10)
        else:
            logger.warning(
                "concept %s did not meet threshold: %s < %s",
                concept,
                average_ranking,
                ranking_threshold,
            )

    # select the top images
    top_images = selected_rankings.most_common(count)
    logger.info("top images: %s", top_images)

    return top_images


@task()
def image_size_choice(interest_agents, description):
    total_ratios = Counter()

    for scientist in interest_agents.values():
        image_ratio = scientist(
            prompts["choose_image_size"],
            description=description,
        ).lower()

        # TODO: use packit enum result parser
        landscape_index = image_ratio.find("landscape")
        portrait_index = image_ratio.find("portrait")
        square_index = image_ratio.find("square")

        if landscape_index < 0:
            landscape_index = 999

        if portrait_index < 0:
            portrait_index = 999

        if square_index < 0:
            square_index = 999

        if landscape_index < portrait_index and landscape_index < square_index:
            total_ratios["landscape"] += 1
        elif portrait_index < landscape_index and portrait_index < square_index:
            total_ratios["portrait"] += 1
        elif square_index < landscape_index and square_index < portrait_index:
            total_ratios["square"] += 1
        else:
            logger.warning(
                "invalid image ratio: %s (%s, %s, %s)",
                image_ratio,
                landscape_index,
                portrait_index,
                square_index,
            )

    logger.info("total ratios: %s", total_ratios)
    return total_ratios.most_common(1)[0][0]


@task()
def image_ranking_sort(interests, interest_agents, image_data, count, max_rank_retry=3):
    total_ranking = Counter()

    for interest in interests:
        rank_retry = 0
        scientist = interest_agents[interest]

        while rank_retry < max_rank_retry:
            careful_warning = ""
            if rank_retry > 0:
                careful_warning = prompts["rank_image_sort_retry"]

            ranking = scientist(
                prompts["rank_image_sort"],
                careful_warning=careful_warning,
                image_data=image_data,
            )
            logger.info("ranking for %s interest: %s", interest, ranking)

            try:
                # TODO: make sure images all exist
                ranking = parse_ranking(ranking)
                ranking = rank_list(ranking)
                logger.debug("ranked list: %s", ranking)
                total_ranking.update(ranking)
                break
            except Exception:
                logger.exception("failed to parse ranking: %s", ranking)
                ranking = []

            logger.error(
                "failed to generate valid ranking for %s interest, retrying", interest
            )
            rank_retry += 1

    logger.info("total ranking: %s", total_ranking.most_common())

    # select the top images
    top_images = total_ranking.most_common(count)
    logger.info("top images: %s", top_images)

    return top_images


@task()
def image_ranking_each_bool(interests, interest_agents, image_data, count, description):
    total_ranking = Counter()

    for image in image_data:
        caption = image["caption"]
        filename = image["filename"]

        interest_panel = Panel(
            [interest_agents[interest] for interest in interests], name="images"
        )
        panel_results = interest_panel.sample(
            prompts["rank_image_binary"],
            {
                "caption": caption,
            },
        )

        for interest, ranking in panel_results.items():
            logger.info("ranking for %s interest: %s", interest, ranking)
            if ranking:
                total_ranking[filename] += 1

    logger.info("total ranking: %s", total_ranking.most_common())

    # select the top images
    top_images = total_ranking.most_common(count)
    logger.info("top images: %s", top_images)

    return top_images


@task()
def image_ranking_each_scale(
    interests,
    interest_agents,
    image_data,
    count,
    description,
    ranking_threshold=3.5,  # TODO: move to data
    max_score=5,  # TODO: move to data
):
    selected_images = []
    selected_rankings = Counter()

    for image in image_data:
        caption = image["caption"]
        filename = image["filename"]

        interest_panel = Panel(
            [interest_agents[interest] for interest in interests], name="images"
        )
        panel_results = interest_panel.sample(
            prompts["rank_image_scale"],
            {
                "caption": caption,
                "description": description,
                "max_score": max_score,
            },
            result_parser=int_result,
        )
        image_rankings = list(panel_results.values())

        # image_rankings = [4]

        if len(image_rankings) > 0:
            average_ranking = sum(image_rankings) / len(image_rankings)
        else:
            average_ranking = 0

        if average_ranking >= ranking_threshold:
            logger.info(
                "image %s met threshold: %s >= %s",
                filename,
                average_ranking,
                ranking_threshold,
            )
            selected_images.append(filename)

            # counter can only handle integers, so multiply by 10
            selected_rankings[filename] = int(average_ranking * 10)
        else:
            logger.warning(
                "image %s did not meet threshold: %s < %s",
                filename,
                average_ranking,
                ranking_threshold,
            )

    # select the top images
    top_images = selected_rankings.most_common(count)
    logger.info("top images: %s", top_images)

    return top_images


@task()
def image_critique_group_bool(critics, context):
    panel = Panel(list(critics.values()), name="critics")
    critiques = panel.sample(
        prompts["critique_image_opinion"],
        context,
        result_parser=str_parser,
    )

    for agent_name, critique in critiques.items():
        logger.info("critique from %s: %s", agent_name, critique)

    ratings = panel.sample(
        prompts["critique_image_binary"],
        context,
    )

    for agent_name, rating in ratings.items():
        logger.info("rating from %s: %s", agent_name, rating)

    return critiques, ratings


@task()
def image_critique_group_scale(critics, context):
    panel = Panel(list(critics.values()), name="critics")
    critiques = panel.sample(
        prompts["critique_image_opinion"],
        context,
        result_parser=str_parser,
    )

    for agent_name, critique in critiques.items():
        logger.info("critique from %s: %s", agent_name, critique)

    ratings = panel.sample(
        prompts["critique_image_scale"],
        context,
        result_parser=int_result,
    )

    valid_ratings = []
    for agent_name, rating in ratings.items():
        logger.info("rating from %s: %s", agent_name, rating)

        if 1 <= rating <= 5:
            valid_ratings.append(rating)

    return critiques, valid_ratings


def summarize(post_ratings, post_times, approved_posts, rejected_posts):
    average_post_rating = sum(post_ratings) / len(post_ratings) if post_ratings else 0
    average_post_time = sum(post_times) / len(post_times) if post_times else 0
    approval_rate = (
        approved_posts / (approved_posts + rejected_posts)
        if approved_posts + rejected_posts > 0
        else 0
    )
    logger.info(
        "approved posts: %s, rejected posts: %s, approval rate: %.2f",
        approved_posts,
        rejected_posts,
        approval_rate,
    )
    logger.info(
        "average rating: %.2f, average time per post: %.2f, average time per approved post: %.2f",
        average_post_rating,
        average_post_time,
        average_post_time / approval_rate if approval_rate > 0 else 0,
    )


@task()
def rate_post(critics, post_captions, post_path):
    critiques, ratings = image_critique_group_bool(critics, post_captions)

    # calculate the average rating
    rating_values = list(ratings.values())
    if len(rating_values) > 0:
        average_rating = sum(rating_values) / len(rating_values)
        logger.info("average rating: %s", average_rating)
    else:
        average_rating = 0
        logger.error("no ratings for post")

    # save rating and critique
    with open(path.join(post_path, "rating.json"), "w") as f:
        f.write(
            dumps(
                {
                    "average": average_rating,
                    "critiques": critiques,
                    "ratings": ratings,
                },
                indent=2,
            )
        )

    return average_rating


@task()
def generate_ideas(interests, interest_agents):
    ideas = {}
    for interest in interests:
        scientist = interest_agents[interest]
        logger.debug("running scientist for interest: %s", interest)
        idea = scientist(prompts["generate_ideas"])
        logger.info("%s scientist came up with an idea: %s", interest, idea)
        ideas[interest] = idea

    logger.debug("ideas: %s", ideas)
    return ideas


@task()
def generate_description(interests, social_media_manager, ideas):
    post_description = social_media_manager(
        prompts["generate_description"],
        ideas=format_bullet_list(ideas.values()),
    )
    logger.info("post description: %s", post_description)
    return post_description


def main(
    approval_threshold=0.65,  # TODO: move to data
    concept_count=20,  # TODO: move to data
    fixed_post_format=None,
    max_post_retry=3,
    min_image_count=3,  # TODO: move to data
    max_image_count=5,  # TODO: move to data
    min_interest_count=2,  # TODO: move to data
    max_interest_count=5,  # TODO: move to data
):
    post_ratings = []
    post_times = []
    approved_posts = 0
    rejected_posts = 0

    for _ in range(concept_count):
        if fixed_post_format is None:
            post_format = choice(post_formats)
        else:
            post_format = fixed_post_format

        interests = random_interest(randint(min_interest_count, max_interest_count))
        interest_agents = {interest: InterestAgent(interest) for interest in interests}

        with trace(post_format, "feedme.post") as (report_args, report_output):
            report_args(interests, post_format)

            concepts = generate_concepts(interest_agents)
            top_concepts = concept_ranking_each_scale(interest_agents, concepts)
            if len(top_concepts) == 0:
                logger.error("no top concepts found")
                continue

            theme = cleanup_sentence(top_concepts[0][0])
            input = {
                "interests": interests,
                "images": [],
                "theme": theme,
            }

            post_retry = 0
            while post_retry < max_post_retry:
                summarize(post_ratings, post_times, approved_posts, rejected_posts)

                with trace(str(post_retry), "feedme.post.retry") as (
                    report_args_retry,
                    report_output_retry,
                ):
                    try:
                        logger.info(
                            "processing input (retry %s): %s", post_retry, input
                        )
                        if path.exists(working_path):
                            logger.warning("removing existing post at %s", working_path)
                            rmtree(working_path)

                        make_post_paths()

                        # start timer
                        start_time = monotonic()

                        # extract parameters
                        modifier = choice(list(modifiers.values()))
                        count = randint(min_image_count, max_image_count)
                        interests = input["interests"]
                        theme = input["theme"]

                        # download images
                        images = input["images"]
                        if len(images) > 0:
                            download_input_images(images, working_path)

                            # load captions and sizes
                            image_data = get_image_data(working_path)
                            logger.info("loaded image captions: %s", image_data)
                        else:
                            image_data = []

                        # set up agents
                        agent_context = {
                            "count": count,
                            "modifier": modifier,
                            "post_format": post_format,
                            "theme": theme,
                        }

                        report_args_retry(**agent_context)

                        social_media_manager = Agent(
                            "social media manager",
                            agent_backstory["Social Media Manager"],
                            agent_context,
                            manager_llm,
                        )
                        art_critic = Agent(
                            "art critic",
                            agent_backstory["Art Critic"],
                            agent_context,
                            creative_llm,
                        )
                        interest_agents = {
                            interest: InterestAgent(interest, **agent_context)
                            for interest in interests
                        }

                        ideas = generate_ideas(interests, interest_agents)
                        post_description = generate_description(
                            interests, social_media_manager, ideas
                        )
                        post_description = cleanup_sentence(post_description)

                        # run the agents
                        # summarize the post
                        prompt_agent = choice(list(interest_agents.values()))
                        logger.info(
                            "using %s to generate post prompt", prompt_agent.name
                        )
                        post_keywords = generate_prompt(prompt_agent, post_description)
                        logger.info("post image prompt: %s", post_keywords)

                        # add images to the post or generate new ones
                        if len(image_data) > 0:
                            top_images = image_ranking_each_scale(
                                interests,
                                interest_agents,
                                image_data,
                                count,
                                post_description,
                            )
                        else:
                            image_size = image_size_choice(
                                interest_agents, post_description
                            )
                            logger.warning(
                                "generating %s %s images for post, prompt: %s",
                                count,
                                image_size,
                                post_keywords,
                            )
                            set_save_path(working_path)
                            top_images = [
                                (image, None)
                                for image in generate_image_tool(
                                    post_keywords, count, size=image_size
                                )
                            ]

                        # make sure there are enough images
                        if len(top_images) == 0:
                            logger.error(
                                "not enough images for post: %s < %s",
                                len(top_images),
                                count,
                            )
                            rejected_posts += 1
                            post_retry += 1
                            report_output_retry(
                                {"status": "failed", "reason": "not enough images"}
                            )
                            continue

                        # compile the post
                        post = {
                            "title": theme,
                            "description": post_description,
                            "files": [path.basename(image) for image, _ in top_images],
                            "keywords": post_keywords,
                        }
                        logger.info("post: %s", post)

                        # move post files to their own folder
                        post_hash = hash_post(post)
                        post_slug = sanitize_name(theme)[:50] + "_" + post_hash
                        post_path = path.join(approval_path, post_slug)
                        move(working_path, post_path)

                        # save the post data and ideas
                        with open(path.join(post_path, "post.json"), "w") as f:
                            f.write(dumps(post, indent=2))

                        with open(path.join(post_path, "ideas.json"), "w") as f:
                            f.write(dumps(ideas, indent=2))

                        # have the art critic and the scientists rate the post
                        critics = {
                            "art critic": art_critic,
                            **interest_agents,
                        }
                        average_rating = rate_post(critics, post, post_path)

                        # accumulate average rating and stop the timer
                        post_ratings.append(average_rating)
                        delta, _ = monotonic_delta(start_time)
                        post_times.append(delta)

                        # move the post to the approved or rejected folder
                        if average_rating < approval_threshold:
                            logger.error("rejecting post: %s", post_path)
                            move(post_path, rejected_path)
                            rejected_posts += 1
                            post_retry += 1
                            report_output_retry(
                                {
                                    "status": "failed",
                                    "reason": "low rating",
                                }
                            )
                            continue

                        logger.warning("approving post: %s", post_path)
                        move(post_path, approved_path)
                        approved_posts += 1

                        # post to Civitai or save to HTML
                        do_post(post_slug, post_description, post_hash, post)

                        logger.info("finished processing input: %s", input)
                        report_output_retry(
                            {
                                "status": "approved",
                                "post": post,
                                "rating": average_rating,
                            }
                        )
                        report_output(
                            {
                                "status": "approved",
                                "post": post,
                                "rating": average_rating,
                            }
                        )
                        break
                    except Exception as err:
                        logger.exception("failed to process input: %s", input)
                        report_output_retry(
                            {
                                "status": "failed",
                                "reason": str(err),
                                "error": type(err).__name__,
                            }
                        )

            report_output({"status": "failed", "reason": "max retries exceeded"})

    summarize(post_ratings, post_times, approved_posts, rejected_posts)


if __name__ == "__main__":
    main()
