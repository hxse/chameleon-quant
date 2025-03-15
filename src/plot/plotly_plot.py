import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np


def get_df_dict(df, plot_params={}):
    """生成 Plotly 所需的数据字典，适配参考数据"""
    df = df.copy()
    df["left"] = df.index.astype(np.float64) - 0.4
    df["right"] = df.index.astype(np.float64) + 0.4
    _df = df[["time", "date", "open", "high", "low", "close", "left", "right"]]

    # 分离上涨和下跌 K 线数据
    df_inc = _df[df["close"] > _df["open"]].copy()
    df_dec = _df[df["close"] <= _df["open"]].copy()

    # 处理回测相关的价格数据
    df = process_backtest_data(df)

    # 处理分段数据（如果有 split_dict）
    split_data = {}
    if "split_dict" in plot_params and plot_params["split_dict"]:
        split_dict = plot_params["split_dict"]
        split_data["valid"] = df.iloc[
            split_dict["valid_start"] : split_dict["valid_stop"]
        ]
        split_data["test"] = df.iloc[split_dict["test_start"] : split_dict["test_stop"]]

    # 清理临时列
    df.drop(["left", "right"], axis=1, inplace=True)

    return {"df": df, "df_inc": df_inc, "df_dec": df_dec, "split_data": split_data}


def process_backtest_data(df):
    """处理回测相关数据，适配参考数据的字段"""
    df = df.copy()

    # Long 和 Short 价格插值
    df["_long_price"] = (
        df["long_price"].where(df["long_status"] != 2).interpolate(method="linear")
    )
    df["_long_price"] = df["_long_price"].where(df["long_status"] != -1)
    df["_short_price"] = (
        df["short_price"].where(df["short_status"] != 2).interpolate(method="linear")
    )
    df["_short_price"] = df["_short_price"].where(df["short_status"] != -1)

    # 分奇偶绘制
    for target, origin, idx2, mode in [
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
    ]:
        df[target] = np.where(df[idx2] % 2 == mode, df[origin], np.nan)

    return df


def candlestick_plot(df_dict, height_scale=0.6, width=800, plot_params=None):
    """绘制 K 线图"""
    df = df_dict["df"]
    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=df["date"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Candlestick",
            increasing_line_color="green",
            decreasing_line_color="red",
        )
    )

    # 添加回测价格线
    add_backtest_lines(fig, df_dict, plot_params)

    return fig, ["high", "low"]


def add_backtest_lines(fig, df_dict, plot_params=None):
    """添加回测相关的价格线（如 long_price, short_price）"""
    df = df_dict["df"]
    for col, color, dash in [
        ("long_price_even", "orange", "dot"),
        ("long_price_odd", "orange", "dot"),
        ("short_price_even", "purple", "dot"),
        ("short_price_odd", "purple", "dot"),
        ("long_sl_even", "orange", "dash"),
        ("long_sl_odd", "orange", "dash"),
        ("short_sl_even", "purple", "dash"),
        ("short_sl_odd", "purple", "dash"),
        ("long_tp_even", "orange", "dashdot"),
        ("long_tp_odd", "orange", "dashdot"),
        ("short_tp_even", "purple", "dashdot"),
        ("short_tp_odd", "purple", "dashdot"),
        ("long_tsl_even", "orange", "solid"),
        ("long_tsl_odd", "orange", "solid"),
        ("short_tsl_even", "purple", "solid"),
        ("short_tsl_odd", "purple", "solid"),
    ]:
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df[col],
                mode="lines",
                name=col,
                line=dict(color=color, width=2, dash=dash),
            )
        )


def indicator_plot(
    plot_config_item, df_dict, height_scale=0.2, width=800, plot_params=None
):
    """绘制指标图（如 ATR）"""
    df = df_dict["df"]
    fig = go.Figure()
    colors = ["blue", "orange", "green", "purple", "grey"]
    key_cols = [
        col for col in df.columns if any(k in col for k in plot_config_item["key"])
    ]

    for i, col in enumerate(key_cols):
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df[col],
                mode="lines",
                name=col,
                line=dict(color=colors[min(i, len(colors) - 1)], width=2),
            )
        )

    return fig, key_cols


