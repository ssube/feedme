# This is an example that uses the websockets api to know when a prompt execution is done
# Once the prompt execution is done it downloads the images using the /history endpoint

import io
import json
import urllib.parse
import urllib.request
import uuid
from logging import getLogger
from os import environ, path
from random import choice, randint
from typing import List

import websocket  # NOTE: websocket-client (https://github.com/websocket-client/websocket-client)
from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image
from traceloop.sdk.decorators import tool

from feedme.data import data_base, get_save_path, misc, prompts
from feedme.tools.onnx_tools import generate_batches, generate_cfg, generate_steps

logger = getLogger(__name__)

server_address = environ["COMFY_API"]
client_id = str(uuid.uuid4())


def queue_prompt(prompt):
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode("utf-8")
    req = urllib.request.Request("http://{}/prompt".format(server_address), data=data)
    return json.loads(urllib.request.urlopen(req).read())


def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen(
        "http://{}/view?{}".format(server_address, url_values)
    ) as response:
        return response.read()


def get_history(prompt_id):
    with urllib.request.urlopen(
        "http://{}/history/{}".format(server_address, prompt_id)
    ) as response:
        return json.loads(response.read())


def get_images(ws, prompt):
    prompt_id = queue_prompt(prompt)["prompt_id"]
    output_images = {}
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message["type"] == "executing":
                data = message["data"]
                if data["node"] is None and data["prompt_id"] == prompt_id:
                    break  # Execution is done
        else:
            continue  # previews are binary data

    history = get_history(prompt_id)[prompt_id]
    for o in history["outputs"]:
        for node_id in history["outputs"]:
            node_output = history["outputs"][node_id]
            if "images" in node_output:
                images_output = []
                for image in node_output["images"]:
                    image_data = get_image(
                        image["filename"], image["subfolder"], image["type"]
                    )
                    images_output.append(image_data)
            output_images[node_id] = images_output

    return output_images


@tool(name="generate_image")
def generate_image_tool(prompt, count, size="landscape"):
    output_paths = []
    for i, count in enumerate(generate_batches(count + misc.images.extra)):
        results = generate_images(prompt, count, size, prefix=f"output-{i}")
        output_paths.extend(results)

    return output_paths


def generate_images(
    prompt: str, count: int, size="landscape", prefix="output"
) -> List[str]:
    cfg = generate_cfg()
    height, width = misc.sizes.get(size, (512, 512))
    steps = generate_steps(min_steps=int(misc.images.steps.min + cfg))
    seed = randint(0, 10000000)
    checkpoint = choice(misc.checkpoints)
    logger.info(
        "generating %s images at %s by %s with prompt: %s", count, height, width, prompt
    )

    env = Environment(
        loader=FileSystemLoader(data_base, "feedme/templates"),
        autoescape=select_autoescape(["json"]),
    )
    template = env.get_template("comfy.json.j2")
    result = template.render(
        cfg=cfg,
        height=height,
        width=width,
        steps=steps,
        seed=seed,
        checkpoint=checkpoint,
        prompt=prompt,
        negative_prompt=prompts.negative_prompt,
        count=count,
        prefix=misc.bot.name,
    )

    # parsing here helps ensure the template emits valid JSON
    logger.debug("template workflow: %s", result)
    prompt_workflow = json.loads(result)

    logger.debug("Connecting to Comfy API at %s", server_address)
    ws = websocket.WebSocket()
    ws.connect("ws://{}/ws?clientId={}".format(server_address, client_id))
    images = get_images(ws, prompt_workflow)

    results = []
    for node_id in images:
        for image_data in images[node_id]:
            image = Image.open(io.BytesIO(image_data))
            results.append(image)

    paths: List[str] = []
    for j, image in enumerate(results):
        image_path = path.join(get_save_path(), f"{prefix}-{j}.png")
        with open(image_path, "wb") as f:
            image_bytes = io.BytesIO()
            image.save(image_bytes, format="PNG")
            f.write(image_bytes.getvalue())

        paths.append(image_path)

    return paths


if __name__ == "__main__":
    paths = generate_images(
        "A painting of a beautiful sunset over a calm lake", 3, "landscape"
    )
    logger.info("Generated %d images: %s", len(paths), paths)
