from base64 import b64encode
from hashlib import sha256
from json import dumps, loads
from logging import getLogger
from re import sub
from time import monotonic

logger = getLogger(__name__)


def sanitize_name(name: str) -> str:
    """
    Replace all non-alphanumeric characters with underscores, then remove repeated underscores.
    """

    name = sub(r"\W", "_", name)
    name = sub(r"_+", "_", name)
    return name


def str_parser(result, **kwargs):
    return str(result)


def get_filename(item):
    if isinstance(item, (list, str)):
        return item
    elif isinstance(item, dict):
        possible_subkeys = [
            "filename",
            "ranks",
            "images",
            "image_filenames",
            "image_ranking",
            "ranked_filenames",
            "sorted_images",
            "sorted_filenames",
            "imagesSorted",
            "updatedImages",
        ]

        # if the root value is a dict with a single subkey, assume that's the ranking
        if len(item) == 1:
            item = list(item.values())[0]

        for subkey in possible_subkeys:
            # this needs to check for dict-ness every time, because the item might be a list nested in a dict
            if isinstance(item, dict) and subkey in item:
                item = item[subkey]

        return item
    else:
        return None


def parse_ranking(ranking: str) -> list[str]:
    # collapse lines
    ranking = ranking.replace("\n", "").replace("\r", "")

    ranking = sub(
        r"<\/\|.*$", "", ranking
    )  # sometimes the system prompt leaks into the output, like <|assistant|>
    ranking = sub(
        r"^[\s\w\.,:]+ \[", "", ranking
    )  # sometimes the output will have a leading comment, like "This is the list: []"
    ranking = ranking.replace('""', '"')  # the robots will double some JSON quotes

    # if they forgot to close the array, fix that
    if ranking.endswith('"}'):
        ranking = ranking + "]"

    # if they forgot to open the array and left it out entirely, fix that
    if ranking.startswith('{"'):
        ranking = "[" + ranking

    # file extension fixups
    ranking = ranking.replace(".0.png", ".png")
    ranking = ranking.replace(" .png", ".png")
    ranking = ranking.replace("..png", ".png")
    ranking = ranking.replace(". png", ".png")

    # remove leading/trailing whitespace
    ranking = ranking.strip()

    logger.info("ranking after fixups: %s", ranking)
    ranking = loads(ranking)
    logger.debug("ranking were valid JSON: %s", ranking)

    # attempt to extract the ranking from a list of strings, which may be nested in a dict, or many dicts
    ranking = get_filename(ranking)
    if isinstance(ranking, list):
        return [get_filename(item) for item in ranking]

    raise ValueError("Invalid ranking format")


def format_bullet_list(items: list[str]) -> str:
    """
    TODO: replace with packit formatting
    """
    # remove newlines within each item
    items = [item.replace("\n", " ").replace("\r", "") for item in items]
    return "\n".join(f"- {item}" for item in items)


def rank_list(ranking: list[str], max_rank=3):
    score = {}
    for i, image in enumerate(ranking):
        score[image] = max(max_rank - i, 1)

    return score


def hash_post(post: dict):
    return b64encode(
        sha256(dumps(post, sort_keys=True).encode("utf-8")).digest(),
        altchars=b"-_",
    ).decode("utf-8")


def monotonic_delta(start: float) -> tuple[float, float]:
    last = monotonic()
    return (last - start, last)