def backtest_plot(df_dict, height_scale=0.2, width=800, plot_params=None):
    """绘制回测结果图（如 merge_total）"""
    df = df_dict["df"]
    fig = go.Figure()

    if "split_dict" not in plot_params or not plot_params["split_dict"]:
        add_total(fig, df, plot_params)
    else:
        split_dict = plot_params["split_dict"]
        if plot_params.get("span_mode", True):
            add_total(fig, df, plot_params)
            for loc, color in [
                (split_dict["train_stop"], "green"),
                (split_dict["valid_stop"], "green"),
            ]:
                fig.add_vline(
                    x=df["date"].iloc[loc], line=dict(color=color, width=2, dash="dash")
                )
        else:
            valid_df = df_dict["split_data"]["valid"]
            test_df = df_dict["split_data"]["test"]
            fig.add_trace(
                go.Scatter(
                    x=df["date"],
                    y=df["merge_total"],
                    mode="lines",
                    name="Total",
                    line=dict(color="black", width=2),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=valid_df["date"],
                    y=valid_df["merge_total"],
                    mode="lines",
                    name="Valid",
                    line=dict(color="orange", width=2.5),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=test_df["date"],
                    y=test_df["merge_total"],
                    mode="lines",
                    name="Test",
                    line=dict(color="yellow", width=3),
                )
            )

    return fig, ["merge_total"]


def add_total(
    fig, df, plot_params, side_arr=["merge_total", "long_total", "short_total"]
):
    """添加回测总收益曲线"""
    if "merge_total" in side_arr:
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["merge_total"],
                mode="lines",
                name="Merge Total",
                line=dict(color="black", width=2),
            )
        )
    if "long_total" in side_arr:
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["long_total"],
                mode="lines",
                name="Long Total",
                line=dict(color="orange", width=2),
            )
        )
    if "short_total" in side_arr:
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["short_total"],
                mode="lines",
                name="Short Total",
                line=dict(color="purple", width=2),
            )
        )
    if "enable_hold" in plot_params and "long" in plot_params["enable_hold"]:
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["long_hold"],
                mode="lines",
                name="Long Hold",
                line=dict(color="orange", width=1, dash="dash"),
            )
        )
    if "enable_hold" in plot_params and "short" in plot_params["enable_hold"]:
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["short_hold"],
                mode="lines",
                name="Short Hold",
                line=dict(color="purple", width=1, dash="dash"),
            )
        )


def layout_plot(df_dict, plot_config, width=800, height=600, plot_params=None):
    """组合多子图布局"""
    fig = make_subplots(
        rows=len(plot_config),
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[item["height_scale"] for item in plot_config],
    )

    for i, item in enumerate(plot_config, 1):
        if not item["show"]:
            continue
        if item["name"] == "candle":
            sub_fig, _ = candlestick_plot(
                df_dict, item["height_scale"], width, plot_params
            )
        elif item["name"] == "backtest":
            sub_fig, _ = backtest_plot(
                df_dict, item["height_scale"], width, plot_params
            )
        else:
            sub_fig, _ = indicator_plot(
                item, df_dict, item["height_scale"], width, plot_params
            )

        for trace in sub_fig.data:
            fig.add_trace(trace, row=i, col=1)

    fig.update_layout(
        width=width,
        height=height,
        showlegend=True,
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        template="plotly_white",
        title="Trading Visualization",
        dragmode="pan",  # 默认拖动模式
        yaxis=dict(autorange=True),  # Y 轴自动调整
    )
    fig.update_xaxes(rangemode="normal", matches="x")
    return fig


if __name__ == "__main__":
    # 加载参考数据
    df = pd.read_csv("src/plot/test.csv")  # 假设数据保存为 CSV 文件
    df["date"] = pd.to_datetime(df["date"])

    # 配置绘图参数
    plot_config = [
        {"name": "candle", "show": True, "height_scale": 0.6},
        {"name": "atr", "key": ["atr"], "show": True, "height_scale": 0.2},
        {"name": "backtest", "show": True, "height_scale": 0.2},
    ]
    plot_params = {
        "long_count": 5,
        "short_count": 3,
        "split_dict": {
            "train_stop": 200,
            "valid_start": 200,
            "valid_stop": 400,
            "test_start": 400,
            "test_stop": len(df),
        },
        "span_mode": True,
        "enable_hold": ["long", "short"],
    }

    # 生成图表
    df_dict = get_df_dict(df, plot_params)
    fig = layout_plot(df_dict, plot_config, plot_params=plot_params)
    fig.show()
