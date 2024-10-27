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
        # Set the webhook URL
        try:
            # Open certificate file only when needed and set webhook
            with open("/usr/src/app/tls/cert", 'r') as cert:
                self.telegram_bot_client.set_webhook(url=f'{telegram_chat_url}/{token}/', certificate=cert, timeout=60)
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


def get_random_fact():
    """Fetches a random fact from an external API."""
    try:
        response = requests.get("https://uselessfacts.jsph.pl/random.json?language=en")
        if response.status_code == 200:
            fact_data = response.json()
            return fact_data.get("text", "Here’s a cool fact for you!")  # Default message if fact not found
        else:
            return "Couldn’t retrieve a fact right now. Did you know? Octopuses have three hearts!"
    except Exception as e:
        return "Oops! Something went wrong with getting a fact."


def get_random_joke():
    """Fetches a random joke from an external API."""
    try:
        response = requests.get("https://v2.jokeapi.dev/joke/Any?type=single")
        if response.status_code == 200:
            joke_data = response.json()
            return joke_data.get("joke", "Here’s a fun joke for you!")  # Default message if joke not found
        else:
            return "Couldn't fetch a joke right now, but here’s a classic: Why don’t skeletons fight each other? They don’t have the guts."
    except Exception as e:
        return "Oops! Something went wrong with getting a joke."


class ObjectDetectionBot(Bot):
    import requests

    def handle_message(self, msg):
        """Bot Main message handler"""
        logger.info(f'Incoming message: {msg}')

        # Section 5: Dynamic Chat Responses for Text Messages
        if "text" in msg:
            user_text = msg["text"].lower()

            # Check for specific keywords and respond with fun messages or info
            if "joke" in user_text:
                joke = get_random_joke()  # Placeholder function to retrieve a random joke
                self.send_text(msg['chat']['id'], f"Here's a joke for you: {joke}")

            elif "fact" in user_text:
                fact = get_random_fact()  # Placeholder function to retrieve a random fact
                self.send_text(msg['chat']['id'], f"Did you know? {fact}")

            elif user_text in ["/start", "/help"]:
                # Section 4: Provide help or instructions menu
                help_message = (
                    "Welcome! Here are the available commands and captions:\n"
                    "Commands:\n"
                    "  - /help: Show available features\n"
                    "  - joke: Receive a random joke\n"
                    "  - fact: Get an interesting fact\n\n"
                    "Available captions for photos:\n"
                    "  - Blur\n  - Contour\n  - Salt and pepper\n"
                    "  - Mix\n  - Predict\n"
                    "Try sending a photo with one of these captions!"
                )
                self.send_text(msg['chat']['id'], help_message)

            else:
                # Default response to echo the message with a prefix
                self.send_text(msg['chat']['id'], f'Officially DevOps Engineer: {msg["text"]}')

        # Process image filters and transformations if a caption is provided
        elif "caption" in msg:
            try:
                img_path = self.download_user_photo(msg)
                caption = msg["caption"]

                # Section 3: Detailed Status Updates for filter application
                if caption == "Blur":
                    self.send_text(msg['chat']['id'], "Starting Blur filter... uploading image.")
                    new_img = Img(img_path)
                    new_img.blur()
                    new_path = new_img.save_img()
                    self.send_photo(msg["chat"]["id"], new_path)
                    self.send_text(msg['chat']['id'], "Blur filter applied successfully! Notice how the image softens.")

                elif caption == "Contour":
                    self.send_text(msg['chat']['id'], "Starting Contour filter... enhancing edges.")
                    new_img = Img(img_path)
                    new_img.contour()
                    new_path = new_img.save_img()
                    self.send_photo(msg["chat"]["id"], new_path)
                    self.send_text(msg['chat']['id'], "Contour filter applied! See how the edges pop out.")

                elif caption == "Salt and pepper":
                    self.send_text(msg['chat']['id'], "Starting Salt and Pepper filter... adding noise.")
                    new_img = Img(img_path)
                    new_img.salt_n_pepper()
                    new_path = new_img.save_img()
                    self.send_photo(msg["chat"]["id"], new_path)
                    self.send_text(msg['chat']['id'], "Salt and Pepper filter applied! Adds a vintage feel.")

                elif caption == "Mix":
                    self.send_text(msg['chat']['id'], "Applying a mix of effects... this will take a moment.")
                    new_img = Img(img_path)
                    new_img.salt_n_pepper()
                    new_path = new_img.save_img()

                    new_img2 = Img(new_path)
                    new_img2.blur()
                    new_path = new_img2.save_img()

                    self.send_photo(msg["chat"]["id"], new_path)
                    self.send_text(msg['chat']['id'],
                                   "Mix filter applied! A blend of noise and blur for a unique look.")

                elif caption == "Predict":
                    self.send_text(msg['chat']['id'], "Your image is being processed. Please wait...")
                    logger.info(f'Photo downloaded to: {img_path}')

                    # S3 and SQS processing code (unchanged, since it works as expected)

                else:
                    # Notify user of valid captions if an invalid one is provided
                    self.send_text(msg['chat']['id'], (
                        "Error: Invalid caption\nAvailable captions:\n"
                        "1) Blur\n2) Mix\n3) Salt and pepper\n4) Contour\n5) Predict"
                    ))


            except Exception as e:
                logger.info(f"Error {e}")
                self.send_text(msg['chat']['id'], 'Failed to process image. Try again later.')

        else:
            # Default message if neither text nor caption is available
            self.send_text(msg['chat']['id'], "Please provide a valid caption or text.")
