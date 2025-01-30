import typer

from trade_api.trade_api import load_config, connect_api, get_balance
from data_api.data_api import (
    get_data_wapper,
    test_data,
    init_data,
    get_split_idx,
)

from backtest.backtest import run_backtest_warp

from plot.plot import layout_plot

import optuna
from optimize.run_optuna import optuna_wrapper


def get_plot_config(df):
    plot_config = [
        {"name": "candle", "height_scale": 0.75, "show": True},
        {"name": "backtest", "height_scale": 0.25, "show": True},
    ]
    if "rsi" in df.columns:
        plot_config.insert(1, {"name": "rsi", "height_scale": 0.25, "show": True})
        plot_config[0]["height_scale"] = 0.60
        plot_config[1]["height_scale"] = 0.15
        plot_config[2]["height_scale"] = 0.25
    return plot_config


def get_optuna(train_df, strategy, strategy_params, optuna_params):
    study = optuna.create_study(
        # storage="sqlite:///optuna_db/db.sqlite3",
        # study_name="test",
    )
    func = optuna_wrapper(
        train_df,
        strategy,
        strategy_params=strategy_params,
        optuna_params=optuna_params,
    )
    study.optimize(func, n_trials=strategy_params.get("n_trials", 50))
    print(f"Best value: {study.best_value} (params: {study.best_params})")
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


def backtest_wapper(
    df,
    strategy,
    strategy_params,
    optuna_params={},
    exchange=None,
    optimize_mode=False,
    count_mode=True,
):
    """
    optimize_mode: 如果为True则优化, False则只回测
    count_mode: 如果为True, 则用count, False则用latest
    """

    if not optimize_mode:
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

        fig = layout_plot(
            df,
            plot_config,
            width=800,
            height=400,
            plot_params={**strategy_params, **result},
        )
        return [exchange, df, result, fig, {}]
    else:
        split_dict = get_split_idx(df, strategy_params.get("ratio", 0.2))
        train_start = split_dict["train_start"]
        train_stop = split_dict["train_stop"]
        valid_stop = split_dict["valid_stop"]
        test_stop = split_dict["test_stop"]

        res_arr = []
        for i in range(strategy_params.get("o_trials", 3)):
            train_df = df[train_start:train_stop].copy()
            study = get_optuna(train_df, strategy, strategy_params, optuna_params)

            train_valid_df = df[train_start:valid_stop].copy()
            result = get_result(train_valid_df, strategy, strategy_params, study)

            res_arr.append(
                {
                    "result": result,
                    "study": study,
                }
            )

        res_arr.sort(key=lambda x: -x["result"]["total"])
        train_study = res_arr[0]["study"]
        valid_result = res_arr[0]["result"]

        df = df[train_start:test_stop].copy()
        result = get_result(df, strategy, strategy_params, train_study)
        plot_config = get_plot_config(df)

        fig = layout_plot(
            df,
            plot_config,
            width=800,
            height=400,
            plot_params={
                "split_array": [[df, split_dict]],
                **result,
                **strategy_params,
            },
        )
        return [
            exchange,
            df,
            result,
            fig,
            {
                "train_study": train_study,
                "valid_result": valid_result,
                "split_dict": split_dict,
                "res_arr": res_arr,
            },
        ]


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
