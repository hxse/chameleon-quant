from datetime import datetime
from random import random

from bokeh.io import curdoc
from bokeh.models import ColumnDataSource, CategoricalColorMapper
from bokeh.plotting import figure
from bokeh.transform import transform
from tornado.ioloop import IOLoop
import pandas as pd
from pathlib import Path
import json
import sys

sys.path.append("src")
from plot.bokeh_plot import layout_plot
from bokeh.server.server import Server


def get_df(file_path):
    data = pd.read_csv(Path(file_path))
    return data


def get_cf(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data


def update(df_path, cf_path, name):
    def _update():
        nonlocal df_path, cf_path, name

        df_path = Path(df_path)
        cf_path = Path(cf_path)
        df = get_df(df_path)
        cf = get_cf(cf_path)
        ds = ColumnDataSource(data=df)

        last_time = ds.data["time"][-1]
        last_time2 = ds.data["time"][-2]
        last_open = ds.data["open"][-1]
        last_close = ds.data["close"][-1]

        if last_time != cf["time"] or last_time != df["time"].iloc[-1]:
            _ = {
                "index": df.iloc[-2:].index.to_list(),
                **df.iloc[-2:].to_dict(orient="list"),
            }
            ds.stream(
                _,
                #     # rollover=10,
            )
            print(name, last_time2, last_time)

    return _update


def modify_doc(df_path, cf_path, name, sleep=1000 * 5):
    def _modify_doc(doc):
        nonlocal df_path, cf_path, name, sleep
        df_path = Path(df_path)
        cf_path = Path(cf_path)
        df = get_df(df_path)
        cf = get_cf(cf_path)

        p = layout_plot(df, cf["plot_config"], plot_params=cf["plot_params"])

        doc.add_periodic_callback(update(df_path, cf_path, name), sleep)
        doc.add_root(p)

    return _modify_doc


def get_csv_list(dir_path):
    return [i for i in Path(dir_path).rglob("*.csv")]


def get_route_name(i):
    return (" ".join([*i.parts[-4:-1], i.stem])).replace(" ", "_")


def main(dir_path, sleep=1000 * 5):
    sleep = int(sleep)
    apps = {}
    for i in get_csv_list(dir_path):
        name = "/" + get_route_name(i)
        df_path = i
        cf_path = i.parent / (i.stem + ".json")
        apps[name] = modify_doc(df_path, cf_path, name, sleep)

    server = Server(
        apps,
        io_loop=IOLoop(),
        port=5006,
        allow_websocket_origin=["*"],
        allow_origin=["*", "0.0.0.0:2197"],
        address="0.0.0.0",
        show=False,
    )
    server.start()
    server.io_loop.add_callback(server.show, "/")
    server.io_loop.start()


if __name__ == "__main__":
    import sys

    main(sys.argv[1])
