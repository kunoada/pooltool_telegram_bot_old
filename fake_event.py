import json
import pprint
import boto3
from os import environ

pool = 'b7c2e25db0e0d05d2a2e9633627b22329f5499684c4948bd57121476916b2442'
currentHash = ''
currentHeight = ''
nbe = ''
nb = ''


environ["AWS_PROFILE"] = "bot_iam"
client = boto3.client('sts')
session = boto3.Session(profile_name='bot_iam')
sqs = boto3.client('sqs')


def awsbroadcast(message):
    queue_url = 'https://sqs.us-west-2.amazonaws.com/637019325511/pooltoolevents.fifo'
    pprint.pprint(message)
    # Send message to SQS queue
    response = sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=(
            json.dumps(message)
        ),
        MessageGroupId="botgroup"
    )
    print(response['MessageId'])


awsbroadcast({"type": "wallet_newpool", "data": {"pool": "b542160e4b100564473a89faff497f3416f65deae62fbf61023f8c6464b085e8", "record": {"saturation": 0, "metrics": {"controlled_stake": {"quantity": 0, "unit": "lovelace"}, "produced_blocks": {"quantity": 0, "unit": "block"}}, "cost": {"quantity": 0, "unit": "lovelace"}, "margin": {"quantity": 5, "unit": "percent"}, "apparent_performance": 0, "metadata": {"homepage": "https://godislove-ada.000webhostapp.com", "owner": "ed25519_pk1nwjxt290j4ehu8vnnvpsn3a6n5va5hxxflcw6vm5ydx7rpf8cxfsu9d0kq", "name": "Dios es Amor", "ticker": "DIOS", "pledge_address": "addr1skd6gedg472hxlsajwdsxzw8h2w3nkjuce8lpmfnws35mcv9ylqexh8ezmr"}, "id": "b542160e4b100564473a89faff497f3416f65deae62fbf61023f8c6464b085e8", "desirability": 0}}})
# awsbroadcast({"type":"block_minted","data":  {"pool":pool,"hash":currentHash, "height":currentHeight, "nbe":nbe, "nb":nb}})