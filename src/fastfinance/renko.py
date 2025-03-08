import pandas as pd
import numpy as np
from pandas_ta.utils import verify_series


def compute_renko(close, brick_size):
    renko_state = np.zeros(len(close), dtype=np.int32)
    renko_brick = np.full(len(close), close[0], dtype=np.float64)
    renko_count = np.zeros(len(close), dtype=np.int32)

    print(
        f"i=0, price={close[0]}, prev_brick={close[0]}, price_change=0.0, renko_count=0, renko_state=0, new_brick={renko_brick[0]}"
    )

    for i in range(1, len(close)):
        price_change = close[i] - renko_brick[i - 1]
        if price_change >= brick_size:
            renko_state[i] = 1
            brick_count = int(np.floor(price_change / brick_size))  # 上升：向下取整
            renko_brick[i] = renko_brick[i - 1] + (brick_count * brick_size)
            renko_count[i] = brick_count
        elif price_change <= -brick_size:
            renko_state[i] = -1
            brick_count = int(np.ceil(price_change / brick_size))  # 下降：向上取整负数
            renko_brick[i] = renko_brick[i - 1] + (brick_count * brick_size)
            renko_count[i] = brick_count
        else:
            renko_state[i] = 0
            renko_brick[i] = renko_brick[i - 1]
            renko_count[i] = 0

        print(
            f"i={i}, price={close[i]}, prev_brick={renko_brick[i-1]}, price_change={price_change}, renko_count={renko_count[i]}, renko_state={renko_state[i]}, new_brick={renko_brick[i]}"
        )

    return renko_state, renko_brick, renko_count


def renko_like(close, brick_size=0.01, name="RENKO", input_col="close"):
    close = verify_series(close)
    renko_state, renko_brick, renko_count = compute_renko(close.values, brick_size)
    result = pd.DataFrame(
        {
            "renko_state": renko_state,
            "renko_brick": renko_brick,
            "renko_count": renko_count,
        },
        index=close.index,
    )
    result.category = "trend"
    result.inputs = {"close": input_col, "brick_size": brick_size}
    return result


if __name__ == "__main__":

    # 测试数据
    dates = pd.date_range(start="2023-01-01", periods=10, freq="D")
    prices = [100.0, 101.5, 102.8, 101.2, 103.0, 104.5, 102.0, 100.5, 99.0, 101.2]
    df = pd.DataFrame({"close": prices}, index=dates)
    renko_df = renko_like(df["close"], brick_size=1.0)
    result_df = pd.concat([df, renko_df], axis=1)
    print("\nFinal Result:")
    print(result_df)
