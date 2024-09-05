import json
import os
from loguru import logger
import boto3
import flask
from botocore.exceptions import ClientError
from flask import request
from bot import ObjectDetectionBot

app = flask.Flask(__name__)


# TODO load TELEGRAM_TOKEN value from Secret Manager
def get_secret():
    secret_name = "ehabo_telegram_tokenV1_tf"
    region_name = os.environ['REGION_NAME']

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        raise e

    secret = get_secret_value_response['SecretString']

    return secret


secret_json_str = get_secret()
if secret_json_str:
    secret_dict = json.loads(secret_json_str)
    TELEGRAM_TOKEN = secret_dict.get('token')
else:
    print("Failed to retrieve the secret")

TELEGRAM_APP_URL = os.environ['TELEGRAM_APP_URL']

# logger.info(f"Token: {TELEGRAM_TOKEN}")
# logger.info(f"Telegram Chat URL: {TELEGRAM_APP_URL}")

@app.route('/health_check', methods=['GET'])
def health_check():
    return 'Ok', 200


@app.route('/', methods=['GET'])
def index():
    return 'Ok'


@app.route(f'/{TELEGRAM_TOKEN}/', methods=['POST'])
def webhook():
    req = request.get_json()
    bot.handle_message(req['message'])
    return 'Ok'


@app.route(f'/results', methods=['POST'])
def results():
    # TODO use the prediction_id to retrieve results from DynamoDB and send to the end-user
    region_name = os.environ['REGION_NAME']
    dynamodb = boto3.resource('dynamodb', region_name=region_name)
    table = dynamodb.Table('ehabo-PolybotService-DynamoDB-tf')

    logger.info("Received request at /results endpoint")
    try:
        prediction_id = flask.request.args.get('predictionId')
        if not prediction_id:
            prediction_id = flask.request.json.get('predictionId')

        if not prediction_id:
            return 'predictionId is required', 400

        response = table.get_item(Key={'prediction_id': prediction_id})
        if 'Item' in response:
            item = response['Item']
            chat_id = item['chat_id']
            labels = item['labels']
           
            class_counts = {}
            for label in labels:
                class_name = label['class']
                if class_name in class_counts:
                    class_counts[class_name] += 1
                else:
                    class_counts[class_name] = 1

            # text_results = f"Prediction results for image {item['original_img_path']}:\n"
            text_results = ""
            for class_name, count in class_counts.items():
                text_results += f"{class_name}: {count}\n"

            bot.send_text(chat_id, text_results)
            return 'Ok'
        else:
            return 'No results found', 404
    except Exception as e:
        print(f"Error processing results: {str(e)}")
        return 'Error', 500


@app.route(f'/loadTest/', methods=['POST'])
def load_test():
    req = request.get_json()
    bot.handle_message(req['message'])
    return 'Ok'


if __name__ == "__main__":
    bot = ObjectDetectionBot(TELEGRAM_TOKEN, TELEGRAM_APP_URL)
    app.run(host='0.0.0.0', port=8443)
