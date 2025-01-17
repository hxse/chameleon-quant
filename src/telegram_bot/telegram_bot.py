import niquests
import json


def push_telegram_channel(config_path, data):
    with open(config_path, "r", encoding="utf-8") as file:
        config = json.load(file)

    tg_bot_token = config.get("tg_bot_token", None)
    tg_channel_id = config.get("tg_channel_id", None)
    if not tg_bot_token or not tg_channel_id:
        print("not detected tg_bot_token or tg_channel_id")
        return

    url = f"https://api.telegram.org/bot{tg_bot_token}/sendMessage?chat_id={tg_channel_id}&text={data}"

    res = niquests.get(url)
