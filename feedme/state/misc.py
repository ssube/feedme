from typing import List

from feedme.state.utils import PostDict, StateDict


def make_compound_middlewares(*middlewares):
    def update(status: str, post: PostDict, state: StateDict) -> StateDict:
        for middleware in middlewares:
            state = middleware(status, post, state)

        return state

    return update


def make_status_middleware(statuses: List[str], middleware):
    def update(status: str, post: PostDict, state: StateDict) -> StateDict:
        if status in statuses:
            state = middleware(status, post, state)

        return state

    return update
