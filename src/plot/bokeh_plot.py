import pandas as pd
from bokeh.plotting import figure, show
from bokeh.models import (
    CustomJS,
    ColumnDataSource,
    HoverTool,
    DatetimeTickFormatter,
    CrosshairTool,
    Span,
    Band,
)
from bokeh.io import output_notebook
import numpy as np
from bokeh.layouts import gridplot, column
from bokeh.models.ranges import DataRange1d


def get_df_dict(df, plot_params={}):
    df["left"] = df.index.astype(np.float64) - 0.4
    df["right"] = df.index.astype(np.float64) + 0.4
    _df = df[["time", "date", "open", "high", "low", "close", "left", "right"]]
    _c = ~_df.columns.isin(["time", "date"])
    df_inc = _df.copy()
    df_inc.loc[df_inc.close <= df_inc.open, _c] = np.nan
    df_dec = _df.copy()
    df_dec.loc[df_dec.close > df_dec.open, _c] = np.nan

    source_df = ColumnDataSource(data=df)
    source_inc = ColumnDataSource(data=df_inc)
    source_dec = ColumnDataSource(data=df_dec)

    _ = {}
    if "split_dict" in plot_params and len(plot_params["split_dict"].keys()) > 0:
        split_dict = plot_params["split_dict"]
        train_stop = split_dict["train_stop"]
        valid_start = split_dict["valid_start"]
        valid_stop = split_dict["valid_stop"]
        test_start = split_dict["test_start"]
        test_stop = split_dict["test_stop"]
        source_valid = ColumnDataSource(data=df[valid_start:valid_stop])
        source_test = ColumnDataSource(data=df[test_start:test_stop])
        _["source_valid"] = source_valid
        _["source_test"] = source_test

    source_plot = get_source_plot(df)

    df.drop(["left"], axis=1, inplace=True)
    df.drop(["right"], axis=1, inplace=True)

    return {
        "df": df,
        "source_df": source_df,
        "source_inc": source_inc,
        "source_dec": source_dec,
        "source_plot": source_plot,
        **_,
    }


def get_source_plot(df):
    df = df.copy()
    df["_long_price"] = df["long_price"]
    df.loc[df["long_status"] == 2, "_long_price"] = np.nan
    df["_long_price"] = df["_long_price"].interpolate(method="linear")
    df.loc[df["long_status"] == -1, "_long_price"] = np.nan

    df["_short_price"] = df["short_price"]
    df.loc[df["short_status"] == 2, "_short_price"] = np.nan
    df["_short_price"] = df["_short_price"].interpolate(method="linear")
    df.loc[df["short_status"] == -1, "_short_price"] = np.nan

    _arr = [
        ["long_price_even", "_long_price", "long_idx2", 0],
        ["long_price_odd", "_long_price", "long_idx2", 1],
        ["short_price_even", "_short_price", "short_idx2", 0],
        ["short_price_odd", "_short_price", "short_idx2", 1],
        ["long_sl_even", "long_sl", "long_idx2", 0],
        ["long_sl_odd", "long_sl", "long_idx2", 1],
        ["short_sl_even", "short_sl", "short_idx2", 0],
        ["short_sl_odd", "short_sl", "short_idx2", 1],
        ["long_tp_even", "long_tp", "long_idx2", 0],
        ["long_tp_odd", "long_tp", "long_idx2", 1],
        ["short_tp_even", "short_tp", "short_idx2", 0],
        ["short_tp_odd", "short_tp", "short_idx2", 1],
        ["long_tsl_even", "long_tsl", "long_idx2", 0],
        ["long_tsl_odd", "long_tsl", "long_idx2", 1],
        ["short_tsl_even", "short_tsl", "short_idx2", 0],
        ["short_tsl_odd", "short_tsl", "short_idx2", 1],
    ]
    for i in _arr:
        target, origin, idx2, mode = i
        df[target] = np.nan
        df.loc[df[idx2] % 2 == mode, target] = df[origin]

    df.drop(["_long_price"], axis=1, inplace=True)
    df.drop(["_short_price"], axis=1, inplace=True)

    # for i in _arr:
    #     df.drop(i[0], axis=1, inplace=True)

    for i in df.columns:
        if i.startswith("chan_price") and not i.startswith("_"):
            df[f"_{i}"] = df[i]
            df[f"_{i}"] = df[f"_{i}"].interpolate(method="linear")

    macd_columns = [
        i for i in df.columns if i.startswith("macd") and not i.startswith("_")
    ]
    if len(macd_columns) > 0:
        df[f"macd0"] = 0
        df["macdh_inc"] = df["macdh"]
        df["macdh_dec"] = df["macdh"]
        df.loc[df["macdh"] <= 0, "macdh_inc"] = np.nan
        df.loc[df["macdh"] > 0, "macdh_dec"] = np.nan

    source = ColumnDataSource(data=df)
    return source


