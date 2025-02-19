import typer

from trade_api.trade_api import load_config, connect_api, get_balance
from data_api.data_api import (
    get_data_wapper,
    test_data,
    init_data,
    get_split_idx,
)

from backtest.backtest import run_backtest_warp

from plot.bokeh_plot import layout_plot, total_line, get_df_dict

import optuna
from optimize.run_optuna import optuna_wrapper

# from multiprocessing import Pool
from pathos.multiprocessing import ProcessingPool as Pool

from tqdm import tqdm


def get_plot_config(df):
    height_scale_arr = [
        [0.75, 0.25],
        [0.6, 0.2, 0.2],
        [0.5, 0.15, 0.15, 0.2],
        [0.5, 0.1, 0.1, 0.1, 0.2],
        [0.4, 0.1, 0.1, 0.1, 0.1, 0.2],
    ]
    plot_config = [
        {"name": "candle", "show": True},
        {"name": "backtest", "show": True},
    ]

    rsi_columns = [i for i in df.columns if "rsi" in i]
    if len(rsi_columns) > 0:
        plot_config.insert(1, {"name": "rsi", "show": True})

    macd_columns = [i for i in df.columns if "macd" in i]
    if len(macd_columns) > 0:
        plot_config.insert(1, {"name": "macd", "show": True})

    scale_arr = height_scale_arr[len(plot_config) - 2]
    assert len(scale_arr) == len(plot_config), "need equal length"
    for k, v in enumerate(scale_arr):
        plot_config[k]["height_scale"] = v
    return plot_config


def get_total_config():
    plot_config = [
        {"name": "backtest", "height_scale": 1, "show": True},
    ]
    return plot_config


def get_total_fig(arr, plot_config, plot_params={}):
    fig = total_line(
        arr,
        plot_config=plot_config,
        width=800,
        height=100,
        plot_params=plot_params,
    )
    return fig


def get_backtest_fig(
    df,
    plot_config,
    result,
    strategy_params,
    split_dict={},
    span_mode=True,
):
    plot_params = {
        "split_dict": split_dict,
        "span_mode": span_mode,
        **result,
        **strategy_params,
    }
    df_dict = get_df_dict(df, plot_params=plot_params)
    fig = layout_plot(
        df_dict, plot_config, width=800, height=400, plot_params=plot_params
    )
    return fig


def get_optuna(train_df, strategy, strategy_params, optuna_params):
    optuna.logging.set_verbosity(optuna.logging.ERROR)

    study = optuna.create_study(
        # storage="sqlite:///optuna_db/db.sqlite3",
        # study_name="test",
    )
    n_trials = strategy_params.get("n_trials", 50)
    with tqdm(total=n_trials, position=1, desc="optuna", leave=True) as pbar:

        def wrapped_objective(trial):

            func = optuna_wrapper(
                train_df,
                strategy,
                strategy_params=strategy_params,
                optuna_params=optuna_params,
            )

            result = func(trial)
            pbar.update(1)
            return result

        study.optimize(
            wrapped_objective,
            n_trials=n_trials,
            # show_progress_bar=True,
        )
        # print(f"Best value: {study.best_value} (params: {study.best_params})")
    return study


def get_result(df, strategy, strategy_params, study):
    strategy_params = {**strategy_params, **study.best_params}
    strategy(df, strategy_params)
    result = run_backtest_warp(
        df,
        atr_sl=strategy_params.get("atr_sl", 0),
        atr_tp=strategy_params.get("atr_tp", 0),
        atr_tsl=strategy_params.get("atr_tsl", 0),
        sltp_limit=strategy_params.get("sltp_limit", True),
        tsl_pole=strategy_params.get("tsl_pole", True),
    )
    return result


def get_optuna_result(params):
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
    train_start = split_dict["train_start"]
    train_stop = split_dict["train_stop"]

    train_df = f_df.iloc[train_start:train_stop].copy()
    study = get_optuna(train_df, strategy, strategy_params, optuna_params)
    return {
        **params,
        "split_dict": split_dict,
        "study": study,
        "f_df": f_df,
        "train_df": train_df,
    }


def get_valid_result(params):
    f_df = params["f_df"]
    split_dict = params["split_dict"]
    strategy = params["strategy"]
    strategy_params = params["strategy_params"]
    study = params["study"]

    train_start = split_dict["train_start"]
    valid_stop = split_dict["valid_stop"]
    train_valid_df = f_df.iloc[train_start:valid_stop].copy()
    valid_result = get_result(train_valid_df, strategy, strategy_params, study)
    return {
        **params,
        "train_valid_df": train_valid_df,
        "valid_result": valid_result,
    }


