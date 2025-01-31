import typer
import time
import datetime
from zoneinfo import ZoneInfo
import numpy as np
import json
from pathlib import Path
import psutil
import sys

sys.path.append("src")


from data_api.data_api import get_data_wapper
from backtest.backtest_framework import backtest_wapper
from trade_api.trade_api import trade_api_wapper, get_ticker
from telegram_bot.telegram_bot import push_telegram_channel, save_fig_file


zone = datetime.timezone.utc
zone = ZoneInfo("Asia/Shanghai")


def reload_strategy(reload=False):
    import strategy

    if not reload:
        return strategy

    import importlib

    importlib.reload(strategy)

    for i in strategy.strategy_arr:
        importlib.reload(i[1])

    return strategy


def get_exchange_name(_name, _s):
    exchange_name = _s.strategy_params["exchange_name"]
    account = _s.strategy_params["account"]
    mode = _s.strategy_params["mode"]
    type = _s.strategy_params["type"]
    return f"{exchange_name} {type} {mode} {account}"


def iso_time(now):
    return now.replace(microsecond=0).isoformat(" ")


exchange_dict = {}


def run_strategy(signal_time, _name, _s, config_path, csv_dir):
    # count_mode = True
    count_mode = False

    period = _s.strategy_params["period"]
    account = _s.strategy_params["account"]

    if signal_time == period and _s.strategy_params.get("enable_bot", False):
        print(f"run {period} {_name} {_s}")

        exchange = exchange_dict.get(get_exchange_name(_name, _s), None)

        start_time = time.time()
        [df, exchange, csv_path] = get_data_wapper(
            strategy_params=_s.strategy_params,
            count_mode=count_mode,
            exchange=exchange,
            config_path=config_path,
            csv_dir=csv_dir,
        )
        print("get data %s second" % (time.time() - start_time))

        start_time = time.time()
        [exchange, df, result, fig, _] = backtest_wapper(
            df,
            strategy=_s.strategy,
            strategy_params=_s.strategy_params,
            optimize_mode=False,
            count_mode=count_mode,
            exchange=exchange,
        )
        print("run strategy %s second" % (time.time() - start_time))

        exchange_dict[get_exchange_name(_name, _s)] = exchange
        return [
            exchange,
            _s.strategy_params,
            df,
            result,
            fig,
            _,
            csv_path,
        ]


def run_trade_api(exchange, strategy_params, df, result, fig, config_path, fig_path):
    now = datetime.datetime.now(zone)

    exchange_name = strategy_params["exchange_name"]
    symbol = strategy_params["symbol"]

    price = get_ticker(exchange, symbol)

    long_tp = None if np.isnan(df.iloc[-1]["long_tp"]) else df.iloc[-1]["long_tp"]
    long_sl = None if np.isnan(df.iloc[-1]["long_sl"]) else df.iloc[-1]["long_sl"]
    long_tsl = None if np.isnan(df.iloc[-1]["long_tsl"]) else df.iloc[-1]["long_tsl"]

    short_tp = None if np.isnan(df.iloc[-1]["short_tp"]) else df.iloc[-1]["short_tp"]
    short_sl = None if np.isnan(df.iloc[-1]["short_sl"]) else df.iloc[-1]["short_sl"]
    short_tsl = None if np.isnan(df.iloc[-1]["short_tsl"]) else df.iloc[-1]["short_tsl"]

    print(
        f"---- long_status {df.iloc[-1]['long_status']} price {price} long_tp {long_tp} long_sl {long_sl} long_tsl {long_tsl}"
    )
    print(
        f"---- short_status {df.iloc[-1]['short_status']} price {price} short_tp {short_tp} short_sl {short_sl} short_tsl {short_tsl}"
    )
    if df.iloc[-1]["long_status"] == 1:
        message = trade_api_wapper(
            exchange,
            strategy_params,
            side=None,
            leverage=1,
            price=None,
            takeProfitPrice=None,
            stopLossParams=None,
            mode="cancel",
        )
        message = trade_api_wapper(
            exchange,
            strategy_params,
            "buy",
            leverage=1,
            price=price,
            takeProfitPrice=long_tp,
            stopLossParams=long_sl,
            mode="open",
        )
        push_telegram_channel(
            config_path,
            data={
                "date": f"{iso_time(now)}",
                "exchange_name": exchange_name,
                "symbol": symbol,
                "mode": "open",
                "side": "buy",
                "price": price,
                "long_tp": long_tp,
                "long_sl": long_sl,
                "long_tsl": long_tsl,
                "message": message,
            },
            fig=fig,
            fig_path=fig_path,
        )
    if df.iloc[-1]["short_status"] == 1:
        message = trade_api_wapper(
            exchange,
            strategy_params,
            side=None,
            leverage=1,
            price=None,
            takeProfitPrice=None,
            stopLossParams=None,
            mode="cancel",
        )
        message = trade_api_wapper(
            exchange,
            strategy_params,
            "sell",
            leverage=1,
            price=price,
            takeProfitPrice=short_tp,
            stopLossParams=short_sl,
            mode="open",
        )
        push_telegram_channel(
            config_path,
            data={
                "date": f"{iso_time(now)}",
                "exchange_name": exchange_name,
                "symbol": symbol,
                "mode": "open",
                "side": "sell",
                "price": price,
                "short_tp": short_tp,
                "short_sl": short_sl,
                "short_tsl": short_tsl,
                "message": message,
            },
            fig=fig,
            fig_path=fig_path,
        )
    if df.iloc[-1]["long_status"] == 0:
        message = trade_api_wapper(
            exchange,
            strategy_params,
            side=None,
            leverage=1,
            price=None,
            takeProfitPrice=None,
            stopLossParams=None,
            mode="close",
        )
        message = trade_api_wapper(
            exchange,
            strategy_params,
            side=None,
            leverage=1,
            price=None,
            takeProfitPrice=None,
            stopLossParams=None,
            mode="cancel",
        )
        push_telegram_channel(
            config_path,
            data={
                "date": f"{iso_time(now)}",
                "exchange_name": exchange_name,
                "symbol": symbol,
                "mode": "long_close",
                "price": price,
                "message": message,
            },
            fig=fig,
            fig_path=fig_path,
        )
    if df.iloc[-1]["short_status"] == 0:
        message = trade_api_wapper(
            exchange,
            strategy_params,
            side=None,
            leverage=1,
            price=None,
            takeProfitPrice=None,
            stopLossParams=None,
            mode="close",
        )
        message = trade_api_wapper(
            exchange,
            strategy_params,
            side=None,
            leverage=1,
            price=None,
            takeProfitPrice=None,
            stopLossParams=None,
            mode="cancel",
        )
        push_telegram_channel(
            config_path,
            data={
                "date": f"{iso_time(now)}",
                "exchange_name": exchange_name,
                "symbol": symbol,
                "mode": "short_close",
                "price": price,
                "message": message,
            },
            fig=fig,
            fig_path=fig_path,
        )


