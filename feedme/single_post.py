from packit.agent import Agent, agent_easy_connect
from packit.prompts import get_function_example, get_random_prompt
from packit.results import markdown_result, multi_function_result
from packit.tools import Toolbox
from packit.utils import logger_with_colors

from feedme.data import prompts
from feedme.tools.civitai_tools import close_page, create_post, get_posts, launch_login

logger = logger_with_colors(__name__)

# Set up a programming expert
llm = agent_easy_connect(model="knoopx/hermes-2-pro-mistral:7b-q8_0", temperature=0.05)
programmer = Agent(
    "tech",
    "You are a brilliant technical support analyst with a talent for breaking down complex tasks and solving them using JSON function calling.",
    {},
    llm,
)

# Prepare a toolbox
toolbox = Toolbox(
    [
        launch_login,
        close_page,
        create_post,
        get_posts,
    ]
)

# Come up with a title and description
result = programmer(prompts.demo_idea)
print("Result: ", result)

title, *description = [line for line in result.split("\n") if len(line.strip()) > 0]
description = "\n".join(description)

# Have them create a post using the civitai tools
result = programmer(
    prompts.demo_post + get_random_prompt("function"),
    description=description,
    example=get_function_example(),
    images=["/home/ssube/Pictures/Screenshot_2024-03-25_13-38-49.png"],
    title=title,
    tools=toolbox.definitions,
)
print("Result: ", result)

if "```" in result:
    # Extract the code blocks
    code_blocks = markdown_result(result)
    result = "\n\n".join(code_blocks)

result = multi_function_result(result, toolbox.callbacks)
print(result)
