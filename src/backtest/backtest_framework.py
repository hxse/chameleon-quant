import typer

from trade_api.trade_api import load_config, connect_api, get_balance
from data_api.data_api import (
    get_data_wapper,
    test_data,
    init_data,
    split_data,
    get_test_index,
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
        return [exchange, df, result, fig, None]
    else:
        train_df = split_data(df, ratio=strategy_params.get("ratio", 0.3), copy=True)
        test_index_dict = get_test_index(df, train_df)

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

        plot_config = get_plot_config(df)

        fig = layout_plot(
            df,
            plot_config,
            width=800,
            height=400,
            plot_params={**test_index_dict, **result, **strategy_params},
        )
        return [exchange, df, result, fig, study]


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