def add_indicator(fig, df_dict, plot_params=None):
    df = df_dict["df"]
    source_plot = df_dict["source_plot"]

    # inc = df.close > df.open
    # dec = ~inc

    # source_inc = ColumnDataSource(data=df[inc])
    # source_dec = ColumnDataSource(data=df[dec])

    color = ["orange", "green", "blue", "purple", "grey"]
    for k, v in enumerate([i for i in df.columns if "linreg" in i]):
        fig.line(
            "index",
            v,
            source=source_plot,
            line_width=2,
            line_alpha=1,
            line_color=color[k] if k < len(color) else color[len(color) - 1],
            visible=True,
            # line_dash="dotted",
        )

    color = ["orange", "green", "blue", "purple", "grey"]
    for k, v in enumerate([i for i in df.columns if "ma_" in i]):
        fig.line(
            "index",
            v,
            source=source_plot,
            line_width=2,
            line_alpha=1,
            line_color=color[k] if k < len(color) else color[len(color) - 1],
            visible=True,
        )

    color = ["orange", "purple"]
    for k, v in enumerate([i for i in df.columns if ("st_" in i)]):
        fig.line(
            "index",
            v,
            source=source_plot,
            line_width=2,
            line_alpha=1,
            line_color=color[k] if k < len(color) else color[len(color) - 1],
            visible=True,
        )

    for i in df.columns:
        for c in ["CM"]:
            if c in i:
                name, suffix = i.rsplit("_", 1)
                fig.line(
                    "index",
                    f"{name}_{suffix}",
                    source=source_plot,
                    line_width=2,
                    line_alpha=1,
                    line_color="grey",
                    visible=True,
                )
        for c in ["CU"]:
            if c in i:
                name, suffix = i.rsplit("_", 1)
                band = Band(
                    base="index",
                    lower=f"CL_{suffix}" if name == "CU" else f"CL_{suffix}",
                    upper=f"CU_{suffix}" if name == "CU" else f"CU_{suffix}",
                    source=source_plot,
                    fill_alpha=0.03,
                    fill_color="blue",
                    line_color="black",
                )
                fig.add_layout(band)

    for i in [
        ["long_price_even", "orange"],
        ["long_price_odd", "orange"],
        ["short_price_even", "purple"],
        ["short_price_odd", "purple"],
    ]:
        col_name, color = i
        # 仓位菱形线
        fig.line(
            "index",
            col_name,
            source=source_plot,
            line_width=12,
            line_alpha=0.7,
            line_color=color,
            visible=True,
            line_dash="dotted",
        )

    for i in [
        ["long_sl_even", "orange"],
        ["long_sl_odd", "orange"],
        ["short_sl_even", "purple"],
        ["short_sl_odd", "purple"],
    ]:
        col_name, color = i
        # 仓位止损线
        fig.line(
            "index",
            col_name,
            source=source_plot,
            line_width=4,
            line_alpha=1,
            line_color=color,
            visible=True,
            line_dash="dotted",
        )

    for i in [
        ["long_tp_even", "orange"],
        ["long_tp_odd", "orange"],
        ["short_tp_even", "purple"],
        ["short_tp_odd", "purple"],
    ]:
        col_name, color = i
        # 仓位止盈线
        fig.line(
            "index",
            col_name,
            source=source_plot,
            line_width=4,
            line_alpha=1,
            line_color=color,
            visible=True,
            line_dash="dotted",
        )

    for i in [
        ["long_tsl_even", "orange"],
        ["long_tsl_odd", "orange"],
        ["short_tsl_even", "purple"],
        ["short_tsl_odd", "purple"],
    ]:
        col_name, color = i
        # 仓位追踪止损线
        fig.line(
            "index",
            col_name,
            source=source_plot,
            line_width=4,
            line_alpha=1,
            line_color=color,
            visible=True,
            line_dash="dashed",
        )


