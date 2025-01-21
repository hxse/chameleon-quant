import pandas as pd
from bokeh.plotting import figure, show
from bokeh.models import (
    CustomJS,
    ColumnDataSource,
    HoverTool,
    DatetimeTickFormatter,
    CrosshairTool,
    Span,
)
from bokeh.io import output_notebook
import numpy as np
from bokeh.layouts import gridplot, column
from bokeh.models.ranges import DataRange1d


def add_indicator(fig, df, plot_params=None):
    df["_long_price"] = df["long_price"]
    df.loc[df["long_status"] == 2, "_long_price"] = np.nan
    df["_long_price"] = df["_long_price"].interpolate(method="linear")
    df.loc[df["long_status"] == -1, "_long_price"] = np.nan

    df["_short_price"] = df["short_price"]
    df.loc[df["short_status"] == 2, "_short_price"] = np.nan
    df["_short_price"] = df["_short_price"].interpolate(method="linear")
    df.loc[df["short_status"] == -1, "_short_price"] = np.nan

    # inc = df.close > df.open
    # dec = ~inc

    source = ColumnDataSource(data=df)
    # source_inc = ColumnDataSource(data=df[inc])
    # source_dec = ColumnDataSource(data=df[dec])

    df.drop(["_long_price"], axis=1, inplace=True)
    df.drop(["_short_price"], axis=1, inplace=True)

    color = ["orange", "green", "blue", "purple", "grey"]
    for k, v in enumerate([i for i in df.columns if "sma" in i]):
        fig.line(
            "index",
            v,
            source=source,
            line_width=2,
            line_alpha=1,
            line_color=color[k] if k < len(color) else color[len(color) - 1],
            visible=True,
        )

    # 仓位菱形线
    fig.line(
        "index",
        "_long_price",
        source=source,
        line_width=12,
        line_alpha=0.7,
        line_color="orange",
        visible=True,
        line_dash="dotted",
    )

    # 仓位菱形线
    fig.line(
        "index",
        "_short_price",
        source=source,
        line_width=12,
        line_alpha=0.7,
        line_color="purple",
        visible=True,
        line_dash="dotted",
    )

    # 仓位止损线
    fig.line(
        "index",
        "long_sl",
        source=source,
        line_width=4,
        line_alpha=1,
        line_color="orange",
        visible=True,
        line_dash="dotted",
    )

    # 仓位止损线
    fig.line(
        "index",
        "short_sl",
        source=source,
        line_width=4,
        line_alpha=1,
        line_color="purple",
        visible=True,
        line_dash="dotted",
    )

    # 仓位止盈线
    fig.line(
        "index",
        "long_tp",
        source=source,
        line_width=4,
        line_alpha=1,
        line_color="orange",
        visible=True,
        line_dash="dotted",
    )

    # 仓位止盈线
    fig.line(
        "index",
        "short_tp",
        source=source,
        line_width=4,
        line_alpha=1,
        line_color="purple",
        visible=True,
        line_dash="dotted",
    )

    # 仓位追踪止损线
    fig.line(
        "index",
        "long_tsl",
        source=source,
        line_width=4,
        line_alpha=1,
        line_color="orange",
        visible=True,
        line_dash="dashed",
    )

    # 仓位追踪止损线
    fig.line(
        "index",
        "short_tsl",
        source=source,
        line_width=4,
        line_alpha=1,
        line_color="purple",
        visible=True,
        line_dash="dashed",
    )

    if "test_index_start" in plot_params and plot_params["test_index_start"]:
        dst_end = Span(
            location=plot_params["test_index_start"],
            dimension="height",
            line_color="green",
            line_width=6,
            line_alpha=0.6,
        )
        fig.add_layout(dst_end)


def add_hover(fig, df):
    source = ColumnDataSource(data=df)
    close_line = fig.line(
        "index", "close", source=source, line_width=2, line_alpha=0, visible=True
    )

    # hovertool 没有办法调整时区 https://github.com/bokeh/bokeh/issues/1135
    hover = HoverTool(
        renderers=[close_line],
        tooltips=[
            ("y", "$y"),
            ("index", "@index"),
            ("date", "@date{%Y-%m-%d %H:%M:%S %z}"),
            ("open", "@open"),
            ("high", "@high"),
            ("low", "@low"),
            ("close", "@close"),
            ("atr", "@atr"),
            ("merge_diff", "@merge_diff"),
            ("merge_total", "@merge_total"),
        ],
        formatters={"@date": "datetime"},
        mode="vline",
        point_policy="follow_mouse",
    )
    fig.add_tools(hover)


