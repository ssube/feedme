from os import environ, path

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