def add_hover(fig, df_dict):
    df = df_dict["df"]
    source_df = df_dict["source_df"]
    # source = ColumnDataSource(data=df)
    close_line = fig.line(
        "index", "close", source=source_df, line_width=2, line_alpha=0, visible=True
    )
    tooltips = [
        ("y", "$y"),
        ("index", "@index"),
        ("date", "@date{%Y-%m-%d %H:%M:%S %z}"),
        ("open", "@open"),
        ("high", "@high"),
        ("low", "@low"),
        ("close", "@close"),
        ("merge_diff", "@merge_diff"),
        ("merge_total", "@merge_total"),
    ]
    for i in reversed(["rsi", "atr"]):
        if i in df.columns:
            tooltips.insert(7, (f"{i}", f"@{i}"))
    # hovertool 没有办法调整时区 https://github.com/bokeh/bokeh/issues/1135
    hover = HoverTool(
        renderers=[close_line],
        tooltips=tooltips,
        formatters={"@date": "datetime"},
        mode="vline",
        point_policy="follow_mouse",
    )
    fig.add_tools(hover)


def candlestick_plot(
    plot_config_item,
    df_dict,
    width=800,
    height=400,
    width_scale=1,
    height_scale=0.75,
    plot_params=None,
):
    """
    DataFrame 参考格式:
        date	open	high	low	close	volume
    0	2000-03-01	89.62	94.09	88.94	90.81	106889800
    1	2000-03-02	91.81	95.37	91.12	93.37	106932600
    2	2000-03-03	94.75	98.87	93.87	96.12	101435200
    """

    source_df = df_dict["source_df"]
    source_inc = df_dict["source_inc"]
    source_dec = df_dict["source_dec"]
    source_plot = df_dict["source_plot"]

    fig = figure(
        name="candle_plot",
        sizing_mode="scale_width",
        tools="xpan,reset,xwheel_zoom,undo,redo,save",  # crosshair
        active_drag="xpan",
        active_scroll="xwheel_zoom",
        x_axis_type="datetime",
        width=int(width * width_scale),
        height=int(height * height_scale),
        output_backend="webgl",
    )

    # inc = df.close > df.open
    # dec = ~inc

    # source = ColumnDataSource(data=df)
    # source_inc = ColumnDataSource(data=df[inc])
    # source_dec = ColumnDataSource(data=df[dec])

    fig.segment(
        "index",
        "high",
        "index",
        "low",
        color="green",
        source=source_inc,
    )
    fig.segment(
        "index",
        "high",
        "index",
        "low",
        color="red",
        source=source_dec,
    )
    bar_inc = fig.quad(
        top="close",
        bottom="open",
        left="left",
        right="right",
        source=source_inc,
        fill_color="green",
        line_color=None,
    )
    bar_dec = fig.quad(
        top="close",
        bottom="open",
        left="left",
        right="right",
        source=source_dec,
        fill_color="red",
        line_color=None,
    )
    color_arr = ["brown", "goldenrod", "cornflowerblue", "cyan", "blue", "gray"]
    n = 0
    for c in source_plot.data.keys():
        if c.startswith("ohlc4"):
            fig.line(
                "index",
                c,
                source=source_plot,
                line_width=2,
                line_alpha=1,
                line_color="gray",
                visible=True,
            )
        if c.startswith("_chan_price"):
            fig.line(
                "index",
                c,
                source=source_plot,
                line_width=2,
                line_alpha=1,
                line_color=color_arr[n] if n < len(color_arr) else color_arr[-1],
                visible=True,
            )
            _c = c[1:].replace("price", "break")
            if _c not in plot_params["display_chan_break"]:
                fig.scatter(
                    "index",
                    _c,
                    source=source_plot,
                    size=10,
                    color=color_arr[n] if n < len(color_arr) else color_arr[-1],
                    alpha=0.4,
                )
            n += 1
    return [fig, ["high", "low"]]


def filter_columns(key_arr, columns):
    return list(dict.fromkeys([i for i in columns for k in key_arr if i.startswith(k)]))


