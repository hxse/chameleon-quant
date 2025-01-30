import optuna
from backtest.backtest import run_backtest_warp


def optuna_wrapper(df, strategy, strategy_params, optuna_params):
    def objective(trial):
        _params = {}
        for k, v in optuna_params.items():
            if v["type"] == "int":
                _params[k] = trial.suggest_int(k, v["min"], v["max"], step=v["step"])

            if v["type"] == "float":
                _params[k] = trial.suggest_float(k, v["min"], v["max"], step=v["step"])

            if v["type"] == "categorical":
                _params[k] = trial.suggest_categorical(k, v["array"])

        _params = {**strategy_params, **_params}
        strategy(df, _params)

        return -run_backtest_warp(
            df,
            atr_sl=_params.get("atr_sl", 0),
            atr_tp=_params.get("atr_tp", 0),
            atr_tsl=_params.get("atr_tsl", 0),
            sltp_limit=strategy_params.get("sltp_limit", True),
            tsl_pole=strategy_params.get("tsl_pole", True),
        )["total"]

    return objective


if __name__ == "__main__":
    pass
optuna_params = {"sma_a": {"min": 5, "max": 200, "step": 15, "type": "int"}}

# study = optuna.create_study(
#     storage="sqlite:///optuna_db/db.sqlite3",
#     # study_name="test",
# )
# study.optimize(optuna_wrapper, n_trials=150)
# print(f"Best value: {study.best_value} (params: {study.best_params})")
