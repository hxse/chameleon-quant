import pandas as pd
import json
from pathlib import Path
import ccxt


amount_dict = {
    "binance": {
        "BTC/USDT": {"minimum": 0.002, "round": 3},
        "ETH/USDT": {"minimum": 0.006, "round": 3},
        "DOGE/USDT": {"minimum": 14, "round": 0},
        "XRP/USDT": {"minimum": 1.8, "round": 1},
    }
}


def load_config(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        config = json.load(file)
        return config


def save_csv(file_path, ohlcv_df):
    filepath = Path(file_path)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    df = ohlcv_df[ohlcv_df.columns[[0, 1, 2, 3, 4, 5]]]
    df.to_csv(file_path, index=False)


def load_csv(file_path):
    if Path(file_path).is_file():
        return pd.read_csv(file_path).rename(
            columns={"0": 0, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5}
        )
    d = {0: [], 1: [], 2: [], 3: [], 4: [], 5: []}
    return pd.DataFrame(data=d)


def connect_api(config, params):
    # https://testnet.binancefuture.com/en/futures/BTCUSDT
    exchange_name = params["exchange_name"]
    mode = params["mode"]
    _type = params["type"]
    account = params["account"]

    apiKey = config[exchange_name][mode][_type][account]["apiKey"]
    secret = config[exchange_name][mode][_type][account]["secret"]
    password = (
        config.get(exchange_name, {}).get(mode, {}).get(_type, {}).get("password", None)
    )

    exchange = None

    http_proxy = config[exchange_name]["proxy"].get("http", None)
    https_proxy = config[exchange_name]["proxy"].get("https", None)
    if exchange_name == "binance":
        exchange = ccxt.binance(
            {
                "apiKey": apiKey,
                "secret": secret,
                "options": {"defaultType": _type},
                "proxies": {
                    "http": http_proxy,
                    "https": https_proxy,
                },
            }
        )

    if exchange_name == "kraken":
        if _type == "spot":
            exchange = ccxt.kraken(
                {"apiKey": apiKey, "secret": secret, "options": {"defaultType": _type}}
            )
        if _type == "future":
            exchange = ccxt.krakenfutures(
                {"apiKey": apiKey, "secret": secret, "options": {"defaultType": _type}}
            )
    if exchange_name == "okx":
        exchange = ccxt.okx(
            {
                "apiKey": apiKey,
                "secret": secret,
                "password": password,
                "options": {"defaultType": _type},
            }
        )

    if mode == "test":
        exchange.set_sandbox_mode(True)
    return exchange


def get_balance(exchange):
    balance_obj = exchange.fetch_balance()
    return balance_obj


def get_ticker(exchange, symbol):
    price = exchange.fetch_ticker(symbol)
    try:
        price = float(price["info"]["lastPrice"])
    except KeyError:
        price = float(price["info"]["last"])
    return price


def get_amount(exchange_name, symbol, price, size, leverage):
    amount = size * leverage / price

    minimum = amount_dict[exchange_name][symbol]["minimum"]
    _round = amount_dict[exchange_name][symbol]["round"]

    if amount >= 1:
        amount = round(amount, _round)
    elif amount < 1 and amount >= minimum:
        amount = round(amount, _round)
    else:
        amount = minimum
    return amount


def create_order(exchange, symbol, side, amount):
    params = {}
    buy_order = exchange.create_order(symbol, "market", side, amount)
    return buy_order


def stop_loss_order(exchange, symbol, side, amount, stopLossPrice):
    stopLossParams = {
        "stopPrice": stopLossPrice,
        "reduceOnly": True,
        "workingType": "CONTRACT_PRICE",  # "MARK_PRICE", "CONTRACT_PRICE"
    }
    stopLossOrder = exchange.create_order(
        symbol, "STOP_MARKET", side, amount, None, params=stopLossParams
    )
    return stopLossOrder


def take_profit_order(exchange, symbol, side, amount, takeProfitPrice):
    takeProfitParams = {
        "stopPrice": takeProfitPrice,
        "reduceOnly": True,
        "workingType": "CONTRACT_PRICE",  # "MARK_PRICE", "CONTRACT_PRICE"
    }
    takeProfitOrder = exchange.create_order(
        symbol, "TAKE_PROFIT_MARKET", side, amount, None, params=takeProfitParams
    )
    return takeProfitOrder


def close_position_all(exchange, symbol):
    """
    close all exist position
    """
    params = {"reduceOnly": True}
    orders_all = exchange.fetch_positions()
    for i in orders_all:
        if i["info"]["symbol"] == symbol.replace("/", ""):
            side = "sell" if i["side"] == "long" else "buy"
            amount = i["contracts"]
            exchange.create_order(symbol, "market", side, amount, params=params)
    orders_all = exchange.fetch_positions()
    return orders_all


def cancel_order_all(exchange, symbol):
    """
    cancel all order when orders_all == 0
    """
    orders_all = exchange.fetch_positions()
    if len(orders_all) == 0:
        orders_all = exchange.fetch_orders(symbol)
        for i in orders_all:
            if i["info"]["status"] == "NEW":
                exchange.cancel_order(i["id"], symbol)


def trade_api_wapper(
    exchange,
    strategy_params,
    side=None,
    leverage=1,
    price=None,
    stopLossParams=None,
    takeProfitPrice=None,
    mode="open",  # open, close, cancel
):
    """
    side:str buy, sell
    leverage:int 杠杆没必要在机器人上设置, 自己在客户端调整就行, 设置为1就忽略了
    mode:str 如果为open, 开仓和止盈止损, close模式则平仓, cancel模式则为撤单
    """
    try:
        exchange_name = strategy_params["exchange_name"]
        symbol = strategy_params["symbol"]

        if mode == "open":
            side_opposite = "sell" if side == "buy" else "buy"
            # price = get_ticker(exchange, symbol)
            # stopLossParams = price - 500 if side == "buy" else price + 500
            # takeProfitPrice = price + 500 if side == "buy" else price - 500

            if price != None:
                amount = get_amount(
                    exchange_name, symbol, price, strategy_params["usd"], leverage
                )  # order["info"]["origQty"],
                order = create_order(exchange, symbol, side, amount)
                message = f"status {order['status']} amount {amount} price {price}"
                print(message)
                return message

            if exchange_name == "binance":
                if stopLossParams != None:
                    order = stop_loss_order(
                        exchange, symbol, side_opposite, amount, stopLossParams
                    )
                    message = f"status {order['status']} amount {amount} price {price}"
                    print(message)
                    return message
                if takeProfitPrice != None:
                    order = take_profit_order(
                        exchange, symbol, side_opposite, amount, takeProfitPrice
                    )
                    message = f"status {order['status']} amount {amount} price {price}"
                    print(message)
                    return message

        if mode == "close":
            close_position_all(exchange, symbol)

        if mode == "cancel":
            cancel_order_all(exchange, symbol)

    except Exception as e:
        error = f"{type(e).__name__} {str(e)}"
        print("trade_api_wapper", error)
        return error