def line_plot(
    plot_config_item,
    df_dict,
    width=800,
    height=400,
    width_scale=1,
    height_scale=0.25,
    plot_params=None,
):
    df = df_dict["df"]
    source_df = df_dict["source_df"]
    source_plot = df_dict["source_plot"]

    fig = figure(
        name=f'{plot_config_item["name"]}_plot',
        sizing_mode="scale_width",
        tools="xpan,reset,xwheel_zoom,undo,redo,save",  # crosshair
        active_drag="xpan",
        active_scroll="xwheel_zoom",
        x_axis_type="datetime",
        width=int(width * width_scale),
        height=int(height * height_scale),
        output_backend="webgl",
    )

    color = ["orange", "green", "blue", "purple", "grey"]
    item_columns = filter_columns(plot_config_item["key"], df.columns)
    for k, v in enumerate(item_columns):
        if v == "macdh":
            fig.quad(
                top="macdh_inc",
                bottom="macd0",
                left="left",
                right="right",
                source=source_plot,
                fill_color="green",
                line_color=None,
            )
            fig.quad(
                top="macdh_dec",
                bottom="macd0",
                left="left",
                right="right",
                source=source_plot,
                fill_color="red",
                line_color=None,
            )
            continue
        fig.line(
            "index",
            v,
            source=source_df,
            line_width=2,
            line_alpha=1,
            line_color=color[k] if k < len(color) else color[len(color) - 1],
            visible=True,
        )

    return [fig, item_columns]


def add_total(fig, source_df, plot_params, side_arr=[]):
    res_col = []
    if (
        "merge_total" in side_arr
        and plot_params
        and "long_count" in plot_params
        and plot_params["long_count"] > 0
        and "short_count" in plot_params
        and plot_params["short_count"] > 0
    ):

        fig.line(
            "index",
            "merge_total",
            source=source_df,
            line_width=2,
            line_alpha=1,
            line_color="black",
            visible=True,
        )
        res_col.append("merge_total")

        if "enable_hold" in plot_params and "long" in plot_params["enable_hold"]:
            fig.line(
                "index",
                "long_hold",
                source=source_df,
                line_width=2,
                line_alpha=1,
                line_color="orange",
                # line_dash="dotted",
                visible=True,
            )
            res_col.append("long_hold")

        if "enable_hold" in plot_params and "short" in plot_params["enable_hold"]:
            fig.line(
                "index",
                "short_hold",
                source=source_df,
                line_width=2,
                line_alpha=1,
                line_color="purple",
                # line_dash="dotted",
                visible=True,
            )
            res_col.append("short_hold")

    if (
        "long_total" in side_arr
        and plot_params
        and "long_count" in plot_params
        and plot_params["long_count"] > 0
    ):
        fig.line(
            "index",
            "long_total",
            source=source_df,
            line_width=2,
            line_alpha=1,
            line_color="green",
            visible=True,
        )
        res_col.append("long_total")

        if plot_params["short_count"] == 0:
            if "enable_hold" in plot_params and "long" in plot_params["enable_hold"]:
                fig.line(
                    "index",
                    "long_hold",
                    source=source_df,
                    line_width=2,
                    line_alpha=1,
                    line_color="orange",
                    # line_dash="dotted",
                    visible=True,
                )
                res_col.append("long_hold")

    if (
        "short_total" in side_arr
        and plot_params
        and "short_count" in plot_params
        and plot_params["short_count"] > 0
    ):
        fig.line(
            "index",
            "short_total",
            source=source_df,
            line_width=2,
            line_alpha=1,
            line_color="red",
            visible=True,
        )
        res_col.append("short_total")

        if plot_params["long_count"] == 0:
            if "enable_hold" in plot_params and "short" in plot_params["enable_hold"]:
                fig.line(
                    "index",
                    "short_hold",
                    source=source_df,
                    line_width=2,
                    line_alpha=1,
                    line_color="purple",
                    # line_dash="dotted",
                    visible=True,
                )
                res_col.append("short_hold")
    return res_col


