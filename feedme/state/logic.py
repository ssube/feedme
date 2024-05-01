from logging import getLogger
from random import random
from typing import Dict, List, Optional

from feedme.models.base import dataclass
from feedme.state.utils import PostDict, StateDict

logger = getLogger(__name__)


@dataclass
class LogicModel:
    match: Dict[str, str]
    chance: float = 1.0
    remove: Optional[List[str]] = None
    set: Optional[Dict[str, str]] = None


@dataclass
class LogicFile:
    logic: List[LogicModel]


def make_logic_middleware(dataset: LogicFile):
    logger.warning(dataset)

    def update(status: str, post: PostDict, state: StateDict) -> StateDict:
        for logic in dataset.logic:
            if logic.match.items() <= state.items():
                logger.info("matched logic: %s", logic.match)
                if logic.chance < 1:
                    if random() > logic.chance:
                        logger.info("logic skipped by chance: %s", logic.chance)
                        continue

                if logic.set:
                    state.update(logic.set)
                    logger.info("logic set state: %s", logic.set)

                for key in logic.remove or []:
                    state.pop(key, None)

        return state

    return update
