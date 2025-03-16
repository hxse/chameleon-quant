import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime
import time

# 全局变量：高度比例（比例和为 1）
HEIGHT_SCALE_ARR = [
    [0.75, 0.25],  # 2 个子图
    [0.6, 0.2, 0.2],  # 3 个子图
    [0.5, 0.15, 0.15, 0.2],  # 4 个子图
    [0.5, 0.1, 0.1, 0.1, 0.2],  # 5 个子图
    [0.4, 0.1, 0.1, 0.1, 0.1, 0.2],  # 6 个子图
]

# 初始化防抖时间
last_update_time = 0


# 生成更真实的 K 线数据
def generate_kline_data(
    n=10000, start_date="2023-01-01", freq="min", tz="Asia/Shanghai", base_price=100
):
    time = pd.date_range(start=start_date, periods=n, freq=freq, tz=tz)
    trend_phases = np.random.choice(
        ["up", "down", "sideways"], size=n, p=[0.4, 0.4, 0.2]
    )
    trend = np.zeros(n)
    price = base_price
    volatility = np.zeros(n)
    vol_states = np.random.choice(["high", "low"], size=n, p=[0.3, 0.7])
    for i in range(n):
        if vol_states[i] == "high":
            volatility[i] = np.random.uniform(1, 3)
        else:
            volatility[i] = np.random.uniform(0.2, 0.8)
    for i in range(1, n):
        if trend_phases[i] == "up":
            trend[i] = np.random.uniform(0.1, 0.5)
        elif trend_phases[i] == "down":
            trend[i] = np.random.uniform(-0.5, -0.1)
        else:
            trend[i] = np.random.uniform(-0.1, 0.1)
        price += trend[i] + np.random.normal(0, volatility[i])
        trend[i] = price
    close = pd.Series(trend)
    close[0] = base_price
    open_price = close.shift(1, fill_value=close[0]) + np.random.uniform(-1, 1, n)
    high = np.maximum(open_price, close) + volatility
    low = np.minimum(open_price, close) - volatility
    df = pd.DataFrame(
        {
            "index": np.arange(n),
            "time": time,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
        }
    )
    df["high"] = df[["open", "close", "high"]].max(axis=1)
    df["low"] = df[["open", "close", "low"]].min(axis=1)
    df["open"] = df["open"].clip(lower=df["low"], upper=df["high"])
    df["close"] = df["close"].clip(lower=df["low"], upper=df["high"])
    return df


# 初始数据
n = 10000
data = generate_kline_data(
    n=n, start_date="2023-01-01", freq="min", tz="Asia/Shanghai", base_price=100
)


# 生成更多交易记录
def generate_positions(df, avg_interval=50):
    positions = []
    idx = 0
    while idx < len(df) - avg_interval:
        entry_idx = idx
        exit_idx = entry_idx + np.random.randint(30, 100)
        if exit_idx >= len(df):
            break
        pos_type = np.random.choice(["long", "short"])
        positions.append(
            {
                "type": pos_type,
                "entry_idx": entry_idx,
                "exit_idx": exit_idx,
                "entry_price": df["close"].iloc[entry_idx],
                "exit_price": df["close"].iloc[exit_idx],
            }
        )
        idx = exit_idx + np.random.randint(10, 50)
    return positions


positions = generate_positions(data, avg_interval=50)


# 技术指标和持仓
def update_indicators(df):
    df["ma20"] = df["close"].rolling(window=20).mean()
    df["rsi"] = 100 - (
        100
        / (
            1
            + (
                df["close"].diff().where(lambda x: x > 0, 0).rolling(14).mean()
                / -df["close"].diff().where(lambda x: x < 0, 0).rolling(14).mean()
            )
        )
    )
    df["position_profit"] = 0.0
    for pos in positions:
        profit = (
            pos["exit_price"] - pos["entry_price"]
            if pos["type"] == "long"
            else pos["entry_price"] - pos["exit_price"]
        )
        df.loc[pos["entry_idx"] : pos["exit_idx"], "position_profit"] = profit
    return df


data = update_indicators(data)

# 创建 Dash 应用
app = dash.Dash(__name__)


