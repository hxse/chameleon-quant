import numba
import numpy as np


@numba.njit
def run_long(
    _array,
    index_list,
    open_list,
    high_list,
    low_list,
    close_list,
    atr_list,
    is_nan_list,
    status_list,
    idx_list,
    idx2_list,
    price_list,
    diff_list,
    total_list,
    sl_list,
    tp_list,
    tsl_list,
    atr_sl=1,
    atr_tp=1,
    atr_tsl=0,
    sltp_limit=False,
    tsl_pole=True,
):
    [idx, n, n2, last_idx, pole_idx] = _array

    if status_list[idx] == 0 and (
        status_list[idx - 1] == -1 or status_list[idx - 1] == 0
    ):
        status_list[idx] = -1

    status = status_list[idx]
    open = open_list[idx]
    high = high_list[idx]
    low = low_list[idx]
    close = close_list[idx]

    if status == 1 and status_list[idx - 1] != 2:
        last_idx = idx
        pole_idx = idx
        n = 0
        n2 += 1
        price_list[idx] = close

    if last_idx != -1:
        n += 1

        if last_idx != idx:
            status = 2
            price_list[idx] = close

        _last_idx = last_idx

        pole_diff = close - close_list[pole_idx]
        if pole_diff > 0:
            pole_idx = idx
        # atr_tsl 没有limit模式, 优先级最低, 所以放上面, 在后面放atr_tp, atr_sl, 从而覆盖long_price_list值
        # 这个是指标离场, 放最上面
        if status_list[idx] == 0:
            status = 0
            last_idx = -1
            price_list[idx] = close

        if atr_tsl != 0:
            _ = high if tsl_pole else close
            tsl = _ - atr_list[idx] * atr_tsl
            tsl = (
                tsl
                if np.isnan(tsl_list[idx - 1])
                or tsl >= tsl_list[idx - 1]
                or _last_idx == idx
                else tsl_list[idx - 1]
            )
            if close <= tsl and status != 1:
                status = 0
                last_idx = -1
                price_list[idx] = close

        if atr_tp != 0:
            tp = close_list[_last_idx] + atr_list[_last_idx] * atr_tp
            if sltp_limit:
                if high >= tp and status != 1:
                    status = 0
                    last_idx = -1
                    price_list[idx] = tp
            else:
                if close >= tp and status != 1:
                    status = 0
                    last_idx = -1
                    price_list[idx] = close

        if atr_sl != 0:
            sl = close_list[_last_idx] - atr_list[_last_idx] * atr_sl
            if sltp_limit:
                if low <= sl and status != 1:
                    status = 0
                    last_idx = -1
                    price_list[idx] = sl
            else:
                if close <= sl and status != 1:
                    status = 0
                    last_idx = -1
                    price_list[idx] = close

        # save long value
        status_list[idx] = status
        idx_list[idx] = n
        idx2_list[idx] = n2

        if atr_sl != 0:
            sl_list[idx] = sl
        if atr_tp != 0:
            tp_list[idx] = tp
        if atr_tsl != 0:
            tsl_list[idx] = tsl

        diff_list[idx] = price_list[idx] - price_list[_last_idx]
        if status == 1:
            total_list[idx] = total_list[idx - 1]
        else:
            total_list[idx] = total_list[idx - 1] + (
                price_list[idx] - price_list[idx - 1]
            )
    else:
        total_list[idx] = total_list[idx - 1]

    _array = [idx, n, n2, last_idx, pole_idx]
    return _array
