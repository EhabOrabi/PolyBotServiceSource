import json
import uuid
import logging
import requests
import telebot
from loguru import logger
import os
import time
from telebot.types import InputFile
from img_proc import Img
import boto3

# Setup loguru logger
logger.add("debug.log", format="{time} {level} {message}", level="DEBUG", rotation="10 MB")


class Bot:

    def __init__(self, token, telegram_chat_url):
        self.telegram_bot_client = telebot.TeleBot(token)
        logger.info(f"Token: {token}")
        logger.info(f"Telegram Chat URL: {telegram_chat_url}")

        # Remove existing webhook
        try:
            self.telegram_bot_client.remove_webhook()
            logger.info("Webhook removed successfully.")
        except Exception as e:
            logger.error(f"Error removing webhook: {e}")

        time.sleep(0.5)

        # Check URL accessibility with retries
        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = requests.get(f'{telegram_chat_url}/{token}/', timeout=10)
                if response.status_code == 200:
                    logger.info(f"Response status code: {response.status_code}")
                    break
                else:
                    logger.error(f"Webhook URL check failed with status code: {response.status_code}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Attempt {attempt + 1} - Error checking webhook URL: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error("Max retries exceeded. Unable to check webhook URL.")
                    return

        # Set the webhook URL
        try:
            self.telegram_bot_client.set_webhook(url=f'{telegram_chat_url}/{token}/', timeout=60)
            logger.info("Webhook set successfully.")
        except Exception as e:
            logger.error(f"Error setting webhook: {e}")

        # Log bot information
        try:
            bot_info = self.telegram_bot_client.get_me()
            logger.info(f'Telegram Bot information\n\n{bot_info}')
        except Exception as e:
            logger.error(f"Error getting bot information: {e}")

    def send_text(self, chat_id, text):
        self.telegram_bot_client.send_message(chat_id, text)

    def send_text_with_quote(self, chat_id, text, quoted_msg_id):
        self.telegram_bot_client.send_message(chat_id, text, reply_to_message_id=quoted_msg_id)

    def is_current_msg_photo(self, msg):
        return 'photo' in msg

    def download_user_photo(self, msg):
        """
        Downloads the photos that sent to the Bot to `photos` directory (should be existed)
        :return:
        """
        if not self.is_current_msg_photo(msg):
            raise RuntimeError(f'Message content of type \'photo\' expected')

        file_info = self.telegram_bot_client.get_file(msg['photo'][-1]['file_id'])
        data = self.telegram_bot_client.download_file(file_info.file_path)
        folder_name = file_info.file_path.split('/')[0]

        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        with open(file_info.file_path, 'wb') as photo:
            photo.write(data)

        return file_info.file_path

    def send_photo(self, chat_id, img_path):
        if not os.path.exists(img_path):
            raise RuntimeError("Image path doesn't exist")

        self.telegram_bot_client.send_photo(
            chat_id,
            InputFile(img_path)
        )

    def handle_message(self, msg):
        """Bot Main message handler"""
        logger.info(f'Incoming message: {msg}')
        self.send_text(msg['chat']['id'], f'Your original message: {msg["text"]}')


class ObjectDetectionBot(Bot):
    def handle_message(self, msg):
        """Bot Main message handler"""
        # logger.info(f'Incoming message: {msg}')
        if "text" in msg:
            self.send_text(msg['chat']['id'], f'Your original message: {msg["text"]}')
        else:
            # if there is checkbox caption
            if "caption" in msg:
                try:
                    img_path = self.download_user_photo(msg)
                    if msg["caption"] == "Blur":
                        # Send message to telegram bot
                        self.send_text(msg['chat']['id'], "Blur filter in progress")
                        new_img = Img(img_path)
                        new_img.blur()
                        new_path = new_img.save_img()
                        self.send_photo(msg["chat"]["id"], new_path)
                        self.send_text(msg['chat']['id'], "Blur filter applied")
                    elif msg["caption"] == "Contour":
                        self.send_text(msg['chat']['id'], "Contour filter in progress")
                        new_img = Img(img_path)
                        new_img.contour()
                        new_path = new_img.save_img()
                        self.send_photo(msg["chat"]["id"], new_path)
                        self.send_text(msg['chat']['id'], "Contour filter applied")
                    elif msg["caption"] == "Salt and pepper":  # concat, segment
                        self.send_text(msg['chat']['id'], "Salt and pepper filter in progress")
                        new_img = Img(img_path)
                        new_img.salt_n_pepper()
                        new_path = new_img.save_img()
                        self.send_photo(msg["chat"]["id"], new_path)
                        self.send_text(msg['chat']['id'], "Salt and pepper filter applied")
                    elif msg["caption"] == "Mix":
                        self.send_text(msg['chat']['id'], "Mix filter in progress")
                        new_img = Img(img_path)
                        new_img.salt_n_pepper()
                        new_path = new_img.save_img()

                        new_img2 = Img(new_path)
                        new_img2.blur()
                        new_path = new_img2.save_img()

                        self.send_photo(msg["chat"]["id"], new_path)
                        self.send_text(msg['chat']['id'], "mix filter applied")

                    elif msg["caption"] == "Predict":
                        self.send_text(msg['chat']['id'], "Your image is being processed. Please wait...")
                        logger.info(f'Photo downloaded to: {img_path}')

                        # Split photo name
                        photo_s3_name = img_path.split("/")

                        # Get the bucket name from the environment variable
                        images_bucket = os.environ['BUCKET_NAME']
                        sqs_queue_url = os.environ['SQS_QUEUE_URL']
                        region_name = os.environ['REGION_NAME']
                        # Upload the image to S3
                        s3_client = boto3.client('s3')
                        s3_client.upload_file(img_path, images_bucket, photo_s3_name[-1])

                        # Prepare the data to be sent to SQS
                        prediction_id = str(uuid.uuid4())
                        json_data = {
                            'imgName': img_path,
                            'chat_id': msg['chat']['id'],
                            'prediction_id': prediction_id
                        }

                        try:
                            # Send job to queue
                            sqs = boto3.client('sqs', region_name=region_name)
                            response = sqs.send_message(
                                QueueUrl=sqs_queue_url,
                                MessageBody=json.dumps(json_data)
                            )
                        except Exception as e:
                            logger.error(f'Error: {str(e)}')
                            self.send_text(msg['chat']['id'], 'Failed to process the image. Please try again later.')
                    else:
                        self.send_text(msg['chat']['id'],"Error invalid caption\n Available captions are :\n1) Blur\n2) Mix\n3) Salt and pepper\n4) Contour\n5) Predict")
                except Exception as e:
                    logger.info(f"Error {e}")
                    self.send_text(msg['chat']['id'], f'failed - try again later')
            else:
                self.send_text(msg['chat']['id'], "please provide caption")
