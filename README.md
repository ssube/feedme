# FeedMe

Generate your own personalized social media feed at home! Decide what you want to see and how much, or just let it run
in a loop and see what happens. Consume meaningless content without waiting for other humans to produce it. The
algorithm is yours, this is your feed, and you decide what you want to see.

Enter a few topics or ideas, pick the right format, and make your own custom image feed complete with post titles,
descriptions, and even gallery web pages. Watch the adventerous agents explore the world and discover fascinating new
places, or make them all creepy relatives selling Tupperware and watch the disaster ensue.

## Requirements

Runs locally, no cloud services required (or recommended).

- Requires Python 3.10 or better.
- Compatible with Ollama and vLLM for text generation (and other OpenAI-compatible APIs).
- Compatible with ComfyUI and onnx-web for image generation.

VRAM requirements depend on the size of the images and the LLM you select.

- 0GB VRAM minimum, everything can run on CPU
- 32GB VRAM recommended for SDXL and Mistral (2x16GB GPUs works well).
- 64GB VRAM recommended for hires and Mixtral (1x24GB + 1x40GB, for example).
- 96GB VRAM recommended for Smaug and other Qwen 2-based models (1x16GB + 1x80GB, for example).

Smaller models like Mistral should produce a post every 3-5 minutes, depending on GPU performance and success rate of
the ensemble voting.

Running the bot with one GPU is possible, if it has enough memory to run both models, or one of the models has been
offloaded to CPU. With Mixtral and other mid-sized LLMs running on CPU, it should produce a post every 10-15 minutes.

## Running

Before launching the bot, browse through the `feedme/data` folder and modify the inputs as desired.

The topics and ideas used by the bot to generate posts are in the `agents.yaml` file, under the `interests` key. This
is a dictionary or map, with a keyword as key and the agent's specialty as the value. For example:

```yaml
interests:
    food: You are a talented chef who enjoys cooking at home and taking pictures of beautifully-prepared meals.
    garden: You are an avid gardener who loves growing plants and documenting their progress with photographs.
    landscape: You are a landscape photographer, traveling the world to capture exotic vistas.
```

For each post, one or more of the interests will be randomly selected and agents created to represent them. Each agent
is asked to come up with an idea, and after some debate between them, the best ideas will be turned into social media
posts. Each post will have a title, description, and some pictures attached.

### Docker

```shell
docker run \
    --rm \
    -it \
    -v ./data:/feedme/feedme/data:ro \
    -v /tmp/feedme-posts:/tmp/feedme-posts:rw \
    -e ROOT_PATH=/tmp/feedme-posts \
    -e COMFY_API="http://comfyui-server:8188" \
    -e LLM_API="http://ollama-server:11434" \
    -e ONNX_API="http://onnx-web-server:5000" \
    feedme
```

## Architecture

Agents:

- Social Media Manager
- Art Critic
- Scientists for each idea/topic

Architecture:

![an infographic showing the feedme architecture](./docs/architecture.png)
