import pandas as pd
import time
import json
from pathlib import Path
from trade_api.trade_api import (
    load_csv,
    save_csv,
    load_config,
    connect_api,
    get_balance,
)

period_dict = {"5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440}


def fetch_ohlcv(exchange, symbol, period, since, limit):
    new_ohlcv = exchange.fetch_ohlcv(symbol, period, since=since, limit=limit + 1)
    return new_ohlcv[:-1]


def _get_data(exchange, ohlcv_df, symbol, period, count, limit):
    print(f"get data: {limit} exist: {len(ohlcv_df)} count: {count}")
    from_ts = int(ohlcv_df.iloc[-1][0])
    new_ohlcv = fetch_ohlcv(exchange, symbol, period, since=from_ts, limit=limit)
    new_ohlcv_df = pd.DataFrame(new_ohlcv)
    new_ohlcv_df.drop(index=new_ohlcv_df.index[0], axis=0, inplace=True)
    ohlcv_df = pd.concat(
        [ohlcv_df.set_index(0), new_ohlcv_df.set_index(0)], axis=0, join="outer"
    )
    ohlcv_df.reset_index(inplace=True)
    return ohlcv_df


def get_data_count(exchange, symbol, start_date, period, count, ohlcv_df=[], wait=1):
    count = int(count)
    from_ts = exchange.parse8601(start_date)
    limit = count if count < 1000 else 1000

    if len(ohlcv_df) == 0:
        print(f"get data: {limit} exist: 0 count: {count}")
        ohlcv = fetch_ohlcv(exchange, symbol, period, since=from_ts, limit=limit)
        ohlcv_df = pd.DataFrame(ohlcv)
        time.sleep(wait)

    n = (count // limit) - (len(ohlcv_df) // limit)
    for i in range(n):
        if limit > count - len(ohlcv_df) + 1:
            continue
        _ = _get_data(exchange, ohlcv_df, symbol, period, count, limit)
        if len(_) == len(ohlcv_df):
            return ohlcv_df
        ohlcv_df = _
        time.sleep(wait)

    if len(ohlcv_df) < count:
        _ = _get_data(
            exchange, ohlcv_df, symbol, period, count, count - len(ohlcv_df) + 1
        )
        if len(_) == len(ohlcv_df):
            return ohlcv_df
        ohlcv_df = _

    duplic_df = ohlcv_df[ohlcv_df[0].duplicated()]
    assert len(duplic_df) == 0, f"有重复项\n{duplic_df}"

    return ohlcv_df


def get_data_latest(
    exchange,
    symbol,
    start_date,
    period,
    ohlcv_df=[],
    limit=1000,
    wait=1,
):
    count = "latest"

    if len(ohlcv_df) == 0:
        print(f"get data: {limit} exist: 0 count: latest")
        from_ts = exchange.parse8601(start_date)
        ohlcv = fetch_ohlcv(exchange, symbol, period, since=from_ts, limit=limit)
        ohlcv_df = pd.DataFrame(ohlcv)
        time.sleep(wait)

    while 1:
        last_start = ohlcv_df.iloc[-1][0]
        ohlcv_df = _get_data(exchange, ohlcv_df, symbol, period, count, 3)
        start = ohlcv_df.iloc[-1][0]
        if start == last_start:
            return ohlcv_df

        time.sleep(2)

        last_start = ohlcv_df.iloc[-1][0]
        ohlcv_df = _get_data(exchange, ohlcv_df, symbol, period, count, 3)
        start = ohlcv_df.iloc[-1][0]
        if start == last_start:
            return ohlcv_df

        time.sleep(2)

        last_start = ohlcv_df.iloc[-1][0]
        ohlcv_df = _get_data(
            exchange, ohlcv_df, symbol, period, count=count, limit=limit
        )
        start = ohlcv_df.iloc[-1][0]
        if start == last_start:
            return ohlcv_df

        time.sleep(2)


def test_data(df, config, strategy_params):
    if len(df) == 0:
        return
    period = strategy_params["period"]

    # 测试时间间隔是否一致, 需要时间连续, 如果存在市场放假就不能这样写了
    s = df[0] - df[0].shift()
    s = s == s.shift()
    n = len(df[~s])
    assert n == 2, "检测到数据间隔不对"

    _ = (df[0].iloc[-1] - df[0].iloc[0]) / (len(df[0]) - 1)
    assert _ == period_dict[period] * 60 * 1000, "发现数据间隔不对"


def test_connect_api(config, strategy_params, sleep=30):
    try:
        exchange = connect_api(config, strategy_params)
        balance_obj = get_balance(exchange)
        print(balance_obj["total"])  # 总资产数量

        print("USDT", balance_obj.get("USDT", {}))
        # print("BTC", balance_obj.get("BTC", {}))
        # print("ETH", balance_obj.get("ETH", {}))
        # print("DOGE", balance_obj.get("DOGE", {}))
        return exchange
    except Exception as e:
        print(e)
        print("sleep...", sleep)
        time.sleep(sleep)
        raise RuntimeError(e)


def handle_data(
    config,
    df,
    count_mode,
    strategy_params,
):
    if count_mode and "count" in strategy_params:
        df = (df[: strategy_params["count"]]).copy()

    test_data(df, config, strategy_params)
    init_data(df)
    return df


def get_data_wapper(
    strategy_params,
    exchange=None,
    count_mode=True,
    config_path="src/strategy/config.json",
    csv_dir="src/csv",
):
    """
    mode: 如果为count, 从指定时间开始, 获取指定数量 如果为latest, 从指定时间开始, 获取到最新K线
    """

    _name = strategy_params["exchange_name"]
    _mode = strategy_params["mode"]
    _type = strategy_params["type"]
    _account = strategy_params["account"]
    symbol = strategy_params["symbol"]
    start_date = (
        strategy_params["count_start_date"]
        if count_mode
        else strategy_params["latest_start_date"]
    )
    period = strategy_params["period"]
    count = strategy_params["count"]
    csv_path = f"{csv_dir}/{symbol.replace('/', '_')}/{_type} {_mode}/{period}/{start_date.replace(':', '_')}.csv"

    csv_df = load_csv(csv_path)
    print(f"load csv: {len(csv_df)}")

    config = load_config(config_path)

    if count_mode:
        if len(csv_df) >= count:
            csv_df = handle_data(config, csv_df, count_mode, strategy_params)
            return [csv_df, None, csv_path]

        if not exchange:
            exchange = test_connect_api(config, strategy_params)

        ohlcv_df = get_data_count(
            exchange=exchange,
            symbol=symbol,
            start_date=start_date,
            period=period,
            count=count,
            ohlcv_df=csv_df,
        )
        save_csv(csv_path, ohlcv_df)

        ohlcv_df = handle_data(config, ohlcv_df, count_mode, strategy_params)
        return [ohlcv_df, exchange, csv_path]
    else:
        if not exchange:
            exchange = test_connect_api(config, strategy_params)

        ohlcv_df = get_data_latest(
            exchange=exchange,
            symbol=symbol,
            start_date=start_date,
            period=period,
            ohlcv_df=csv_df,
        )
        save_csv(csv_path, ohlcv_df)

        ohlcv_df = handle_data(config, ohlcv_df, count_mode, strategy_params)
        return [ohlcv_df, exchange, csv_path]


def get_split_idx(length, ratio=0.2):
    num = int(length * ratio)
    return {
        "df_start": 0,
        "df_stop": length,
        "train_start": 0,
        "train_stop": length - num * 2,
        "valid_start": length - num * 2,
        "valid_stop": length - num * 1,
        "test_start": length - num * 1,
        "test_stop": length,
    }


def init_data(df):
    df.rename(
        columns={
            0: "time",
            1: "open",
            2: "high",
            3: "low",
            4: "close",
            5: "volume",
        },
        inplace=True,
    )

    df["date"] = pd.to_datetime(df["time"], unit="ms", utc=True)
    # df.iloc[df.index, "date"] = pd.to_datetime(df["time"], unit="ms", utc=True)

    df["date"] = df["date"].dt.tz_convert("Asia/Shanghai")
    # df.iloc[df.index, "date"] = df["date"].dt.tz_convert("Asia/Shanghai")
    return df
