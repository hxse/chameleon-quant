import niquests
import json
from bokeh.plotting import figure, output_file, save
from bokeh.io import export_png
from pathlib import Path
import datetime
import time


def time_decorate(name):
    def time_decorator(func):
        def wrapper_function(*args, **kwargs):
            start_time = time.time()
            func(*args, **kwargs)
            print(f"{name} {time.time() - start_time}")

        return wrapper_function

    return time_decorator


def convert_np2json(_dict):
    for k, v in _dict.items():
        if "numpy.int64" in str(type(v)):
            _dict[k] = int(v)
        if "numpy.float64" in str(type(v)):
            _dict[k] = float(v)
        if "numpy.bool_" in str(type(v)):
            _dict[k] = bool(v)
    _dict["func_arr"] = []


def get_fig_path(csv_path, dir_name="fig_data"):
    """
    根据csv_path拼接fig_path
    """
    fig_path = Path(
        *[*Path(csv_path).parts[:-5], dir_name, *[*Path(csv_path).parts[-4:]]]
    )
    return fig_path.parent / (fig_path.stem + ".html")


@time_decorate("save fig done ")
def save_fig_file(fig, config_path, csv_path, _):
    if csv_path:
        fig_path = get_fig_path(csv_path)
        fig_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        fig_path = (Path(config_path).parent) / "fig.html"

    save(fig, fig_path)
    print("html文件已存档", fig_path)
    return fig_path


@time_decorate("save df done ")
def save_df_file(df, config_path, csv_path, _):
    if csv_path:
        df_path = get_fig_path(csv_path)
        df_path = df_path.parent / (df_path.stem + ".csv")
        df_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        df_path = (Path(config_path).parent) / "df.csv"

    filepath = Path(df_path)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(df_path, index=False)

    _c = {
        "time": int(df.iloc[-1]["time"]),
        "plot_config": _["plot_config"],
        "plot_params": _["plot_params"],
    }
    convert_np2json(_c["plot_params"])
    with open(df_path.parent / (df_path.stem + ".json"), "w", encoding="utf-8") as file:
        json.dump(_c, file, ensure_ascii=False, indent=4)

    print("df csv文件已存档", df_path)
    return df_path


def push_telegram_channel(config_path, data, fig=None, fig_path="", send_html=False):
    try:
        with open(config_path, "r", encoding="utf-8") as file:
            config = json.load(file)

        tg_bot_token = config.get("tg_bot_token", None)
        tg_channel_id = config.get("tg_channel_id", None)
        if not tg_bot_token or not tg_channel_id:
            print("not detected tg_bot_token or tg_channel_id")
            return

        data = ("\n".join([f"{k}: {v}" for k, v in data.items()])).replace("\n", "%0A")
        url = f"https://api.telegram.org/bot{tg_bot_token}/sendMessage?chat_id={tg_channel_id}&text={data}"

        res = niquests.get(url)

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

    except Exception as e:
        error = f"{type(e).__name__} {str(e)}"
        print("push_telegram_channel:", error)
        return error
