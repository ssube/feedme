from io import BytesIO
from json import dumps
from logging import getLogger
from os import environ, path
from random import choice, randint
from time import sleep
from typing import List, Literal
from urllib.request import urlretrieve

import requests
from packit.tracing import trace
from PIL import Image
from traceloop.sdk.decorators import tool

from feedme.data import get_save_path, misc, prompts

logger = getLogger(__name__)

ImageSize = Literal["landscape", "portrait", "square"]

onnx_root = environ.get("ONNX_API", None)


@tool(name="generate_image")
def generate_image_tool(prompt: str, count: int, size: ImageSize = "landscape") -> str:
    output_paths = []
    for i in range(count + int(misc.images.extra)):
        results = generate_images(prompt, int(misc.images.batch), size)
        if isinstance(results, str):
            output_paths.append(results)

        for j, image in enumerate(results):
            if isinstance(image, str):
                output_paths.append(image)
                continue

            image_path = f"{get_save_path()}/output-{i}-{j}.png"
            logger.info("saving image %s to: %s", i, image_path)
            image.save(image_path)
            output_paths.append(image_path)

    return output_paths


def generate_images(
    prompt: str, count: int, size: ImageSize = "landscape"
) -> List[Image.Image]:
    dims = misc.sizes.get(size)
    with trace("generate_images", "feedme.onnx") as (report_args, report_result):
        report_args(prompt=prompt, count=count, size=size)
        job = generate_txt2img(onnx_root, prompt, count, *dims)
        if job is None:
            report_result({"status": "error", "reason": "could not get job name"})
            return ["Error generating images: could not get job name."]

        ready = False
        for _ in range(int(misc.onnx.retries)):
            if check_ready(onnx_root, job):
                logger.debug("image is ready: %s", job)
                ready = True
                break
            else:
                logger.debug("waiting for image to be ready")
                sleep(int(misc.onnx.poll))

        if not ready:
            report_result({"status": "error", "reason": "image not ready in time"})
            return ["Error generating images: image not ready in time."]

        results = download_images(onnx_root, job)
        if results is None or len(results) == 0:
            report_result({"status": "error", "reason": "could not download images"})
            return ["Error generating images: could not download images."]

        return results


def generate_steps(min_steps: int = 25, max_steps: int = 40) -> int:
    return randint(min_steps // 5, max_steps // 5) * 5


def generate_cfg() -> float:
    return randint(3, 8)


def generate_txt2img(
    host: str, prompt: str, count: int, height: int, width: int
) -> str:
    cfg = generate_cfg()
    steps = generate_steps(min_steps=25 + cfg)
    image_parameters = {
        "device": {
            "platform": "cuda",
        },
        "params": {
            "batch": count,
            "cfg": cfg,
            "steps": steps,
            "prompt": prompt,
            "negativePrompt": prompts.negative_prompt,
            "width": width,
            "height": height,
            "pipeline": "txt2img-sdxl",
            "model": choice(misc.checkpoints),  # TODO: make this smarter, ask an agent
            "tiled_vae": False,
            "unet_overlap": 0.25,
            "unet_tile": 1280,
            "vae_overlap": 0.25,
            "vae_tile": 512,
            "scheduler": "dpm-sde",
            "seed": -1,
        },
        "experimental": {
            "latentSymmetry": {
                "enabled": False,
                "gradientStart": 0,
                "gradientEnd": 0,
                "lineOfSymmetry": 0,
            },
            "promptEditing": {
                "enabled": True,
                "addSuffix": "",
                "minLength": 240,
                "promptFilter": misc.onnx.filter,
                "removeTokens": misc.onnx.remove,
            },
        },
    }

    body = {
        "json": (None, dumps(image_parameters)),
    }

    resp = requests.post(f"{host}/api/txt2img", files=body)
    if resp.status_code == 200:
        json = resp.json()
        return json.get("name")

    raise ValueError(f"error generating images, status code: {resp.status_code}")


def check_ready(host: str, key: str) -> bool:
    resp = requests.get(f"{host}/api/ready?output={key}")
    if resp.status_code == 200:
        json = resp.json()
        ready = json.get("ready", False)
        if ready:
            cancelled = json.get("cancelled", False)
            failed = json.get("failed", False)
            return not cancelled and not failed
        else:
            return False
    else:
        logger.warning("ready request failed: %s", resp.status_code)
        raise ValueError("error getting image status")


def check_outputs(host: str, key: str) -> List[str]:
    resp = requests.get(f"{host}/api/job/status?jobs={key}")
    if resp.status_code == 200:
        json = resp.json()
        outputs = json[0].get("outputs", [])
        return outputs

    logger.warning("getting outputs failed: %s: %s", resp.status_code, resp.text)
    raise ValueError("error getting image outputs")


def download_images(host: str, key: str) -> List[Image.Image]:
    outputs = check_outputs(host, key)

    images = []
    for key in outputs:
        url = f"{host}/output/{key}"
        resp = requests.get(url)
        if resp.status_code == 200:
            logger.debug("downloading image: %s", key)
            images.append(Image.open(BytesIO(resp.content)))
        else:
            logger.warning("download request failed: %s: %s", url, resp.status_code)
            raise ValueError("error downloading image")

    return images


def download_input_images(images: list[str], dest: str):
    for i, image in enumerate(images):
        logger.info("downloading image: %s", image)
        # get image and json metadata
        urlretrieve(
            onnx_root + "/output/" + image + ".png", path.join(dest, f"{i}.png")
        )
        urlretrieve(
            onnx_root + "/output/" + image + ".png.json",
            path.join(dest, f"{i}.png.json"),
        )