def callback(_p, strategy, config_path, csv_dir):
    for [_name, _s] in strategy.strategy_arr:
        res = run_strategy(_p, _name, _s, config_path, csv_dir)
        if res is not None:
            [
                exchange,
                strategy_params,
                df,
                result,
                fig,
                _,
                csv_path,
            ] = res
            fig_path = save_fig_file(fig, config_path, csv_path)
            run_trade_api(
                exchange, strategy_params, df, result, fig, config_path, fig_path
            )
            del df, fig


def init_log(path):
    data = {
        "last_minute_5": None,
        "last_minute_15": None,
        "last_minute_30": None,
        "last_hour_1": None,
        "last_hour_4": None,
        "last_day_1": None,
    }
    dump_log(path, data)
    return data


def dump_log(path, data):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def load_log(path):
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)
        return data


def loop_time(
    zone=zone,
    delay=10,
    config_path="src/strategy/config",
    csv_dir="src/csv",
    reload=False,
):
    log_path = Path(config_path).parent / "log.json"
    if Path(log_path).is_file():
        log_data = load_log(log_path)
    else:
        log_data = init_log(log_path)

    while 1:
        try:
            strategy = reload_strategy(reload=reload)
        except SyntaxError as e:
            print(e)
            time.sleep(delay)
            continue

        try:
            strategy.strategy_arr
        except AttributeError as e:
            print(e)
            time.sleep(delay)
            continue

        now = datetime.datetime.now(zone)

        if (
            now.second >= delay
            and now.minute % 5 == 0
            and log_data["last_minute_5"] != now.minute
        ):  # 测试时改成1, 测试完了改成5
            log_data["last_minute_5"] = now.minute
            print(iso_time(now), "last_minute_5")
            callback("5m", strategy, config_path, csv_dir)
            dump_log(log_path, log_data)
            get_memory()
        if (
            now.second >= delay
            and now.minute % 15 == 0
            and log_data["last_minute_15"] != now.minute
        ):
            log_data["last_minute_15"] = now.minute
            print(iso_time(now), "last_minute_15")
            callback("15m", strategy, config_path, csv_dir)
            dump_log(log_path, log_data)
            get_memory()
        if (
            now.second >= delay
            and now.minute % 30 == 0
            and log_data["last_minute_30"] != now.minute
        ):
            log_data["last_minute_30"] = now.minute
            print(iso_time(now), "last_minute_30")
            callback("30m", strategy, config_path, csv_dir)
            dump_log(log_path, log_data)
            get_memory()
        if (
            now.second >= delay
            and now.hour % 1 == 0
            and log_data["last_hour_1"] != now.hour
        ):
            log_data["last_hour_1"] = now.hour
            print(iso_time(now), "last_hour_1")
            callback("1h", strategy, config_path, csv_dir)
            dump_log(log_path, log_data)
            get_memory()
        if (
            now.second >= delay
            and now.hour % 4 == 0
            and log_data["last_hour_4"] != now.hour
        ):
            log_data["last_hour_4"] = now.hour
            print(iso_time(now), "last_hour_4")
            callback("4h", strategy, config_path, csv_dir)
            dump_log(log_path, log_data)
            get_memory()
        if (
            now.second >= delay
            and now.day % 1 == 0
            and log_data["last_day_1"] != now.day
        ):
            log_data["last_day_1"] = now.day
            print(iso_time(now), "last_day")
            callback("1d", strategy, config_path, csv_dir)
            dump_log(log_path, log_data)
            get_memory()

        time.sleep(delay)


def get_memory():
    process = psutil.Process()
    rss = process.memory_info().rss
    print(f"memory: {rss / 1024 / 1024} M")
    return rss


def main(config_path="src/strategy/config.json", csv_dir="src/csv", reload=False):
    get_memory()
    now = datetime.datetime.now(zone)
    print(f"{iso_time(now)} run trading_robot")
    loop_time(config_path=config_path, csv_dir=csv_dir, reload=reload)


if __name__ == "__main__":
    app = typer.Typer(pretty_exceptions_show_locals=False)
    app.command(help="also ma")(main)
    app.command("ma", hidden=True)(main)
    app()
