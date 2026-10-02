"""
Data loading and market state preparation.
No look-ahead: all statistics computed only from available history.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import yaml

def load_raw_series(data_dir: Path):
    def _load(name):
        df = pd.read_csv(data_dir / f"{name}.csv")
        df.columns = ["open", "low", "high", "close", "change", "pct", "date_g", "date_s"]
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df["date_g"] = pd.to_datetime(df["date_g"])
        return df.dropna(subset=["close"]).sort_values("date_g")[["date_g", "close"]]

    coffee = _load("coffee").rename(columns={"close": "coffee_gbp"})
    gbp = _load("GBP").rename(columns={"close": "gbp_irr"})
    usd = _load("USD").rename(columns={"close": "usd_irr"})

    df = (
        coffee.merge(gbp, on="date_g", how="inner")
        .merge(usd, on="date_g", how="inner")
        .sort_values("date_g")
        .set_index("date_g")
    )
    df["p_irr"] = df["coffee_gbp"] * df["gbp_irr"]
    return df


def compute_return_stats(df: pd.DataFrame):
    rets = np.log(df[["coffee_gbp", "gbp_irr"]] / df[["coffee_gbp", "gbp_irr"]].shift(1)).dropna()
    stats = {
        "mu_c": float(rets["coffee_gbp"].mean()),
        "sig_c": float(rets["coffee_gbp"].std()),
        "mu_g": float(rets["gbp_irr"].mean()),
        "sig_g": float(rets["gbp_irr"].std()),
        "corr": float(rets.corr().iloc[0, 1]),
        "n_obs": len(rets),
    }
    return stats, rets


def get_current_state(df: pd.DataFrame):
    last = df.iloc[-1]
    return {
        "coffee_gbp": float(last["coffee_gbp"]),
        "gbp_irr": float(last["gbp_irr"]),
        "usd_irr": float(last["usd_irr"]),
        "p_irr": float(last["p_irr"]),
        "date": df.index[-1],
    }


def load_config(config_path: Path):
    with open(config_path) as f:
        return yaml.safe_load(f)