def get_test_result(params):
    split_dict = params["split_dict"]
    f_df = params["f_df"]
    strategy = params["strategy"]
    strategy_params = params["strategy_params"]
    study = params["study"]

    train_start = split_dict["train_start"]
    test_stop = split_dict["test_stop"]
    test_df = f_df.iloc[train_start:test_stop].copy()
    test_result = get_result(test_df, strategy, strategy_params, study)
    return {
        **params,
        "test_df": test_df,
        "test_result": test_result,
    }


def get_sort_result(result_arr):
    value_arr = {}
    key_arr = {}

    def get_idx(x):
        return "_".join([str(i) for i in x["f_idx"]])

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


def get_forwar_test_split_data(df, strategy_params):
    enable_forward_test = strategy_params.get("enable_forward_test", True)
    if not enable_forward_test:
        return [[0, len(df)]]
    df_length = len(df)
    f_count = strategy_params.get("f_count", 5000)
    ratio = strategy_params.get("ratio", 0.2)
    test_length = int(f_count * ratio)
    res = []
    s = (df_length - 1 - f_count) / (test_length)
    s2 = (df_length - 1 - f_count) % (test_length)
    s = int(s + 1) if s2 == 0 else int(s + 2)
    for i in range(s):
        res.append([0 + ((i) * test_length), f_count + ((i) * test_length)])
    return res


def print_result_array(arr, name, field):
    print(
        f"{name}:",
        len(arr),
        [
            [
                "f_idx",
                i["f_idx"],
                "candle_count",
                i[field]["candle_count"],
                "count",
                i[field]["count"],
                "total",
                i[field]["total"],
            ]
            for i in arr
        ],
    )


def backtest_wapper(
    df,
    strategy,
    strategy_params,
    optuna_params={},
    exchange=None,
    optimize_mode=False,
    multi_process=False,
):
    """
    optimize_mode: 如果为True则优化, False则只回测
    count_mode: 如果为True, 则用count, False则用latest
    """

    if optimize_mode == "backtest":
        df = df.copy()
        strategy(df, strategy_params)
        result = run_backtest_warp(
            df,
            atr_sl=strategy_params.get("atr_sl", 0),
            atr_tp=strategy_params.get("atr_tp", 0),
            atr_tsl=strategy_params.get("atr_tsl", 0),
            sltp_limit=strategy_params.get("sltp_limit", True),
            tsl_pole=strategy_params.get("tsl_pole", True),
        )
        plot_config = get_plot_config(df)

        plot_params = {**strategy_params, **result}
        df_dict = get_df_dict(df)
        fig = layout_plot(
            df_dict,
            plot_config,
            width=800,
            height=400,
            plot_params=plot_params,
        )
        return [
            exchange,
            df,
            result,
            fig,
            {"plot_config": plot_config, "plot_params": plot_params},
        ]

    elif optimize_mode == "forward_testing":
        df = df.copy()

        forwar_test_split_data = get_forwar_test_split_data(df, strategy_params)
        params_arr = []
        for f in forwar_test_split_data:
            for o in range(strategy_params.get("o_trials", 3)):
                params_arr.append(
                    {
                        "f_idx": f,
                        "o_idx": o,
                        "strategy": strategy,
                        "strategy_params": strategy_params,
                        "optuna_params": optuna_params,
                        "df": df,
                    }
                )

        def _get_result_wrapper(i):
            params_res = get_optuna_result(i)
            params_res = get_valid_result(params_res)
            return params_res

        if not multi_process:
            valid_arr = []
            for i in tqdm(
                range(len(params_arr)), position=0, desc="all loop", leave=True
            ):
                result = _get_result_wrapper(params_arr[i])
                valid_arr.append(result)
        else:
            with Pool() as pool:
                valid_arr = list(
                    tqdm(
                        pool.imap(_get_result_wrapper, params_arr),
                        total=len(params_arr),
                        position=0,
                        desc="all loop",
                        leave=True,
                    )
                )

        sort_arr = get_sort_result(valid_arr)

        test_arr = []
        for i in sort_arr:
            result = get_test_result(i)
            test_arr.append(result)

        return [valid_arr, sort_arr, test_arr]


def test():
    import strategy

    for [_p, _s, _name] in strategy.strategy_arr:
        print(f"run {_p} {_name} {_s}")
        [exchange, ohlcv_df] = backtest_wapper(
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
