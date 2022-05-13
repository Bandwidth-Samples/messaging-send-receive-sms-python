import os

import uvicorn
from fastapi import FastAPI, Request
from pydantic import BaseModel
from bandwidth.bandwidth_client import BandwidthClient
from bandwidth.messaging.models.message_request import MessageRequest

BW_USERNAME = os.environ.get('BW_USERNAME')
BW_PASSWORD = os.environ.get('BW_PASSWORD')
BW_NUMBER = os.environ.get('BW_NUMBER')
BW_ACCOUNT_ID = os.environ.get('BW_ACCOUNT_ID')
BW_MESSAGING_APPLICATION_ID = os.environ.get('BW_MESSAGING_APPLICATION_ID')


bandwidth_client = BandwidthClient(
    messaging_basic_auth_user_name=BW_USERNAME,
    messaging_basic_auth_password=BW_PASSWORD
)
messaging_client = bandwidth_client.messaging_client.client

account_id = BW_ACCOUNT_ID


class CreateBody(BaseModel):
    to: str
    text: str


class InboundBody(BaseModel):
    type: str
    description: str
    message: dict


app = FastAPI()


@app.post('/callbacks/outbound/messaging')
def handle_outbound_message(create_body: CreateBody):
    body = MessageRequest()
    body.application_id = BW_MESSAGING_APPLICATION_ID
    body.to = [create_body.to]
    body.mfrom = BW_NUMBER
    body.text = create_body.text

    create_response = messaging_client.create_message(account_id, body=body)

    return create_response.status_code


@app.post('/callbacks/outbound/messaging/status')
async def handle_outbound_status(request: Request):
    status_body_array = await request.json()
    status_body = status_body_array[0]
    if status_body['type'] == "message-sending":
        print("message-sending type is only for MMS")
    elif status_body['type'] == "message-delivered":
        print("your message has been handed off to the Bandwidth's MMSC network, but has not been confirmed at the downstream carrier")
    elif status_body['type'] == "message-failed":
        print("For MMS and Group Messages, you will only receive this callback if you have enabled delivery receipts on MMS.")
    else:
        print("Message type does not match endpoint. This endpoint is used for message status callbacks only.")

    return 200


@app.post('/callbacks/inbound/messaging')
async def handle_inbound(request: Request):
    inbound_body_array = await request.json()
    inbound_body = inbound_body_array[0]
    print(inbound_body['description'])
    if inbound_body['type'] == "message-received":
        print("From: {}\nTo: {}\nText: {}".format(inbound_body['message']['from'], inbound_body['message']['to'][0],
                                                  inbound_body['message']['text']))
    else:
        print("Message type does not match endpoint. This endpoint is used for inbound messages only.\nOutbound message callbacks should be sent to /callbacks/outbound/messaging.")

    return 200


if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=5000, reload=True, root_path="/")
