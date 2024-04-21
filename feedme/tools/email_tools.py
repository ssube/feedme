from os import environ
from urllib.parse import quote_plus

from nylas import Client

client = None
grant = None


def connect():
    global client
    global grant

    client = Client(
        environ["NYLAS_API_KEY"],
        environ["NYLAS_API_URI"],
    )
    grant = environ["NYLAS_GRANT_ID"]


def check_email(limit=5, query="from:login@civitai.com"):
    messages = client.messages.list(
        grant,
        query_params={
            "limit": limit,
            "search_query_native": quote_plus(query),
        },
    )

    return [message.body for message in messages.data]
