from logging import getLogger
from typing import Dict, List, Tuple

from pgmpy.models import MarkovChain

from feedme.utils.state import PostDict, StateDict

logger = getLogger(__name__)


def get_state_keys(dataset) -> Tuple[List[str], Dict[str, List[str]]]:
    names = list(dataset.keys())
    keys = {key: list(value.keys()) for key, value in dataset.items()}

    return names, keys


def make_state_chain(dataset) -> MarkovChain:
    names = list(dataset.keys())
    cardinality = [len(value) for value in dataset.values()]

    chain = MarkovChain(names, cardinality)

    for name in names:
        chain.add_transition_model(name, generate_transitions(dataset[name]))

    return chain


def generate_transitions(
    dataset: Dict[str, Dict[str, float]], wildcard: str = "*"
) -> Dict[int, Dict[int, float]]:
    """
    Given a dictionary of names to relative weights, normalize that into a dictionary of indices to normalized weights.
    """

    keys = list(dataset.keys())

    transitions = {}
    for name, edges in dataset.items():
        edge_weights = {}
        total_weight = 0
        for link, weight in edges.items():
            if link == wildcard:
                continue

            edge_weights[keys.index(link)] = weight
            total_weight += weight

        # add any remaining edges using the wildcard weight
        if "*" in edges:
            for i, key in enumerate(keys):
                if i not in edge_weights:
                    edge_weights[i] = edges[wildcard]
                    total_weight += edges[wildcard]

        # normalize the weights
        for key in edge_weights:
            edge_weights[key] /= total_weight

        transitions[keys.index(name)] = edge_weights

    return transitions


def make_markov_middleware(state_data):
    state_chain = make_state_chain(state_data)
    state_vars, state_keys = get_state_keys(state_data)

    def update(status: str, post: PostDict, state: StateDict) -> StateDict:
        if status in ["approved", "init"]:
            if len(state) > 0:
                logger.info("updating state with status %s", state)
                states = []
                for key, value in state.items():
                    states.append((key, state_keys[key].index(value)))

                state_chain.set_start_state(states)

            for sample in state_chain.generate_sample(size=1):
                for key, value in zip(state_vars, sample):
                    value_name = state_keys[key][value.state]
                    logger.info(
                        "changing %s from %s to %s",
                        key,
                        state.get(key, None),
                        value_name,
                    )
                    state[key] = value_name

        return state

    return update
