import os
import json

# ***************needs to be changed when sdk becomes python package
import sys
sys.path.insert(0, 'C:/Users/ckoegel/Documents/sdks/python-v1')
import openapi_client
from openapi_client.api.messages_api import MessagesApi
from openapi_client.model.message_request import MessageRequest
from openapi_client.model.bandwidth_callback_message import BandwidthCallbackMessage
# ---------------------------------------------------

from fastapi import FastAPI, Request
from pydantic import BaseModel


BW_NUMBER = os.environ.get('BW_NUMBER')
BW_USERNAME = os.environ.get('BW_USERNAME')
BW_PASSWORD = os.environ.get('BW_PASSWORD')
BW_ACCOUNT_ID = os.environ.get('BW_ACCOUNT_ID')
BW_MESSAGING_APPLICATION_ID = os.environ.get('BW_MESSAGING_APPLICATION_ID')


class CreateBody(BaseModel):    # model for the received json body to create a message
    to: str
    text: str


configuration = openapi_client.Configuration(     # needs to be updated*********  # Configure HTTP basic authorization: httpBasic
    username=BW_USERNAME,
    password=BW_PASSWORD
)


api_client = openapi_client.ApiClient(configuration)  # needs to be updated*********
messages_api_instance = MessagesApi(api_client) # needs to be updated*********


app = FastAPI()


@app.post('/sendMessage')
def send_message(create_body: CreateBody):
    message_body = MessageRequest(  # needs to be updated*********
        to=[create_body.to],
        _from=BW_NUMBER,
        application_id=BW_MESSAGING_APPLICATION_ID,
        text=create_body.text
    )
    response = messages_api_instance.create_message(    # needs to be updated*********
        account_id=BW_ACCOUNT_ID,
        message_request=message_body,
        _return_http_data_only=False
    )

    return response[1]


@app.post('/callbacks/outbound/messaging/status')
async def handle_outbound_status(request: Request):
    status_body_array = await request.json()
    status_body = status_body_array[0]
    if status_body['type'] == "message-sending":
        print("message-sending type is only for MMS.")
    elif status_body['type'] == "message-delivered":
        print("Your message has been handed off to the Bandwidth's MMSC network, but has not been confirmed at the downstream carrier.")
    elif status_body['type'] == "message-failed":
        print("For MMS and Group Messages, you will only receive this callback if you have enabled delivery receipts on MMS.")
    else:
        print("Message type does not match endpoint. This endpoint is used for message status callbacks only.")

    return 200


@app.post('/callbacks/inbound/messaging')
async def handle_inbound(request: Request):
    inbound_body_array = await request.json()
    inbound_body = BandwidthCallbackMessage._new_from_openapi_data(inbound_body_array[0])
    print(inbound_body.description)
    if inbound_body.type == "message-received":
        print("To: {}\nFrom: {}\nText: {}".format(inbound_body.message.to[0], inbound_body.message._from,
                                                  inbound_body.message.text))
    else:
        print("Message type does not match endpoint. This endpoint is used for inbound messages only.\nOutbound message status callbacks should be sent to /callbacks/outbound/messaging/status.")

    return 200


if __name__ == '__main__':
    app.run(host='0.0.0.0')
