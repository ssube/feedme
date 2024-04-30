from importlib import import_module
from json import dump, load
from logging import getLogger
from os import environ, path
from typing import Any, Dict

from feedme.data import get_save_path

logger = getLogger(__name__)

PostDict = Dict[str, Any]  # TODO: replace with a proper Post model
StateDict = Dict[str, str]

# make sure this is always saved to the root path, not within each post
# TODO: save a copy with each post for easy reference
state_path = path.join(get_save_path(), "state.json")


def load_middlewares():
    middlewares = []
    for middleware in environ.get("FEEDME_MIDDLEWARES", "").split(","):
        if not middleware:
            continue

        module_name, func_name = middleware.rsplit(":", 1)
        module = import_module(module_name)
        func = getattr(module, func_name)
        middlewares.append(func)

    return middlewares


def load_state() -> StateDict:
    if not path.exists(state_path):
        # run middleware to initialize a new state
        middlewares = load_middlewares()
        logger.debug(
            "generating new state using middlewares: %s",
            [m.__name__ for m in middlewares],
        )

        state = {}
        for middleware in middlewares:
            try:
                state = middleware("init", {}, state)
            except Exception:
                logger.exception("middleware %s failed", middleware.__name__)

        logger.info("initial state: %s", state)
        return state

    with open(state_path) as f:
        state = load(f)
        logger.info("loaded state: %s", state)
        return state


def save_state(state: StateDict) -> None:
    with open(state_path, "w") as f:
        logger.debug("saving state: %s", state)
        dump(state, f)


def update_state(status: str, post: PostDict, state: StateDict) -> StateDict:
    middlewares = load_middlewares()
    logger.debug(
        "updating state using middlewares: %s", [m.__name__ for m in middlewares]
    )

    for middleware in middlewares:
        try:
            state = middleware(status, post, state)
        except Exception:
            logger.exception("middleware %s failed", middleware.__name__)

    return state
