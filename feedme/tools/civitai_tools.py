from os import environ
from re import sub
from typing import Any, Dict, List

from playwright.sync_api import expect, sync_playwright
from traceloop.sdk.decorators import tool


class BrowserSession:
    browser: Any = None
    context: Any = None
    page: Any = None
    playwright: Any = None

    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None


session = BrowserSession()


@tool()
def launch_login() -> str:
    """
    Launch the Civitai website and log in.
    """
    session.playwright = sync_playwright().start()
    session.browser = session.playwright.firefox.launch(headless=False)
    session.context = session.browser.new_context()
    session.context.add_cookies(
        [
            {
                "url": "https://.civitai.com/",
                "name": "__Secure-civitai-token",
                "value": environ["CIVITAI_SESSION"],
            }
        ]
    )
    session.page = session.context.new_page()
    session.page.goto("https://civitai.com/")
    return session.page.title()


@tool()
def close_page() -> str:
    """
    Close the browser and clean up the session.
    """
    session.page = None
    session.context = None
    session.browser.close()
    session.browser = None
    session.playwright.stop()
    session.playwright = None
    return "Browser closed."


@tool()
def create_post(
    images: List[str],
    mature: bool = False,
    title: str | None = None,
    description: str | None = None,
) -> str:
    """
    Create a new post on Civitai.

    Args:
        images: A list of images to upload.
        mature: A boolean indicating if the post should be marked as mature.
        title: The title of the post.
        description: The description of the post.
    """
    if session.page is None:
        launch_login()

    session.page.goto("https://civitai.com/posts/create")
    dropzone = session.page.locator("css=div.mantine-Dropzone-root")

    with session.page.expect_file_chooser() as fc_info:
        dropzone.click()

    file_chooser = fc_info.value
    file_chooser.set_files(images)

    session.page.wait_for_url("https://civitai.com/posts/*/edit")

    if mature:
        mature_flag = session.page.get_by_label("Mature")
        mature_flag.click()

    if title:
        title_input = session.page.get_by_placeholder("Add a title...")
        title_input.fill(title)

    if description:
        description_input = session.page.locator(
            "[data-placeholder='Add a description...']"
        )
        description_input.fill(description)

    expect(session.page.get_by_text("Saving"), "post should be saving").to_be_visible()
    expect(session.page.get_by_text("Saved"), "post should be saved").to_be_visible()

    post_url = session.page.url
    return sub(r"^https://civitai.com/posts/(\d+)/edit$", "\\1", post_url)


def login(email: str):
    session.page.goto("https://civitai.com/")

    sign_in = session.page.get_by_role("link", name="Sign In")
    if sign_in:
        sign_in.click()
    else:
        raise Exception("Sign In button not found")

    session.page.wait_for_url("https://civitai.com/login?returnUrl=/")
    session.page.get_by_label("Email").fill(email)


def get_posts() -> List[Dict[str, str]]:
    """
    Get a list of your previous posts on Civitai, with their ratings and comments.
    """
    return []
