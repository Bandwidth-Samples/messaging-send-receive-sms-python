import http
import os
import sys

import bandwidth
from bandwidth import ApiException
from fastapi import FastAPI, Response
from pydantic import BaseModel
from typing import List, Union
import uvicorn

try:
    BW_USERNAME = os.environ['BW_USERNAME']
    BW_PASSWORD = os.environ['BW_PASSWORD']
    BW_ACCOUNT_ID = os.environ['BW_ACCOUNT_ID']
    BW_MESSAGING_APPLICATION_ID = os.environ['BW_MESSAGING_APPLICATION_ID']
    BW_NUMBER = os.environ['BW_NUMBER']
    USER_NUMBER = os.environ['USER_NUMBER']
    LOCAL_PORT = int(os.environ['LOCAL_PORT'])
    BASE_CALLBACK_URL = os.environ['BASE_CALLBACK_URL']
except KeyError as e:
    print(f"Please set the environmental variables defined in the README\n\n{e}")
    sys.exit(1)
except ValueError as e:
    print(f"Please set the LOCAL_PORT environmental variable to an integer\n\n{e}")
    sys.exit(1)

app = FastAPI()

bandwidth_configuration = bandwidth.Configuration(
    username=BW_USERNAME,
    password=BW_PASSWORD
)

bandwidth_api_client = bandwidth.ApiClient(bandwidth_configuration)
bandwidth_messages_api_instance = bandwidth.MessagesApi(bandwidth_api_client)


class CreateMessageRequest(BaseModel):
    to: str
    text: str


@app.post('/messages', status_code=http.HTTPStatus.NO_CONTENT)
def send_message(data: CreateMessageRequest):
    create_message_request = bandwidth.models.MessageRequest(
        application_id=BW_MESSAGING_APPLICATION_ID,
        to=[data.to],
        var_from=BW_NUMBER,
        text=data.text,
        tag="Outbound Message"
    )

    try:
        bandwidth_messages_api_instance.create_message(BW_ACCOUNT_ID, create_message_request)
        return Response(content=None)
    except ApiException as e:
        print(f"Encountered and error while sending message: {e}")
        return Response(content=None, status_code=http.HTTPStatus.INTERNAL_SERVER_ERROR)


@app.post('/callbacks/outbound/messaging', status_code=http.HTTPStatus.NO_CONTENT)
def handle_outbound_message(
        data: Union[
            List[bandwidth.models.MessageSendingCallback],
            List[bandwidth.models.MessageDeliveredCallback],
            List[bandwidth.models.MessageFailedCallback]
        ]):
    match data[0].type:
        case "message-sending":
            print("message-sending type is only for MMS.")
        case "message-delivered":
            print("Your message has been handed off to the Bandwidth's MMSC network, but has not been confirmed at the downstream carrier.")
        case "message-failed":
            print(f"Your message has failed to be delivered to the downstream carrier. Error Code: {data[0].error_code}")
            print("For MMS and Group Messages, you will only receive this callback if you have enabled delivery receipts on MMS.")
        case _:
            print(f"Unexpected callback received: {data[0].type}")
            return Response(content=None, status_code=http.HTTPStatus.BAD_REQUEST)


@app.post('/callbacks/inbound/messaging', status_code=http.HTTPStatus.NO_CONTENT)
def handle_inbound(data: List[bandwidth.models.InboundMessageCallback]):
    if data[0].type != "message-received":
        print(f"Unexpected callback received: {data[0].type}")
        return Response(content=None, status_code=http.HTTPStatus.BAD_REQUEST)

    print(f"Received message from {data[0].message.from_} with text {data[0].message.text}")


if __name__ == '__main__':
    uvicorn.run('main:app', port=LOCAL_PORT, reload=True)
