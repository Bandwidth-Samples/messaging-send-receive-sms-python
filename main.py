import http
import os
import sys
from typing import List, Optional

import bandwidth
from fastapi import FastAPI, Response
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, StrictStr
import uvicorn

try:
    BW_ACCOUNT_ID = os.environ['BW_ACCOUNT_ID']
    BW_CLIENT_ID = os.environ['BW_CLIENT_ID']
    BW_CLIENT_SECRET = os.environ['BW_CLIENT_SECRET']
    BW_MESSAGING_APPLICATION_ID = os.environ['BW_MESSAGING_APPLICATION_ID']
    BW_NUMBER = os.environ['BW_NUMBER']
    LOCAL_PORT = int(os.environ['LOCAL_PORT'])
except KeyError as e:
    print(f"Please set the environmental variables defined in the README\n\n{e}")
    sys.exit(1)
except ValueError as e:
    print(f"Please set the LOCAL_PORT environmental variable to an integer\n\n{e}")
    sys.exit(1)

app = FastAPI()

bandwidth_configuration = bandwidth.Configuration(
    client_id=BW_CLIENT_ID,
    client_secret=BW_CLIENT_SECRET
)

bandwidth_api_client = bandwidth.ApiClient(bandwidth_configuration)
bandwidth_messages_api_instance = bandwidth.MessagesApi(bandwidth_api_client)
bandwidth_media_api_instance = bandwidth.MediaApi(bandwidth_api_client)

STATUS_MESSAGES = {
    "message-sending": "message-sending type is only for MMS.",
    "message-delivered": "Your message has been handed off to the Bandwidth's MMSC network, but has not been confirmed at the downstream carrier.",
    "message-failed": "For MMS and Group Messages, you will only receive this callback if you have enabled delivery receipts on MMS.",
}


class SendMessageRequest(BaseModel):
    to: StrictStr
    text: StrictStr
    media: Optional[List[StrictStr]] = None


@app.exception_handler(RequestValidationError)
def invalid_request(request, exc):
    return Response(status_code=http.HTTPStatus.BAD_REQUEST)


def save_media(media_url: str):
    media_id = media_url.partition("media/")[2]
    media_name = os.path.basename(media_id)
    if media_name.endswith(".xml"):
        return

    try:
        media = bandwidth_media_api_instance.get_media(BW_ACCOUNT_ID, media_id)
        os.makedirs("media", exist_ok=True)
        with open(os.path.join("media", media_name), "wb") as f:
            f.write(media)
        print(f"Saved media to media/{media_name}")
    except Exception as e:
        print(f"Failed to download {media_url}: {e}")


@app.post("/messages", status_code=http.HTTPStatus.NO_CONTENT)
def send_message(send_message_request: SendMessageRequest):
    message_request = bandwidth.models.MessageRequest(
        application_id=BW_MESSAGING_APPLICATION_ID,
        to=[send_message_request.to],
        var_from=BW_NUMBER,
        text=send_message_request.text,
        media=send_message_request.media or None
    )

    try:
        message = bandwidth_messages_api_instance.create_message(BW_ACCOUNT_ID, message_request)
        print(f"Sent message {message.id}")
    except Exception as e:
        print(f"Failed to send message: {e}")
        return Response(status_code=http.HTTPStatus.INTERNAL_SERVER_ERROR)

    return Response(status_code=http.HTTPStatus.NO_CONTENT)


@app.post("/callbacks/outbound/messaging/status", status_code=http.HTTPStatus.NO_CONTENT)
def status_callback(callbacks: List[bandwidth.models.StatusCallback]):
    if not all(callback.type.value in STATUS_MESSAGES for callback in callbacks):
        return Response(status_code=http.HTTPStatus.BAD_REQUEST)

    for callback in callbacks:
        print(STATUS_MESSAGES[callback.type.value])

    return Response(status_code=http.HTTPStatus.NO_CONTENT)


@app.post("/callbacks/inbound/messaging", status_code=http.HTTPStatus.NO_CONTENT)
def inbound_callback(callbacks: List[bandwidth.models.InboundCallback]):
    if not all(callback.type.value == "message-received" for callback in callbacks):
        return Response(status_code=http.HTTPStatus.BAD_REQUEST)

    for callback in callbacks:
        message = callback.message
        print(f"{callback.description}\nTo: {message.to[0]}\nFrom: {message.var_from}\nText: {message.text}")
        for media_url in message.media or []:
            save_media(media_url)

    return Response(status_code=http.HTTPStatus.NO_CONTENT)


if __name__ == "__main__":
    uvicorn.run("main:app", port=LOCAL_PORT, reload=True)
