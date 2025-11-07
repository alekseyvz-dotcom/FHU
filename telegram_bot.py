from typing import Union
from telegram import Bot

class TelegramClient:
    def __init__(self, token: str, chat_id: Union[int, str]):
        self.bot = Bot(token=token)
        self.chat_id = chat_id

    def send_message(self, text: str):
        self.bot.send_message(chat_id=self.chat_id, text=text)
