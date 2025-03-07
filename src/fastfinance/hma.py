import numpy as np
import pandas as pd
import numba as nb


@nb.njit
def wma(series: np.ndarray, length: int):
    """计算加权移动平均 WMA，确保返回与输入长度一致"""
    if length <= 1:
        return series.astype(np.float64)

    weights = np.arange(1, length + 1, dtype=np.float64)
    weighted_sum = np.full(series.shape, np.nan, dtype=np.float64)

    for i in range(len(series) - length + 1):
        weighted_sum[i + length - 1] = np.sum(
            series[i : i + length] * weights
        ) / np.sum(weights)

    return weighted_sum


@nb.njit
def hma_np(price: np.ndarray, length: int):
    """计算 HMA 指标，确保返回与输入长度一致"""
    if length < 1:
        return np.full_like(price, np.nan, dtype=np.float64)

    half_length = max(1, length // 2)
    sqrt_length = max(1, int(np.sqrt(length)))

    wma_half = wma(price, half_length)
    wma_full = wma(price, length)

    # 计算 2 * WMA(half_length) - WMA(length)
    diff = 2 * wma_half - wma_full

    # 计算 WMA(sqrt_length)
    hma_values = wma(diff, sqrt_length)

    return hma_values


def hma(close: pd.Series, length: int = 14, offset: int = 0):
    """pandas-ta 兼容的 HMA 实现"""
    close_np = close.to_numpy(dtype=np.float64)
    result = hma_np(close_np, length)
    hma_series = pd.Series(result, index=close.index)

    if offset != 0:
        hma_series = hma_series.shift(offset)

    return hma_series


# 示例用法：
if __name__ == "__main__":
    test_data = np.array(
        [
            100,
            102,
            101,
            105,
            107,
            110,
            108,
            109,
            111,
            113,
            115,
            117,
            116,
            118,
            120,
            122,
            121,
            123,
            125,
            127,
        ],
        dtype=np.float64,
    )
    df = pd.DataFrame({"close": test_data})
    df["HMA_14"] = hma(df["close"], length=14)

    import pandas_ta as ta

    df["HMA_ta"] = ta.hma(df["close"], length=14)

    print(df)
