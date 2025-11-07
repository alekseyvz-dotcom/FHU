# telegram_client.py
import requests
from typing import Union

class TelegramClient:
    def __init__(self, token: str, chat_id: Union[int, str]):
        self.token = token
        self.chat_id = chat_id

    def send_message(self, text: str):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        resp = requests.post(url, json={"chat_id": self.chat_id, "text": text})
        if resp.status_code != 200:
            raise RuntimeError(f"Telegram API error: {resp.status_code} {resp.text}")