def backtest_plot(
    plot_config_item,
    df_dict,
    width=800,
    height=400,
    width_scale=1,
    height_scale=0.25,
    plot_params=None,
):
    source_df = df_dict["source_df"]

    fig = figure(
        name="backtest_plot",
        sizing_mode="scale_width",
        tools="xpan,reset,xwheel_zoom,undo,redo,save",  # crosshair
        active_drag="xpan",
        active_scroll="xwheel_zoom",
        x_axis_type="datetime",
        width=int(width * width_scale),
        height=int(height * height_scale),
        output_backend="webgl",
    )

    if not ("split_dict" in plot_params and len(plot_params["split_dict"].keys()) > 0):
        res_col = add_total(
            fig,
            source_df,
            plot_params,
            side_arr=["merge_total", "long_total", "short_total"],
        )
    else:
        split_dict = plot_params["split_dict"]
        train_stop = split_dict["train_stop"]
        valid_start = split_dict["valid_start"]
        valid_stop = split_dict["valid_stop"]
        test_start = split_dict["test_start"]
        test_stop = split_dict["test_stop"]

        # source = ColumnDataSource(data=df_dict)

        if plot_params.get("span_mode", True):
            res_col = add_total(
                fig,
                source_df,
                plot_params,
                side_arr=["merge_total", "long_total", "short_total"],
            )
            dst_end = Span(
                location=train_stop,
                dimension="height",
                line_color="green",
                line_width=6,
                line_alpha=0.6,
            )
            fig.add_layout(dst_end)

            dst_end = Span(
                location=valid_stop,
                dimension="height",
                line_color="green",
                line_width=6,
                line_alpha=0.6,
            )
            fig.add_layout(dst_end)
        else:

            source_valid = df_dict["source_valid"]
            source_test = df_dict["source_test"]
            res_col = add_total(fig, source_df, plot_params, side_arr=["merge_total"])

            # source = ColumnDataSource(data=df_dict[valid_start:valid_stop])

            fig.line(
                "index",
                "merge_total",
                source=source_valid,
                line_width=2.5,
                line_alpha=1,
                line_color="orange",
                visible=True,
            )

            # source = ColumnDataSource(data=df_dict[test_start:test_stop])
            fig.line(
                "index",
                "merge_total",
                source=source_test,
                line_width=3,
                line_alpha=1,
                line_color="yellow",
                visible=True,
            )
    return [fig, res_col]


def total_line(
    arr,
    plot_config,
    width=800,
    height=450,
    plot_params=None,
):

    for i in plot_config:
        if i["name"] == "backtest":
            height_scale = i["height_scale"]
            fig = figure(
                name="total_plot",
                sizing_mode="scale_width",
                tools="xpan,reset,xwheel_zoom,undo,redo,save",  # crosshair
                active_drag="xpan",
                active_scroll="xwheel_zoom",
                x_axis_type="datetime",
                width=int(width),
                height=int(height * height_scale),
                output_backend="webgl",
            )

            color_arr = [
                "red",
                "orange",
                "yellow",
                "green",
                "cyan",
                "blue",
                "purple",
                "gray",
            ]
            for k, v in enumerate(arr):
                df = v["test_df"]
                fig.line(
                    "origin_index",
                    "merge_total",
                    source=df,
                    line_width=2,
                    line_alpha=1,
                    line_color=color_arr[k] if k < len(color_arr) else "black",
                    visible=True,
                )

            _l = []
            for k, v in enumerate(arr):
                test_start = v["split_dict"]["test_start"]
                test_stop = v["split_dict"]["test_stop"]
                _l.append(v["test_df"][test_start:test_stop])
            new_ohlcv_df = _l[0].iloc[0:0].copy()
            total = 0
            for _df in _l[:]:
                _df = _df.copy()
                _df["merge_total"] = _df["merge_total"] - _df["merge_total"].iloc[0]
                _df["merge_total"] = _df["merge_total"] + total
                new_ohlcv_df = pd.concat([new_ohlcv_df, _df], axis=0, join="outer")
                total = new_ohlcv_df.iloc[-1]["merge_total"]
            new_ohlcv_df.reset_index(inplace=True, drop=True)
            fig.line(
                "origin_index",
                "merge_total",
                source=new_ohlcv_df,
                line_width=2,
                line_alpha=1,
                line_color="black",
                visible=True,
            )

    return column([fig], sizing_mode="scale_width", width=width, height=height)


