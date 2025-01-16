import numba
import numpy as np
from backtest.backtest_long import run_long
from backtest.backtest_short import run_short


@numba.njit
def run_backtest(
    index_list,
    open_list,
    high_list,
    low_list,
    close_list,
    atr_list,
    is_nan_list,
    long_status_list,
    long_idx_list,
    long_price_list,
    long_diff_list,
    long_total_list,
    long_sl_list,
    long_tp_list,
    long_tsl_list,
    short_status_list,
    short_idx_list,
    short_price_list,
    short_diff_list,
    short_total_list,
    short_sl_list,
    short_tp_list,
    short_tsl_list,
    merge_price_list,
    merge_diff_list,
    merge_total_list,
    atr_sl=1,
    atr_tp=0,
    atr_tsl=1,
    sltp_limit=True,
    merge=True,
):
    """
    atr_sl: 1, 2, 3.5, 4... 代表atr倍数, 如果为0则省略止损, atr_tp, atr_tsl也类似
    sltp_limit: 如果为True则计算实时价格, 如果为False则计算收盘价
    触发优先级, sl limit模式, tp limit 模式, sl 普通模式, tp 普通模式, tsl 普通模式
    long_status,-1代表空仓, 1代表进场, 2代表持有0代表离场
    如果long_status=1, 那么在当前K线忽略任何止损
    merge true, 会忽略掉重合的多头空头持仓
    """
    long_array = [0, 0, -1, -1]  # idx, n, last_idx, pole_idx
    short_array = [0, 0, -1, -1]  # idx, n, last_idx, pole_idx
    for idx in range(len(index_list)):
        if is_nan_list[idx]:
            continue

        long_array[0] = idx

        if (
            long_status_list[idx] == 1
            and (short_status_list[idx - 1] == 1 or short_status_list[idx - 1] == 2)
            and merge
        ):
            long_status_list[idx] = -1
            long_total_list[idx] = long_total_list[idx - 1]
        else:
            long_array = run_long(
                _array=long_array,
                index_list=index_list,
                open_list=open_list,
                high_list=high_list,
                low_list=low_list,
                close_list=close_list,
                atr_list=atr_list,
                is_nan_list=is_nan_list,
                status_list=long_status_list,
                idx_list=long_idx_list,
                price_list=long_price_list,
                diff_list=long_diff_list,
                total_list=long_total_list,
                sl_list=long_sl_list,
                tp_list=long_tp_list,
                tsl_list=long_tsl_list,
                atr_sl=atr_sl,
                atr_tp=atr_tp,
                atr_tsl=atr_tsl,
                sltp_limit=sltp_limit,
            )

        short_array[0] = idx

        if (
            short_status_list[idx] == 1
            and (long_status_list[idx - 1] == 1 or long_status_list[idx - 1] == 2)
            and merge
        ):
            short_status_list[idx] = -1
            short_total_list[idx] = short_total_list[idx - 1]
        else:
            short_array = run_short(
                _array=short_array,
                index_list=index_list,
                open_list=open_list,
                high_list=high_list,
                low_list=low_list,
                close_list=close_list,
                atr_list=atr_list,
                is_nan_list=is_nan_list,
                status_list=short_status_list,
                idx_list=short_idx_list,
                price_list=short_price_list,
                diff_list=short_diff_list,
                total_list=short_total_list,
                sl_list=short_sl_list,
                tp_list=short_tp_list,
                tsl_list=short_tsl_list,
                atr_sl=atr_sl,
                atr_tp=atr_tp,
                atr_tsl=atr_tsl,
                sltp_limit=sltp_limit,
            )

        if merge:
            merge_diff = (
                long_diff_list[idx]
                if long_status_list[idx] != -1
                else short_diff_list[idx]
            )
            merge_diff_list[idx] = (
                merge_diff  # np.nan if np.isnan(merge_diff) else merge_diff
            )

            merge_price = (
                long_price_list[idx]
                if long_status_list[idx] != -1
                else short_price_list[idx]
            )
            merge_price_list[idx] = (
                merge_price  # np.nan if np.isnan(merge_price) else merge_price
            )

            last_merge_diff = (
                0.0 if np.isnan(merge_diff_list[idx - 1]) else merge_diff_list[idx - 1]
            )
            last_merge_price = (
                0.0
                if np.isnan(merge_price_list[idx - 1])
                else merge_price_list[idx - 1]
            )
            last_merge_total = (
                0.0
                if np.isnan(merge_total_list[idx - 1])
                else merge_total_list[idx - 1]
            )

            if (
                long_status_list[idx] == 1
                or short_status_list[idx] == 1
                or (long_status_list[idx] == -1 and short_status_list[idx] == -1)
            ):
                merge_total_list[idx] = last_merge_total
            else:
                if long_status_list[idx] != -1:
                    merge_total_list[idx] = last_merge_total + (
                        merge_price_list[idx] - last_merge_price
                    )
                else:
                    merge_total_list[idx] = last_merge_total - (
                        merge_price_list[idx] - last_merge_price
                    )


def run_backtest_warp(df, atr_sl=1, atr_tp=0, atr_tsl=1, sltp_limit=True, merge=True):
    run_backtest(
        df.index.values.astype("float64"),
        df.open.values,
        df.high.values,
        df.low.values,
        df.close.values,
        df.atr.values,
        df.is_nan.values,
        df.long_status.values,
        df.long_idx.values,
        df.long_price.values,
        df.long_diff.values,
        df.long_total.values,
        df.long_sl.values,
        df.long_tp.values,
        df.long_tsl.values,
        df.short_status.values,
        df.short_idx.values,
        df.short_price.values,
        df.short_diff.values,
        df.short_total.values,
        df.short_sl.values,
        df.short_tp.values,
        df.short_tsl.values,
        df.merge_price.values,
        df.merge_diff.values,
        df.merge_total.values,
        atr_sl=atr_sl,
        atr_tp=atr_tp,
        atr_tsl=atr_tsl,
        sltp_limit=sltp_limit,
        merge=merge,
    )
    df["long_count"] = df["long_status"]
    df.loc[df["long_count"] != 1, "long_count"] = np.nan
    long_count = df["long_count"].count()
    df.drop(["long_count"], axis=1, inplace=True)

    df["short_count"] = df["short_status"]
    df.loc[df["short_count"] != 1, "short_count"] = np.nan
    short_count = df["short_count"].count()
    df.drop(["short_count"], axis=1, inplace=True)

    count = long_count + short_count

    df["repeat"] = np.nan
    df.loc[(df["long_idx"] != -1) & (df["short_idx"] != -1), "repeat"] = 1
    repeat_count = df["repeat"].count()
    df.drop(["repeat"], axis=1, inplace=True)

    return {
        "count": count,
        "long_count": long_count,
        "short_count": short_count,
        "total": df.iloc[-1]["merge_total"],
        "one_side": long_count == 0 or short_count == 0,
        "repeat_count": repeat_count,
    }