def candlestick_plot(df, width=800, height=400, width_scale=1, height_scale=0.75):
    """
    DataFrame 参考格式:
        date	open	high	low	close	volume
    0	2000-03-01	89.62	94.09	88.94	90.81	106889800
    1	2000-03-02	91.81	95.37	91.12	93.37	106932600
    2	2000-03-03	94.75	98.87	93.87	96.12	101435200
    """

    fig = figure(
        sizing_mode="scale_width",
        tools="xpan,xwheel_zoom,undo,redo,reset,save",  # crosshair
        active_drag="xpan",
        active_scroll="xwheel_zoom",
        x_axis_type="datetime",
        width=int(width * width_scale),
        height=int(height * height_scale),
    )

    inc = df.close > df.open
    dec = ~inc

    source = ColumnDataSource(data=df)
    source_inc = ColumnDataSource(data=df[inc])
    source_dec = ColumnDataSource(data=df[dec])

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
    width_vbar = 0.65
    bar_inc = fig.vbar(
        "index",
        width_vbar,
        "open",
        "close",
        color="green",
        source=source_inc,
    )
    bar_dec = fig.vbar(
        "index",
        width_vbar,
        "open",
        "close",
        color="red",
        source=source_dec,
    )

    return fig


def line_plot(
    df, width=800, height=400, width_scale=1, height_scale=0.25, plot_params=None
):
    fig = figure(
        sizing_mode="scale_width",
        tools="xpan,xwheel_zoom,undo,redo,reset,save",  # crosshair
        active_drag="xpan",
        active_scroll="xwheel_zoom",
        x_axis_type="datetime",
        width=int(width * width_scale),
        height=int(height * height_scale),
    )

    if (
        plot_params
        and "long_count" in plot_params
        and plot_params["long_count"] > 0
        and "short_count" in plot_params
        and plot_params["short_count"] > 0
    ):
        fig.line(
            "index",
            "merge_total",
            source=df,
            line_width=2,
            line_alpha=1,
            line_color="black",
            visible=True,
        )
    if plot_params and "long_count" in plot_params and plot_params["long_count"] > 0:
        fig.line(
            "index",
            "long_total",
            source=df,
            line_width=2,
            line_alpha=1,
            line_color="green",
            visible=True,
        )
    if plot_params and "short_count" in plot_params and plot_params["short_count"] > 0:
        fig.line(
            "index",
            "short_total",
            source=df,
            line_width=2,
            line_alpha=1,
            line_color="red",
            visible=True,
        )

    return fig


def layout_plot(
    df,
    plot_config,
    width=800,
    height=450,
    plot_params=None,
):
    fig_array = []
    for i in plot_config:
        if not i["show"]:
            continue
        if i["name"] == "candle":
            fig = candlestick_plot(
                df,
                width=width,
                height=height,
                height_scale=i["height_scale"],
            )
        else:
            fig = line_plot(
                df,
                width=width,
                height=height,
                height_scale=i["height_scale"],
                plot_params=plot_params,
            )
        fig_array.append(fig)

    fig_first = fig_array[0]
    x_range = create_x_range(fig_first, df, line_figs=fig_array[1:])
    add_indicator(fig_first, df, plot_params=plot_params)
    add_hover(fig_first, df)

    if len(fig_array) > 1:
        fig_first.xaxis.visible = False

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


def create_x_range(fig, df, line_figs=[]):
    common_x_range = DataRange1d(bounds=None)
    source = ColumnDataSource(data=df)
    callback = CustomJS(
        args={
            "fig": fig,
            "source": source,
            "line_figs": line_figs,
        },
        code="""
    clearTimeout(window._autoscale_timeout);

    let index = source.data.index,
    low = source.data.low,
    high = source.data.high,
    long_total = source.data.long_total,
    short_total = source.data.short_total,
    merge_total = source.data.merge_total,
    start = cb_obj.start,
    end = cb_obj.end,
    min = Infinity,
    max = -Infinity;

    for (let i = 0; i < index.length; ++i) {
        if (start <= index[i] && index[i] <= end) {
            max = Math.max(high[i], max);
            min = Math.min(low[i], min);
        }
    }
    let _array=[]
    for (let i = 0; i < line_figs.length; ++i) {
        let _min = Infinity;
        let _max = -Infinity;
        for (let i = 0; i < index.length; ++i) {
            if (start <= index[i] && index[i] <= end) {
                _max = Math.max(long_total[i], short_total[i], merge_total[i], _max);
                _min = Math.min(long_total[i], short_total[i], merge_total[i], _min);
            }
        }
        _array.push([_min,_max])
    }

    let y_pad = (max - min) * 0.05;

    window._autoscale_timeout = setTimeout(function() {

        fig.y_range.start = min - y_pad;
        fig.y_range.end = max + y_pad;

        let x_pad = 5 // parseInt(index.length) * 0.05
        if (start < -x_pad) {
            cb_obj.start = -x_pad
        }

        if (end > index.length + x_pad) {
            cb_obj.end = index.length + x_pad
        }

        if (end-start <= 2){
            cb_obj.start = start - 1
            cb_obj.end = end + 1
        }

        // line fig scale
        for (let i = 0; i < line_figs.length; ++i) {
            let [_min,_max]=_array[i]
            let y_range=line_figs[i].y_range
            y_range.start = _min - y_pad;
            y_range.end = _max + y_pad;
        }

        console.log(cb_obj.start,cb_obj.end)
    },150); //ms

    """,
    )

    common_x_range.js_on_change("end", callback)
    return common_x_range
