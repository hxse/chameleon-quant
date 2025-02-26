import pandas as pd
import numpy as np

# Still getting "cannot import name 'NaN' from numpy" error
# https://github.com/twopirllc/pandas-ta/issues/857
import pandas_ta as ta


def gt(a, b):
    return a > b


def lt(a, b):
    return a < b


def eq(a, b):
    return a == b


def ge(a, b):
    return a >= b


def le(a, b):
    return a <= b


def ne(a, b):
    return a != b


def cross_up(a, b):
    return (a > b) & (a.shift() <= b.shift())


def cross_down(a, b):
    return (a < b) & (a.shift() >= b.shift())


def cross_up2(a, b):
    return (a > b) & (a.shift() <= b)


def cross_down2(a, b):
    return (a < b) & (a.shift() >= b)


def init_df(df):
    df["is_nan"] = False

    df["long_status"] = -1
    df["long_idx"] = -1
    df["long_idx2"] = -1
    df["long_price"] = np.nan
    df["long_diff"] = np.nan
    df["long_total"] = 0.0
    df["long_sl"] = np.nan
    df["long_tp"] = np.nan
    df["long_tsl"] = np.nan

    df["short_status"] = -1
    df["short_idx"] = -1
    df["short_idx2"] = -1
    df["short_price"] = np.nan
    df["short_diff"] = np.nan
    df["short_total"] = 0.0
    df["short_sl"] = np.nan
    df["short_tp"] = np.nan
    df["short_tsl"] = np.nan

    df["merge_price"] = np.nan
    df["merge_diff"] = np.nan
    df["merge_total"] = 0.0
    df["merge_idx"] = -1
    df["merge_idx2"] = -1

    df["long_hold"] = df["close"] - df.iloc[0]["close"]
    df["short_hold"] = -df["long_hold"]


def set_ma(df, length, ma_mode="sma", suffix="a"):
    if ma_mode == "sma":
        df[f"{ma_mode}_{suffix}"] = ta.sma(df["close"], length=length)
    if ma_mode == "ema":
        df[f"{ma_mode}_{suffix}"] = ta.ema(df["close"], length=length)


def set_channel(
    mode, df, channel_length, channel_std, mamode="ema", suffix="a", drop_middle=False
):
    """
    bbands, kc : channel_length channel_std mamode suffix
    dc : channel_length suffix
    """
    if mode == "bbands":
        bbands = ta.bbands(
            df["close"], length=channel_length, std=channel_std, mamode=mamode
        )
        df[f"CL_{suffix}"] = bbands[f"BBL_{channel_length}_{channel_std}"]
        df[f"CM_{suffix}"] = bbands[f"BBM_{channel_length}_{channel_std}"]
        df[f"CU_{suffix}"] = bbands[f"BBU_{channel_length}_{channel_std}"]
        df[f"CB_{suffix}"] = bbands[f"BBB_{channel_length}_{channel_std}"]
        df[f"CP_{suffix}"] = bbands[f"BBP_{channel_length}_{channel_std}"]
        if drop_middle:
            df.drop([f"CM_{suffix}"], axis=1, inplace=True)
            df.drop([f"CB_{suffix}"], axis=1, inplace=True)
            df.drop([f"CP_{suffix}"], axis=1, inplace=True)

    if mode == "kc":
        kc = ta.kc(
            df["high"],
            df["low"],
            df["close"],
            length=channel_length,
            scalar=channel_std,
            mamode=mamode,
        )
        df[f"CL_{suffix}"] = kc[f"KCL{mamode[0]}_{channel_length}_{channel_std}"]
        df[f"CM_{suffix}"] = kc[f"KCB{mamode[0]}_{channel_length}_{channel_std}"]
        df[f"CU_{suffix}"] = kc[f"KCU{mamode[0]}_{channel_length}_{channel_std}"]
        if drop_middle:
            df.drop([f"CM_{suffix}"], axis=1, inplace=True)

    if mode == "dc":
        kc = ta.donchian(
            df["high"],
            df["low"],
            lower_length=channel_length,
            upper_length=channel_length,
        )
        df[f"CL_{suffix}"] = kc[f"DCL_{channel_length}_{channel_length}"]
        df[f"CM_{suffix}"] = kc[f"DCM_{channel_length}_{channel_length}"]
        df[f"CU_{suffix}"] = kc[f"DCU_{channel_length}_{channel_length}"]
        if drop_middle:
            df.drop([f"CM_{suffix}"], axis=1, inplace=True)


def set_macd(df, macd_fast, macd_slow, macd_signal):
    if macd_slow < macd_fast:
        macd_fast, macd_slow = macd_slow, macd_fast
    macd = ta.macd(df["close"], fast=macd_fast, slow=macd_slow, signal=macd_signal)
    df["macd"] = macd[f"MACD_{macd_fast}_{macd_slow}_{macd_signal}"]
    df["macds"] = macd[f"MACDs_{macd_fast}_{macd_slow}_{macd_signal}"]
    df["macdh"] = macd[f"MACDh_{macd_fast}_{macd_slow}_{macd_signal}"]


def set_rsi(df, length, rsi_smooth=None, ma_mode="ema", suffix="a"):
    df[f"rsi_{suffix}"] = ta.rsi(df["close"], length=length)
    if rsi_smooth:
        df[f"rsi_{suffix}"] = getattr(ta, ma_mode)(df["rsi_a"], length=rsi_smooth)


def set_adx(df, length, mamode="rma", suffix="a", drop=[]):
    adx = ta.adx(df["high"], df["low"], df["close"], length=length, mamode=mamode)
    df[f"adx_{suffix}"] = adx[f"ADX_{length}"]
    df[f"dmp_{suffix}"] = adx[f"DMP_{length}"]
    df[f"dmn_{suffix}"] = adx[f"DMN_{length}"]
    for i in drop:
        df.drop([f"{i}_{suffix}"], axis=1, inplace=True)