# 创建初始图表
def create_figure(df):
    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        row_heights=HEIGHT_SCALE_ARR[2],
        vertical_spacing=0.05,
    )

    # K 线
    fig.add_trace(
        go.Candlestick(
            x=df["index"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            increasing_line_color="#089981",
            decreasing_line_color="#f23645",
            increasing_fillcolor="#089981",
            decreasing_fillcolor="#f23645",
            line=dict(width=1),
            name="K-Line",
        ),
        row=1,
        col=1,
    )

    # MA20
    fig.add_trace(
        go.Scattergl(
            x=df["index"],
            y=df["ma20"],
            mode="lines",
            line=dict(color="blue", width=1),
            name="MA20",
        ),
        row=1,
        col=1,
    )

    # 持仓记录线（倾斜虚线）
    for pos in positions:
        color = "orange" if pos["type"] == "long" else "#AB47BC"  # 多头橙色，空头紫色
        x_values = [pos["entry_idx"], pos["exit_idx"]]
        y_values = [pos["entry_price"], pos["exit_price"]]  # 从进场价格到离场价格
        fig.add_trace(
            go.Scattergl(
                x=x_values,
                y=y_values,
                mode="lines",
                line=dict(color=color, width=5, dash="dash"),  # 虚线，宽度 5px
                name=f"{pos['type']} Position",
                showlegend=False,
            ),
            row=1,
            col=1,
        )

    # 副图
    fig.add_trace(
        go.Scattergl(
            x=df["index"],
            y=df["rsi"],
            mode="lines",
            line=dict(color="purple", width=1),
            name="RSI",
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scattergl(
            x=df["index"],
            y=df["close"].pct_change(),
            mode="lines",
            line=dict(color="gray", width=1),
            name="Returns",
        ),
        row=3,
        col=1,
    )
    fig.add_trace(
        go.Scattergl(
            x=df["index"],
            y=df["position_profit"].cumsum(),
            mode="lines",
            line=dict(color="orange", width=1),
            name="Profit",
        ),
        row=4,
        col=1,
    )

    # 布局
    fig.update_layout(
        title="K-Line Chart (Dynamic Update)",
        width=None,
        height=900,
        margin=dict(l=50, r=50, t=50, b=50),
        plot_bgcolor="#161a25",
        paper_bgcolor="#161a25",
        font=dict(color="#b2b5be"),
        grid=dict(rows=4, columns=1),
        xaxis=dict(
            title="",
            tickvals=df["index"][::100],
            ticktext=df["time"].dt.strftime("%Y-%m-%d %H:%M").iloc[::100],
            rangeslider_visible=False,
            gridcolor="#2A2E39",
            zerolinecolor="#161a25",
            showgrid=False,
        ),
        xaxis4=dict(
            title="Index",
            gridcolor="#2A2E39",
            zerolinecolor="#161a25",
            showgrid=False,
        ),
        yaxis=dict(
            gridcolor="#2A2E39", zerolinecolor="#161a25", showgrid=False, autorange=True
        ),
        yaxis2=dict(
            gridcolor="#2A2E39", zerolinecolor="#161a25", showgrid=False, autorange=True
        ),
        yaxis3=dict(
            gridcolor="#2A2E39", zerolinecolor="#161a25", showgrid=False, autorange=True
        ),
        yaxis4=dict(
            gridcolor="#2A2E39", zerolinecolor="#161a25", showgrid=False, autorange=True
        ),
        dragmode="pan",
        hovermode="x unified",
        hoverdistance=3,
        hoverlabel=dict(bgcolor="rgba(0,0,0,0.8)", font_color="#b2b5be"),
    )
    return fig


# 初始布局
app.layout = html.Div(
    [
        dcc.Graph(
            id="kline-chart",
            figure=create_figure(data),
            config={"scrollZoom": True, "displayModeBar": False},
        ),
        dcc.Interval(id="interval-component", interval=5 * 1000, n_intervals=0),
        html.Script("""
    document.addEventListener('DOMContentLoaded', function() {
        var plot = document.getElementsByClassName('plotly')[0];
        plot.on('plotly_hover', function(data) {
            var xval = data.points[0].x;
            var yval = data.points[0].y;
            var time = data.points[0].data.x[data.points[0].pointIndex];
            Plotly.relayout(plot, {
                'shapes': [
                    {type: 'line', x0: xval, x1: xval, y0: 0, y1: 1, xref: 'x', yref: 'paper',
                     line: {color: '#b2b5be', width: 1, dash: 'dot'}},
                    {type: 'line', y0: yval, y1: yval, x0: 0, x1: 1, xref: 'paper', yref: 'y',
                     line: {color: '#b2b5be', width: 1, dash: 'dot'}}
                ],
                'annotations': [
                    {x: xval, y: yval, xref: 'x', yref: 'y', text: yval.toFixed(2), showarrow: true,
                     ax: 20, ay: 0, bgcolor: '#161a25', font: {color: '#b2b5be'}},
                    {x: 0, y: yval, xref: 'paper', yref: 'y', text: yval.toFixed(2), showarrow: false,
                     xshift: -50, bgcolor: '#161a25', font: {color: '#b2b5be'}},
                    {x: xval, y: 0, xref: 'x', yref: 'paper', text: time, showarrow: false,
                     yshift: -20, font: {color: '#b2b5be'}}
                ]
            });
        });
        plot.on('plotly_unhover', function() {
            Plotly.relayout(plot, {'shapes': [], 'annotations': []});
        });
    });
    """),
    ]
)


# 生成新 K 线
def generate_new_kline(last_close, last_time):
    volatility = np.random.uniform(0.5, 3)
    trend = np.random.choice([0.2, -0.2, 0], p=[0.4, 0.4, 0.2])
    close = last_close + trend + np.random.normal(0, 2)
    open_price = last_close + np.random.uniform(-1, 1)
    high = max(open_price, close) + volatility
    low = min(open_price, close) - volatility
    return pd.DataFrame(
        {
            "index": [data["index"].iloc[-1] + 1],
            "time": [last_time + pd.Timedelta(minutes=1)],
            "open": [open_price],
            "high": [high],
            "low": [low],
            "close": [close],
        }
    )


# 自适应 Y 轴范围的通用函数
def update_y_axis_ranges(data, x_start, x_end):
    x_start = max(0, x_start)
    x_end = min(len(data) - 1, x_end)
    visible_data = data.iloc[x_start : x_end + 1]
    y_min = visible_data[["low", "ma20"]].min().min() * 0.98
    y_max = visible_data[["high", "ma20"]].max().max() * 1.02
    rsi_min = visible_data["rsi"].min() * 0.98
    rsi_max = visible_data["rsi"].max() * 1.02
    returns = visible_data["close"].pct_change()
    returns_min = returns.min() * 0.98 if not returns.empty else -0.1
    returns_max = returns.max() * 1.02 if not returns.empty else 0.1
    profit = visible_data["position_profit"].cumsum()
    profit_min = profit.min() * 0.98 if not profit.empty else 0
    profit_max = profit.max() * 1.02 if not profit.empty else 0
    return {
        "yaxis.range": [y_min, y_max],
        "yaxis2.range": [rsi_min, rsi_max],
        "yaxis3.range": [returns_min, returns_max],
        "yaxis4.range": [profit_min, profit_max],
    }


# 定时更新回调（仅追加新数据）
@app.callback(
    Output("kline-chart", "figure", allow_duplicate=True),
    [Input("interval-component", "n_intervals")],
    [State("kline-chart", "figure"), State("kline-chart", "relayoutData")],
    prevent_initial_call=True,
)
def update_chart(n_intervals, current_fig, relayout_data):
    global data
    new_row = generate_new_kline(data["close"].iloc[-1], data["time"].iloc[-1])
    data = pd.concat([data, new_row], ignore_index=True)
    data = update_indicators(data)

    fig = go.Figure(current_fig)
    fig.data[0].open = data["open"]
    fig.data[0].high = data["high"]
    fig.data[0].low = data["low"]
    fig.data[0].close = data["close"]
    fig.data[0].x = data["index"]
    fig.data[1].y = data["ma20"]

    pos_traces = len(positions)
    for i, pos in enumerate(positions):
        x_values = [pos["entry_idx"], pos["exit_idx"]]
        y_values = [pos["entry_price"], pos["exit_price"]]  # 倾斜，从进场到离场
        fig.data[2 + i].x = x_values
        fig.data[2 + i].y = y_values

    fig.data[2 + pos_traces].y = data["rsi"]
    fig.data[3 + pos_traces].y = data["close"].pct_change()
    fig.data[4 + pos_traces].y = data["position_profit"].cumsum()

    if (
        relayout_data
        and "xaxis.range[0]" in relayout_data
        and "xaxis.range[1]" in relayout_data
    ):
        x_start = int(relayout_data["xaxis.range[0]"])
        x_end = int(relayout_data["xaxis.range[1]"])
        fig.update_layout(xaxis=dict(range=[x_start, x_end]))
    else:
        x_start = max(0, len(data) - 100)
        x_end = len(data) - 1
        fig.update_layout(xaxis=dict(range=[x_start, x_end]))

    y_ranges = update_y_axis_ranges(data, x_start, x_end)
    fig.update_layout(**y_ranges)

    return fig


# 缩放/平移时立即自适应 Y 轴（添加防抖）
@app.callback(
    Output("kline-chart", "figure", allow_duplicate=True),
    [Input("kline-chart", "relayoutData")],
    [State("kline-chart", "figure")],
    prevent_initial_call=True,
)
def update_y_axis_on_zoom(relayout_data, current_fig):
    global last_update_time

    # 修正条件检查，确保 xaxis.range[0] 和 xaxis.range[1] 都存在
    if (
        not relayout_data
        or "xaxis.range[0]" not in relayout_data
        or "xaxis.range[1]" not in relayout_data
    ):
        raise dash.exceptions.PreventUpdate

    # 防抖逻辑：只在最后一次缩放后 200ms 更新
    current_time = time.time()
    if current_time - last_update_time < 0.2:  # 200ms 防抖
        raise dash.exceptions.PreventUpdate
    last_update_time = current_time

    fig = go.Figure(current_fig)
    x_start = int(relayout_data["xaxis.range[0]"])
    x_end = int(relayout_data["xaxis.range[1]"])
    y_ranges = update_y_axis_ranges(data, x_start, x_end)
    fig.update_layout(**y_ranges)
    return fig


# 运行服务器
if __name__ == "__main__":
    app.run_server(debug=True, port=5000)
