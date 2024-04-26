from datetime import datetime
from json import dumps, load
from os import listdir, path
from queue import Queue
from threading import Thread
from time import strftime

from flask import Flask, jsonify, request, send_file
from packit.tracing import set_tracer
from packit.tracing.traceloop import dumper

from feedme.data import get_bot_name
from feedme.index_page import list_posts, template_page
from feedme.multi_post import main, root_path
from feedme.progress_tracer import make_tracer

CREATE_TEMPLATE = "create.html.j2"
INDEX_TEMPLATE = "index.html.j2"
POST_TEMPLATE = "default.html.j2"


post_path = path.join(root_path, "approved")


app = Flask(get_bot_name())


@app.route("/", methods=["GET"])
def posts():
    posts = list_posts(post_path)
    return template_page(get_bot_name(), posts, INDEX_TEMPLATE)


@app.route("/create", methods=["GET"])
def create():
    return template_page(get_bot_name(), {}, CREATE_TEMPLATE)


@app.route("/<string:post_id>", methods=["GET"])
def post_get(post_id):
    post_file = path.join(post_path, post_id, "post.json")
    if not path.isfile(post_file):
        return jsonify({"error": "Post not found"}), 404

    with open(post_file, "r") as f:
        post_data = load(f)

    mtime = path.getmtime(path.join(post_path, post_id))
    timestamp = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")

    title = post_data.get("title", post_id)
    images = listdir(path.join(post_path, post_id))
    images = [
        f
        for f in images
        if path.isfile(path.join(post_path, post_id, f)) and f.endswith(".png")
    ]
    post = {
        "folder": post_id,
        "title": title,
        "images": images,
        "timestamp": timestamp,
    }

    return template_page(title, post)


@app.route("/<string:post_id>/<path:subpath>", methods=["GET"])
def post_html(post_id, subpath):
    post_file = path.join(post_path, post_id, subpath)
    if not path.isfile(post_file):
        return jsonify({"error": "Post not found"}), 404

    if subpath.endswith(".png"):
        return send_file(post_file)

    with open(post_file, "r") as f:
        content = f.read()

    return content


@app.route("/post", methods=["POST"])
def post_create():
    data = request.json
    print(data)

    interests = data["interests"]
    max_interests = min(len(interests), 5)

    # set up the progress tracer
    progress = Queue()

    def callback(**kwargs):
        print(kwargs)
        progress.put(kwargs)

    def generate():
        while True:
            try:
                update = progress.get()
                yield dumps(update, default=dumper) + "\n\n"
                if "done" in update and update["done"]:
                    break
            except Exception as err:
                print(err)
                break

    def run():
        tracer = make_tracer(callback)
        set_tracer(tracer)

        posts = main(
            interests=interests, concept_count=1, max_interest_count=max_interests
        )
        print(posts)

        callback(done=True, result=posts)

    thread = Thread(target=run)
    thread.start()

    return app.response_class(generate(), mimetype="text/plain")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/default.css", methods=["GET"])
def css():
    return send_file("feedme/templates/default.css")


@app.after_request
def after_request(response):
    timestamp = strftime("[%Y-%b-%d %H:%M]")
    print(
        timestamp,
        request.remote_addr,
        request.method,
        request.scheme,
        request.full_path,
        response.status,
    )
    return response


if __name__ == "__main__":
    print("Please run this server using `waitress-serve`")
    print("Example: `waitress-serve --call 'feedme.server:app'`")
    app.run()
