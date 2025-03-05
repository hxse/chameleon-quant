import pandas as pd
import numpy as np

import pandas as pd
import numpy as np


def standard_lrsi(price, gamma=0.5):
    """
    计算标准 Laguerre RSI（带循环）。

    参数:
        price (pd.Series): 输入价格序列
        gamma (float): Laguerre 滤波器的阻尼因子，默认 0.5

    返回:
        pd.Series: LRSI 序列
    """
    n = len(price)
    l0 = np.zeros(n)
    l1 = np.zeros(n)
    l2 = np.zeros(n)
    l3 = np.zeros(n)
    lrsi = np.zeros(n)

    for t in range(1, n):
        l0[t] = (1 - gamma) * price[t] + gamma * l0[t - 1]
        l1[t] = -gamma * l0[t] + l0[t - 1] + gamma * l1[t - 1]
        l2[t] = -gamma * l1[t] + l1[t - 1] + gamma * l2[t - 1]
        l3[t] = -gamma * l2[t] + l2[t - 1] + gamma * l3[t - 1]

        cu = 0.0
        cd = 0.0
        if l0[t] >= l1[t]:
            cu += l0[t] - l1[t]
        else:
            cd += l1[t] - l0[t]
        if l1[t] >= l2[t]:
            cu += l1[t] - l2[t]
        else:
            cd += l2[t] - l1[t]
        if l2[t] >= l3[t]:
            cu += l2[t] - l3[t]
        else:
            cd += l3[t] - l2[t]

        den = cu + cd
        lrsi[t] = 1.0 if den == 0 else cu / den

    return pd.Series(lrsi, index=price.index, name="lrsi")


import pandas as pd
import numpy as np


def vectorized_lrsi(price, gamma=0.5):
    """
    计算矢量化的 Laguerre RSI（无循环）。

    参数:
        price (pd.Series): 输入价格序列
        gamma (float): Laguerre 滤波器的阻尼因子，默认 0.5

    返回:
        pd.Series: LRSI 序列
    """
    price_values = price.values
    n = len(price)
    l0 = np.zeros(n)
    l1 = np.zeros(n)
    l2 = np.zeros(n)
    l3 = np.zeros(n)

    # 计算 Laguerre 滤波器
    for t in range(1, n):
        l0[t] = (1 - gamma) * price_values[t] + gamma * l0[t - 1]
        l1[t] = -gamma * l0[t] + l0[t - 1] + gamma * l1[t - 1]
        l2[t] = -gamma * l1[t] + l1[t - 1] + gamma * l2[t - 1]
        l3[t] = -gamma * l2[t] + l2[t - 1] + gamma * l3[t - 1]

    # 矢量化计算差异
    diff0 = l0 - l1
    diff1 = l1 - l2
    diff2 = l2 - l3

    # 矢量化计算 cu 和 cd
    cu = np.maximum(diff0, 0) + np.maximum(diff1, 0) + np.maximum(diff2, 0)
    cd = np.maximum(-diff0, 0) + np.maximum(-diff1, 0) + np.maximum(-diff2, 0)

    # 矢量化计算 LRSI，处理除零情况
    den = cu + cd
    lrsi = np.where(den == 0, 0.0, cu / den)  # 当 den=0 时，设置为 0.0

    # 显式设置 t=0 处的 LRSI 为 0.0
    lrsi[0] = 0.0

    return pd.Series(lrsi, index=price.index, name="lrsi")


from numba import njit


@njit
def compute_lrsi(price_values, gamma):
    """
    使用 Numba 加速的 LRSI 计算核心函数。

    参数:
        price_values (np.ndarray): 输入价格数组
        gamma (float): Laguerre 滤波器的阻尼因子

    返回:
        np.ndarray: LRSI 数组
    """
    n = len(price_values)
    l0 = np.zeros(n)
    l1 = np.zeros(n)
    l2 = np.zeros(n)
    l3 = np.zeros(n)
    lrsi = np.zeros(n)

    # 计算 Laguerre 滤波器和 LRSI
    for t in range(1, n):
        l0[t] = (1 - gamma) * price_values[t] + gamma * l0[t - 1]
        l1[t] = -gamma * l0[t] + l0[t - 1] + gamma * l1[t - 1]
        l2[t] = -gamma * l1[t] + l1[t - 1] + gamma * l2[t - 1]
        l3[t] = -gamma * l2[t] + l2[t - 1] + gamma * l3[t - 1]

        # 计算 cu 和 cd
        cu = 0.0
        cd = 0.0
        if l0[t] >= l1[t]:
            cu += l0[t] - l1[t]
        else:
            cd += l1[t] - l0[t]
        if l1[t] >= l2[t]:
            cu += l1[t] - l2[t]
        else:
            cd += l2[t] - l1[t]
        if l2[t] >= l3[t]:
            cu += l2[t] - l3[t]
        else:
            cd += l3[t] - l2[t]

        # 计算 LRSI
        den = cu + cd
        lrsi[t] = 0.0 if den == 0 else cu / den

    return lrsi


def optimized_lrsi(price, gamma=0.5):
    """
    优化后的 Laguerre RSI 计算函数。

    参数:
        price (pd.Series): 输入价格序列
        gamma (float): Laguerre 滤波器的阻尼因子，默认 0.5

    返回:
        pd.Series: LRSI 序列
    """
    price_values = price.values
    lrsi = compute_lrsi(price_values, gamma)
    return pd.Series(lrsi, index=price.index, name="lrsi")


if __name__ == "__main__":
    price = pd.Series([100, 102, 101, 103, 105, 104, 106, 107, 108, 110])
    # 假设你有标准 LRSI 的实现函数 standard_lrsi
    std_lrsi = standard_lrsi(price, gamma=0.5)
    vec_lrsi = vectorized_lrsi(price, gamma=0.5)
    opt_lrsi = optimized_lrsi(price, gamma=0.5)

    print("标准 LRSI:")
    print(std_lrsi)
    print("\n矢量化 LRSI:")
    print(vec_lrsi)
    print("\nnumba LRSI:")
    print(opt_lrsi)
    print("\nLRSI 序列是否相等？")
    print(np.allclose(std_lrsi, vec_lrsi, opt_lrsi, atol=1e-8))
