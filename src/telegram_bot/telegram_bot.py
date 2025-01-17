import niquests
import json
from bokeh.plotting import figure, output_file, save
from bokeh.io import export_png
from pathlib import Path


def push_telegram_channel(config_path, data, fig=None, send_html=False):
    with open(config_path, "r", encoding="utf-8") as file:
        config = json.load(file)

    tg_bot_token = config.get("tg_bot_token", None)
    tg_channel_id = config.get("tg_channel_id", None)
    if not tg_bot_token or not tg_channel_id:
        print("not detected tg_bot_token or tg_channel_id")
        return

    url = f"https://api.telegram.org/bot{tg_bot_token}/sendMessage?chat_id={tg_channel_id}&text={data}"

    res = niquests.get(url)

    fig_path = (Path(config_path).parent) / "fig.html"
    save(fig, fig_path)
    print("html文件已存档", fig_path)

    if send_html:
        with open(fig_path, "rb") as f:
            file_data = f.read()

        url = f"https://api.telegram.org/bot{tg_bot_token}/sendDocument"
        res = niquests.post(
            url,
            data={
                "chat_id": tg_channel_id,
                "parse_mode": "HTML",
                "caption": "This is my file",
            },
            files={"document": ("fig.html", file_data)},
        )
        print(res)