def layout_plot(
    df_dict,
    plot_config,
    width=800,
    height=450,
    plot_params=None,
):
    df = df_dict["df"]
    fig_array = []
    columns_array = []
    for i in plot_config:
        if not i["show"]:
            continue
        if i["name"] == "candle":
            _f = candlestick_plot(
                i,
                df_dict,
                width=width,
                height=height,
                height_scale=i["height_scale"],
                plot_params=plot_params,
            )
            fig_array.append(_f[0])
            columns_array.append(_f[1])
        elif i["name"] == "backtest":
            _f = backtest_plot(
                i,
                df_dict,
                width=width,
                height=height,
                height_scale=i["height_scale"],
                plot_params=plot_params,
            )
            fig_array.append(_f[0])
            columns_array.append(_f[1])
        else:
            _f = line_plot(
                i,
                df_dict,
                width=width,
                height=height,
                height_scale=i["height_scale"],
                plot_params=plot_params,
            )
            fig_array.append(_f[0])
            columns_array.append(_f[1])

    fig_first = fig_array[0]
    x_range = create_x_range(
        fig_first, df_dict, fig_array=fig_array, columns_array=columns_array
    )
    add_indicator(fig_first, df_dict, plot_params=plot_params)
    add_hover(fig_first, df_dict)

    for i in fig_array[:-1]:
        i.xaxis.visible = False

    _w = Span(dimension="width", line_dash="dashed", line_width=1)
    _h = Span(dimension="height", line_dash="dotted", line_width=1)
    for idx, fig in enumerate(fig_array):
        fig.xaxis.major_label_overrides = {
            i: date.isoformat(" ", "seconds")
            for i, date in enumerate(pd.to_datetime(df["date"]))
        }
        fig.xaxis.formatter = DatetimeTickFormatter(
            years="%d/%m/%Y %H:%M:%S",
            months="%d/%m/%Y %H:%M:%S",
            days="%d/%m/%Y %H:%M:%S",
            hours="%d/%m/%Y %H:%M:%S",
            hourmin="%d/%m/%Y %H:%M:%S",
            minutes="%d/%m/%Y %H:%M:%S",
            minsec="%d/%m/%Y %H:%M:%S",
            seconds="%d/%m/%Y %H:%M:%S",
            milliseconds="%d/%m/%Y %H:%M:%S",
            microseconds="%d/%m/%Y %H:%M:%S",
        )
        fig.x_range = x_range
        fig.add_tools(CrosshairTool(overlay=[_w, _h]))

    return column(fig_array, sizing_mode="scale_width", width=width, height=height)


def create_x_range(fig, df_dict, fig_array=[], columns_array=[]):
    source_df = df_dict["source_df"]

    common_x_range = DataRange1d(bounds=None)
    # source = ColumnDataSource(data=df_dict)
    callback = CustomJS(
        args={
            "fig": fig,
            "source": source_df,
            "fig_array": fig_array,
            "columns_array": columns_array,
        },
        code="""
    clearTimeout(window._autoscale_timeout);

    let index = source.data.index
    let start_cb_x = cb_obj.start
    let end_cb_x = cb_obj.end

    let _array=[]
    for (let i = 0; i < fig_array.length; ++i) {
        let _min = Infinity;
        let _max = -Infinity;
        let c = columns_array[i]

        if (1){
            //两种写法
            let _start=start_cb_x<0?0:parseInt(start_cb_x)
            let _end=parseInt(end_cb_x)+1
            let c_arr = c.map(i=>source.data[i].slice(_start,_end).filter(value => !isNaN(value)))
            let c_arr_max = c_arr.map(i=>Math.max(...i))
            let c_arr_min = c_arr.map(i=>Math.min(...i))
            _array.push([Math.min(...c_arr_min), Math.max(...c_arr_max)])
        }else{
            for (let i = 0; i < index.length; ++i) {
                if (start_cb_x <= index[i] && index[i] <= end_cb_x) {
                    let _n=c.map(m=>source.data[m][i]).filter(value => !isNaN(value))
                    _max = Math.max(..._n, _max);
                    _min = Math.min(..._n, _min);
                }
            }
            _array.push([_min,_max])
        }
    }


    window._autoscale_timeout = setTimeout(function() {

        // fig y scale
         for (let i = 0; i < fig_array.length; ++i) {
             let [_min,_max]=_array[i]
             let y_pad = (_max - _min) * 0.05;
             let y_range=fig_array[i].y_range
             y_range.start = _min - y_pad;
             y_range.end = _max + y_pad;
         }

        let x_pad = 5 // parseInt(index.length) * 0.05
        if (start_cb_x < -x_pad) {
            cb_obj.start = -x_pad
        }

        if (end_cb_x > index.length + x_pad) {
            cb_obj.end = index.length + x_pad
        }

        if (end_cb_x-start_cb_x <= 2){
            cb_obj.start = start_cb_x - 1
            cb_obj.end = end_cb_x + 1
        }

        console.log(cb_obj.start,cb_obj.end)
    },150); //ms

    """,
    )

    common_x_range.js_on_change("end", callback)
    return common_x_range
