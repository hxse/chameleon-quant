import typer
from trade_api.trade_api import load_config, connect_api, get_balance
from data_api.data_api import (
    get_data_wapper,
    test_data,
    init_data,
    get_split_idx,
)
from backtest.backtest import run_backtest_warp
from plot.bokeh_plot import layout_plot, total_line, get_df_dict, filter_columns
import optuna
from optimize.run_optuna import optuna_wrapper
from pathos.multiprocessing import ProcessingPool as Pool
from tqdm import tqdm
import pandas as pd
import sys
from multiprocessing import Value
import math
import warnings
from typing import Optional, Dict, List, Any, Tuple
import os

warnings.filterwarnings("ignore", category=UserWarning, module="optuna")

# 常量定义
HEIGHT_SCALE_ARR = [
    [0.75, 0.25],
    [0.6, 0.2, 0.2],
    [0.5, 0.15, 0.15, 0.2],
    [0.5, 0.1, 0.1, 0.1, 0.2],
    [0.4, 0.1, 0.1, 0.1, 0.1, 0.2],
]


def get_plot_config(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """动态生成绘图配置，根据 DataFrame 列名调整"""
    plot_config = [
        {"name": "candle", "show": True},
        {"name": "backtest", "show": True},
    ]

    indicators = [
        {"name": "rsi", "key": ["rsi"]},
        {"name": "lrsi", "key": ["lrsi"]},
        {"name": "macd", "key": ["macd"]},
        {"name": "adx", "key": ["adx", "dmp", "dmn"]},
        {"name": "slope", "key": ["zscore"]},
    ]

    for indicator in indicators:
        if any(col in df.columns for col in indicator["key"]):
            indicator["show"] = True
            plot_config.insert(1, indicator)

    scale_arr = HEIGHT_SCALE_ARR[len(plot_config) - 2]
    assert len(scale_arr) == len(plot_config), (
        "Height scales must match plot config length"
    )
    for idx, scale in enumerate(scale_arr):
        plot_config[idx]["height_scale"] = scale

    return plot_config


def get_total_config() -> List[Dict[str, Any]]:
    """返回总览图配置"""
    return [{"name": "backtest", "height_scale": 1, "show": True}]


def get_total_fig(
    arr: List[Any], plot_config: List[Dict[str, Any]], plot_params: Dict[str, Any] = {}
) -> Any:
    """生成总览图"""
    return total_line(
        arr, plot_config=plot_config, width=800, height=100, plot_params=plot_params
    )


def get_backtest_fig(
    df: pd.DataFrame,
    plot_config: List[Dict[str, Any]],
    result: Dict[str, Any],
    strategy_params: Dict[str, Any],
    split_dict: Dict[str, int] = {},
    span_mode: bool = True,
) -> Any:
    """生成回测图"""
    plot_params = {
        "split_dict": split_dict,
        "span_mode": span_mode,
        **result,
        **strategy_params,
    }
    df_dict = get_df_dict(df, plot_params=plot_params)
    return layout_plot(
        df_dict, plot_config, width=800, height=400, plot_params=plot_params
    )


def get_optuna(
    train_df: pd.DataFrame,
    strategy: callable,
    strategy_params: Dict[str, Any],
    optuna_params: Dict[str, Any],
    disable_bar: bool = False,
) -> optuna.Study:
    """执行 Optuna 优化"""
    optuna.logging.set_verbosity(optuna.logging.ERROR)
    study = optuna.create_study()
    n_trials = strategy_params.get("n_trials", 50)
    n_jobs = strategy_params.get("n_jobs", 1)
    completed_trials = Value("i", 0)

    pbar = tqdm(
        total=n_trials,
        desc="Optuna",
        leave=True,
        file=sys.stdout,
        disable=disable_bar,
    )

    def update_progress(study, trial):
        with completed_trials.get_lock():
            completed_trials.value += 1
        pbar.n = completed_trials.value
        pbar.refresh()
        sys.stdout.flush()

    def wrapped_objective(trial):
        func = optuna_wrapper(
            train_df,
            strategy,
            strategy_params=strategy_params,
            optuna_params=optuna_params,
        )
        result = func(trial)
        if n_jobs == 1:
            with completed_trials.get_lock():
                completed_trials.value += 1
            pbar.n = completed_trials.value
            pbar.refresh()
            sys.stdout.flush()
        return result

    study.optimize(
        wrapped_objective,
        n_trials=n_trials,
        n_jobs=n_jobs,
        callbacks=[update_progress] if n_jobs != 1 else [],
    )
    pbar.close()
    return study


def get_result(
    df: pd.DataFrame,
    strategy: callable,
    strategy_params: Dict[str, Any],
    study: Optional[optuna.Study] = None,
) -> Dict[str, Any]:
    """运行策略并返回回测结果"""
    if study is not None:
        strategy_params = {**strategy_params, **study.best_params}
    strategy(df, strategy_params)
    return run_backtest_warp(
        df,
        atr_sl=strategy_params.get("atr_sl", 0),
        atr_tp=strategy_params.get("atr_tp", 0),
        atr_tsl=strategy_params.get("atr_tsl", 0),
        sltp_limit=strategy_params.get("sltp_limit", True),
        tsl_pole=strategy_params.get("tsl_pole", True),
    )


def get_optuna_result(params: Dict[str, Any]) -> Dict[str, Any]:
    """获取 Optuna 优化结果"""
    df = params["df"]
    f_idx = params["f_idx"]
    strategy = params["strategy"]
    strategy_params = params["strategy_params"]
    optuna_params = params["optuna_params"]

    f_df = df.iloc[f_idx[0] : f_idx[1]].copy()
    f_df.reset_index(inplace=True)
    f_df.rename(columns={"index": "origin_index"}, inplace=True)

    length = f_idx[1] - f_idx[0]
    split_dict = get_split_idx(length, strategy_params.get("ratio", 0.2))
    train_start, train_stop = split_dict["train_start"], split_dict["train_stop"]

    train_df = f_df.iloc[train_start:train_stop].copy()
    study = get_optuna(train_df, strategy, strategy_params, optuna_params)
    return {
        **params,
        "split_dict": split_dict,
        "study": study,
        "f_df": f_df,
        "train_df": train_df,
    }


def get_valid_result(params: Dict[str, Any]) -> Dict[str, Any]:
    """获取验证集结果"""
    f_df = params["f_df"]
    split_dict = params["split_dict"]
    strategy = params["strategy"]
    strategy_params = params["strategy_params"]
    study = params["study"]

    train_start, valid_stop = split_dict["train_start"], split_dict["valid_stop"]
    train_valid_df = f_df.iloc[train_start:valid_stop].copy()
    valid_result = get_result(train_valid_df, strategy, strategy_params, study)
    return {**params, "train_valid_df": train_valid_df, "valid_result": valid_result}


def get_test_result(params: Dict[str, Any]) -> Dict[str, Any]:
    """获取测试集结果"""
    f_df = params["f_df"]
    split_dict = params["split_dict"]
    strategy = params["strategy"]
    strategy_params = params["strategy_params"]
    study = params["study"]

    train_start, test_stop = split_dict["train_start"], split_dict["test_stop"]
    test_df = f_df.iloc[train_start:test_stop].copy()
    test_result = get_result(test_df, strategy, strategy_params, study)
    return {**params, "test_df": test_df, "test_result": test_result}


def get_sort_result(result_arr: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """根据验证集总收益对结果排序，保留最佳结果"""
    value_arr = {}
    key_arr = {}

    def get_idx(x):
        return "_".join(map(str, x["f_idx"]))

    for k, v in enumerate(result_arr):
        key = get_idx(v)
        if key in value_arr:
            if v["valid_result"]["total"] > value_arr[key]["valid_result"]["total"]:
                value_arr[key] = v
                key_arr[key] = k
        else:
            value_arr[key] = v
            key_arr[key] = k

    return [v for k, v in enumerate(result_arr) if k == key_arr[get_idx(v)]]


def get_forward_test_split_data(
    df: pd.DataFrame, strategy_params: Dict[str, Any]
) -> List[List[List[int]]]:
    """生成前向测试的滚动窗口分割数据"""
    f_count = strategy_params.get("f_count", 5000)
    if f_count >= len(df):
        raise ValueError(
            f"Window size ({f_count}) must be less than data length ({len(df)})"
        )
    ratio = strategy_params.get("ft_ratio", 0.3)
    roll_num = int(f_count * ratio)
    res = [[[0, f_count], [f_count, f_count + roll_num]]]

    for i in range(1, math.ceil(len(df) / roll_num)):
        prev = res[-1]
        new_train_start = prev[0][0] + roll_num
        new_train_stop = prev[0][1] + roll_num
        new_test_start = prev[1][0] + roll_num
        new_test_stop = min(prev[1][1] + roll_num, len(df))
        res.append([[new_train_start, new_train_stop], [new_test_start, new_test_stop]])
        if new_test_stop == len(df):
            break

    return res


def print_result_array(arr: List[Dict[str, Any]], name: str, field: str) -> None:
    """打印结果数组的详细信息"""
    print(
        f"{name}: {len(arr)}",
        [
            {
                "f_idx": i["f_idx"],
                "candle_count": i[field]["candle_count"],
                "count": i[field]["count"],
                "total": i[field]["total"],
            }
            for i in arr
        ],
    )


def get_fig(
    strategy_params: Dict[str, Any],
    df: pd.DataFrame,
    result: Dict[str, Any],
    split_dict: Optional[Dict[str, int]] = None,
    span_mode: bool = False,
) -> Tuple[Any, List[Dict[str, Any]], Dict[str, Any]]:
    """生成绘图对象"""
    plot_config = get_plot_config(df)
    plot_params = {**strategy_params, **result}
    if split_dict is not None:
        plot_params["split_dict"] = split_dict
    plot_params["span_mode"] = span_mode

    df_dict = get_df_dict(df, plot_params=plot_params)
    fig = layout_plot(
        df_dict, plot_config, width=800, height=400, plot_params=plot_params
    )
    return [fig, plot_config, plot_params]


def fill_df(
    origin_df: pd.DataFrame, target_df: pd.DataFrame, is_nan_count: int
) -> pd.DataFrame:
    """根据 is_nan 值补全 DataFrame"""
    fill_df = origin_df.iloc[-is_nan_count:]
    return pd.concat([fill_df, target_df], axis=0, ignore_index=True)


def cut_df(
    origin_df: Optional[pd.DataFrame], target_df: pd.DataFrame, is_nan_count: int
) -> pd.DataFrame:
    """根据 is_nan 值剪切 DataFrame"""
    new_df = target_df.iloc[is_nan_count:].copy()
    new_df.reset_index(drop=True, inplace=True)
    return new_df


def process_data_segment(
    df: pd.DataFrame,
    origin_df: pd.DataFrame,
    is_nan_count: int,
    start: int,
    stop: int,
    strategy: callable,
    strategy_params: Dict[str, Any],
    study: Optional[optuna.Study],
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """处理数据片段"""
    segment_df = df.iloc[start:stop].copy()
    segment_df.reset_index(drop=True, inplace=True)

    if strategy_params.get("data_completion", False):
        original_start, original_end = (
            segment_df["date"].iloc[0],
            segment_df["date"].iloc[-1],
        )
        segment_df = fill_df(origin_df, segment_df, is_nan_count)

    result = get_result(segment_df, strategy, strategy_params, study)

    if strategy_params.get("data_completion", False):
        segment_df = cut_df(None, segment_df, is_nan_count)
        if not (
            segment_df["date"].iloc[0] == original_start
            and segment_df["date"].iloc[-1] == original_end
        ):
            raise AssertionError("Date mismatch after data completion")

    return segment_df, result


def get_is_nan_count(df: pd.DataFrame) -> int:
    """计算 DataFrame 中 is_nan 的数量"""
    return df["is_nan"].sum() if "is_nan" in df.columns else 0


def get_train_valid_test(
    df: pd.DataFrame,
    strategy: callable,
    strategy_params: Dict[str, Any],
    optuna_params: Dict[str, Any],
) -> Dict[str, Any]:
    """执行训练-验证-测试流程"""
    df = df.copy()
    df["origin_index"] = df.index
    split_dict = get_split_idx(len(df), strategy_params.get("ratio", 0.2))

    train_df = df.iloc[split_dict["train_start"] : split_dict["train_stop"]].copy()
    train_df.reset_index(drop=True, inplace=True)

    study = get_optuna(train_df, strategy, strategy_params, optuna_params)
    train_result = get_result(train_df, strategy, strategy_params, study)

    is_nan_count = get_is_nan_count(train_df)

    valid_df, valid_result = process_data_segment(
        df,
        train_df,
        is_nan_count,
        split_dict["valid_start"],
        split_dict["valid_stop"],
        strategy,
        strategy_params,
        study,
    )
    test_df, test_result = process_data_segment(
        df,
        valid_df,
        is_nan_count,
        split_dict["test_start"],
        split_dict["test_stop"],
        strategy,
        strategy_params,
        study,
    )

    train_valid_df = df.iloc[
        split_dict["train_start"] : split_dict["valid_stop"]
    ].copy()
    train_valid_df.reset_index(drop=True, inplace=True)
    train_valid_result = get_result(train_valid_df, strategy, strategy_params, study)

    train_valid_test_df = df.iloc[
        split_dict["train_start"] : split_dict["test_stop"]
    ].copy()
    train_valid_test_df.reset_index(drop=True, inplace=True)
    train_valid_test_result = get_result(
        train_valid_test_df, strategy, strategy_params, study
    )

    return {
        "train_df": train_df,
        "train_result": train_result,
        "valid_df": valid_df,
        "valid_result": valid_result,
        "test_df": test_df,
        "test_result": test_result,
        "train_valid_df": train_valid_df,
        "train_valid_result": train_valid_result,
        "train_valid_test_df": train_valid_test_df,
        "train_valid_test_result": train_valid_test_result,
        "study": study,
        "split_dict": split_dict,
    }


def find_new_index(df: pd.DataFrame, origin_index_value: int) -> Optional[int]:
    """查找原始索引在新 DataFrame 中的位置"""
    mask = df["origin_index"] == origin_index_value
    return mask.idxmax() if mask.any() else None


def _get_forward_test(params: List[Any], disable_bar: bool = False) -> Dict[str, Any]:
    """执行单个前向测试任务"""
    f_idx, df, strategy, strategy_params, optuna_params = params
    train_start, train_stop = f_idx[0][0], f_idx[0][1]
    test_start, test_stop = f_idx[1][0], f_idx[1][1]

    train_df = df.iloc[train_start:train_stop].copy()
    train_df.reset_index(drop=True, inplace=True)

    study = get_optuna(
        train_df, strategy, strategy_params, optuna_params, disable_bar=disable_bar
    )
    train_result = get_result(train_df, strategy, strategy_params, study)

    is_nan_count = get_is_nan_count(train_df)

    test_df, test_result = process_data_segment(
        df,
        train_df,
        is_nan_count,
        test_start,
        test_stop,
        strategy,
        strategy_params,
        study,
    )

    train_test_df = df.iloc[train_start:test_stop].copy()
    train_test_df.reset_index(drop=True, inplace=True)
    train_test_result = get_result(train_test_df, strategy, strategy_params, study)

    split_dict = {
        "train_start": find_new_index(train_test_df, train_start - 1),
        "train_stop": find_new_index(train_test_df, train_stop - 1),
        "test_start": find_new_index(train_test_df, test_start - 1),
        "test_stop": find_new_index(train_test_df, test_stop - 1),
    }

    return {
        "train_df": train_df,
        "train_result": train_result,
        "test_df": test_df,
        "test_result": test_result,
        "train_test_df": train_test_df,
        "train_test_result": train_test_result,
        "study": study,
        "f_idx": f_idx,
        "split_dict": split_dict,
    }


def get_forward_test(
    df: pd.DataFrame,
    strategy: callable,
    strategy_params: Dict[str, Any],
    optuna_params: Dict[str, Any],
    multi_process: bool = False,
) -> List[Dict[str, Any]]:
    """执行前向测试"""
    df = df.copy()
    df["origin_index"] = df.index
    forward_test_split_data = get_forward_test_split_data(df, strategy_params)
    params_arr = [
        [f_idx, df, strategy, strategy_params, optuna_params]
        for f_idx in forward_test_split_data
    ]

    res_arr = []
    if not multi_process:
        # 单进程模式，使用 tqdm 包装迭代
        for params in tqdm(
            params_arr,
            total=len(params_arr),
            position=0,
            desc="all loop",
            leave=True,
        ):
            res = _get_forward_test(params, disable_bar=True)
            res_arr.append(res)
    else:
        # 多进程模式，保持原有 tqdm 包装 pool.imap
        with Pool(processes=min(len(params_arr), os.cpu_count())) as pool:
            res_arr = list(
                tqdm(
                    pool.imap(
                        lambda x: _get_forward_test(x, disable_bar=True), params_arr
                    ),
                    total=len(params_arr),
                    position=0,
                    desc="all loop",
                    leave=True,
                )
            )

    return res_arr


def backtest_wapper(
    df: pd.DataFrame,
    strategy: callable,
    strategy_params: Dict[str, Any],
    optuna_params: Dict[str, Any] = {},
    exchange: Optional[str] = None,
    optimize_mode: str = "backtest",
    multi_process: bool = False,
) -> Any:
    """回测或优化主函数"""
    if optimize_mode == "backtest":
        df = df.copy()
        df["origin_index"] = df.index
        strategy(df, strategy_params)
        result = run_backtest_warp(
            df,
            atr_sl=strategy_params.get("atr_sl", 0),
            atr_tp=strategy_params.get("atr_tp", 0),
            atr_tsl=strategy_params.get("atr_tsl", 0),
            sltp_limit=strategy_params.get("sltp_limit", True),
            tsl_pole=strategy_params.get("tsl_pole", True),
        )
        fig, plot_config, plot_params = get_fig(strategy_params, df, result)
        return [
            exchange,
            df,
            result,
            fig,
            {"plot_config": plot_config, "plot_params": plot_params},
        ]
    elif optimize_mode == "train_valid_test":
        return get_train_valid_test(df, strategy, strategy_params, optuna_params)
    elif optimize_mode == "forward_testing":
        return get_forward_test(
            df, strategy, strategy_params, optuna_params, multi_process=multi_process
        )
    else:
        raise ValueError(f"Unknown optimize_mode: {optimize_mode}")


def show_fig_wapper(
    result_dict: Dict[str, Any],
    _s: Any,
    enable_train: bool = False,
    enable_valid: bool = False,
    enable_test: bool = False,
    enable_train_valid: bool = False,
    enable_train_valid_test: bool = False,
) -> Tuple[Optional[Any], Optional[List[Dict[str, Any]]], Optional[Dict[str, Any]]]:
    """显示指定部分的图形"""
    fig = None
    plot_config = None
    plot_params = None

    if enable_train:
        fig, plot_config, plot_params = get_fig(
            _s.strategy_params, result_dict["train_df"], result_dict["train_result"]
        )
    elif enable_valid:
        fig, plot_config, plot_params = get_fig(
            _s.strategy_params, result_dict["valid_df"], result_dict["valid_result"]
        )
    elif enable_test:
        fig, plot_config, plot_params = get_fig(
            _s.strategy_params, result_dict["test_df"], result_dict["test_result"]
        )
    elif enable_train_valid:
        fig, plot_config, plot_params = get_fig(
            _s.strategy_params,
            result_dict["train_valid_df"],
            result_dict["train_valid_result"],
            split_dict=result_dict["split_dict"],
            span_mode=True,
        )
    elif enable_train_valid_test:
        fig, plot_config, plot_params = get_fig(
            _s.strategy_params,
            result_dict["train_valid_test_df"],
            result_dict["train_valid_test_result"],
            split_dict=result_dict["split_dict"],
            span_mode=True,
        )

    return fig, plot_config, plot_params


def test():
    """测试函数"""
    import strategy

    for [_p, _s, _name] in strategy.strategy_arr:
        print(f"run {_p} {_name} {_s}")
        exchange, ohlcv_df = backtest_wapper(
            strategy=_s.strategy,
            strategy_params=_s.params,
            optuna_params=_s.optuna_params,
        )
        print(233, exchange, len(ohlcv_df))
        break


if __name__ == "__main__":
    app = typer.Typer(pretty_exceptions_show_locals=False)
    app.command(help="also tw")(backtest_wapper)
    app.command("tw", hidden=True)(backtest_wapper)
    app.command(help="also te")(test)
    app.command("te", hidden=True)(test)
    app()
