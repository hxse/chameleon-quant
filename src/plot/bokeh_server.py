import colorcet as cc
from bokeh.server.server import Server
from bokeh.application import Application
from bokeh.application.handlers.function import FunctionHandler
from bokeh.plotting import figure, ColumnDataSource
from bokeh.models import Button
from bokeh.layouts import column, row
from pathlib import Path
import sys
import json
import pandas as pd
import sys
import numpy as np

sys.path.append("src")
from plot.bokeh_plot import layout_plot, get_source_plot, get_df_dict


def get_df(file_path):
    data = pd.read_csv(Path(file_path))
    return data


def get_cf(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data


def get_csv_list(dir_path):
    return [i for i in Path(dir_path).rglob("*.csv")]


def get_route_name(i):
    return (" ".join([*i.parts[-4:-1], i.stem])).replace(" ", "_")


def make_document(df_path, cf_path, name, sleep=1000 * 15, test=False):
    def _make_document(doc):
        nonlocal df_path, cf_path, name, sleep, test
        callback_obj = None

        df = get_df(df_path)
        cf = get_cf(cf_path)
        df_dict = get_df_dict(df, plot_params=cf["plot_params"])

        # plot 1
        p1 = figure(title="Streaming Line Plot - Step 0", width=800, height=400)
        color = "red" if "btc" in name else "green"
        p1.line(
            x="index", y="close", source=df_dict["source_df"], color=color, line_width=2
        )
        # plot 2
        p2 = layout_plot(df_dict, cf["plot_config"], plot_params=cf["plot_params"])

        def change_range(source_df, offset=3):
            nonlocal p2, p1
            plot_arr = [i for i in p2.select(dict(name="candle_plot"))]
            if len(plot_arr) > 0:
                x_end = source_df.data["index"][-1]
                print(x_end, plot_arr[0].x_range.end)
                if x_end - plot_arr[0].x_range.end < 10:
                    plot_arr[0].x_range.end = x_end + offset

        def patch_data(df_dict):
            arr = [
                "long_price_even",
                "long_price_odd",
                "short_price_even",
                "short_price_odd",
            ]
            for i in arr:

                if "long" in i and df_dict["source_plot"].data["long_status"][-1] == 0:
                    name = None
                    if not np.isnan(df_dict["source_plot"].data[i][-1]):
                        name = i

                    if name:
                        source_plot_df = df_dict["source_plot"].to_df()
                        start = source_plot_df.loc[
                            source_plot_df["long_status"] == 1
                        ].index[-1]
                        stop = source_plot_df.index[-1]

                        source_plot_df.loc[source_plot_df["long_status"] == 2, name] = (
                            np.nan
                        )
                        new_data = source_plot_df[name][start : stop + 1].interpolate(
                            method="linear"
                        )
                        _new_data = new_data[:-1]
                        _c = list(zip(_new_data.index.tolist(), _new_data.tolist()))
                        df_dict["source_plot"].patch({name: _c})

                if (
                    "short" in i
                    and df_dict["source_plot"].data["short_status"][-1] == 0
                ):
                    name = None
                    if not np.isnan(df_dict["source_plot"].data[i][-1]):
                        name = i

                    if name:
                        source_plot_df = df_dict["source_plot"].to_df()
                        start = source_plot_df.loc[
                            source_plot_df["short_status"] == 1
                        ].index[-1]
                        stop = source_plot_df.index[-1]

                        source_plot_df.loc[
                            source_plot_df["short_status"] == 2, name
                        ] = np.nan
                        new_data = source_plot_df[name][start : stop + 1].interpolate(
                            method="linear"
                        )
                        _new_data = new_data[:-1]
                        _c = list(zip(_new_data.index.tolist(), _new_data.tolist()))
                        df_dict["source_plot"].patch({name: _c})

        def button1_run():
            nonlocal callback_obj
            if button1.label == "Run":
                button1.label = "Stop"
                button1.button_type = "danger"
                callback_obj = doc.add_periodic_callback(button2_step, 1000)
            else:
                button1.label = "Run"
                button1.button_type = "success"
                doc.remove_periodic_callback(callback_obj)

        def button2_step():
            nonlocal df_path, cf_path, name, sleep, test, df_dict

            df_path = Path(df_path)
            cf_path = Path(cf_path)
            df = get_df(df_path)
            cf = get_cf(cf_path)
            new_df_dict = get_df_dict(df, plot_params=cf["plot_params"])

            if (
                df_dict["source_df"].data["time"][-1]
                == new_df_dict["source_df"].data["time"][-1]
            ):
                return

            for _d in df_dict.keys():
                data_source = df_dict[_d]
                new_source_df = new_df_dict[_d]
                if new_source_df is None or type(new_source_df) == pd.DataFrame:
                    continue

                _data = {}
                for i in data_source.data.keys():
                    _data[i] = [new_source_df.data[i][-1]]

                # test
                # if test:
                #     _data["index"] = [data_source.data["index"][-1] + 1]
                #     _data["time"] = [data_source.data["time"][-1] + 3600000]
                #     _data["open"] = [data_source.data["open"][-1] + 10]
                #     _data["high"] = [data_source.data["high"][-1] + 10]
                #     _data["low"] = [data_source.data["low"][-1] + 6]
                #     _data["close"] = [data_source.data["close"][-1] + 6]

                data_source.stream(_data)
            patch_data(df_dict)
            change_range(df_dict["source_df"])

        button1 = Button(label="Run", button_type="success", width=390)
        button1.on_click(button1_run)
        button2 = Button(label="Step", button_type="primary", width=390)
        button2.on_click(button2_step)

        p1_test = column(
            row(button1, button2), p1, sizing_mode="scale_width", width=800, height=400
        )
        p2_test = column(
            row(button1, button2), p2, sizing_mode="scale_width", width=800, height=400
        )
        doc.add_root(p2_test if test else p2)  # p1, p2, p1_test, p2_test
        doc.title = "Now with live updating!"
        button1_run()

    return _make_document


def main(dir_path, sleep=1000 * 15, test=False):
    dir_path = Path(dir_path)
    sleep = int(sleep)
    test = 1 if test in [True, "True", "true", "1", 1] else 0
    apps = {}
    for i in get_csv_list(dir_path):
        name = "/" + get_route_name(i)
        df_path = i
        cf_path = i.parent / (i.stem + ".json")
        app = Application(
            FunctionHandler(make_document(df_path, cf_path, name, sleep, test))
        )
        apps[name] = app

    server = Server(apps, port=5006)
    server.start()
    server.io_loop.add_callback(server.show, "/")
    server.io_loop.start()


if __name__ == "__main__":
    import sys

    main(*sys.argv[1:])
