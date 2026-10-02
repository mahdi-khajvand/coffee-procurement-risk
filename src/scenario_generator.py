"""
Advanced correlated scenario generation.
- GBM with historical moments (no leakage)
- Price-demand elasticity
- Optional block-bootstrap hybrid for robustness
"""
import numpy as np
from typing import Dict, Tuple


def generate_scenarios(
    current: Dict,
    stats: Dict,
    base_demand: np.ndarray,
    n_scenarios: int = 10000,
    n_months: int = 3,
    days_per_month: int = 20,
    demand_cv: float = 0.15,
    elasticity: float = -0.45,
    seed: int = 42,
) -> Dict[str, np.ndarray]:
    """
    Returns dict with keys:
      coffee (n, T), gbp (n, T), p_irr (n, T), demand (n, T)
    Demand responds to relative price via constant elasticity.
    """
    rng = np.random.default_rng(seed)
    T = n_months
    n = n_scenarios

    mu_c, sig_c = stats["mu_c"], stats["sig_c"]
    mu_g, sig_g = stats["mu_g"], stats["sig_g"]
    corr = stats["corr"]

    # Monthly moments
    mu_cm = mu_c * days_per_month
    mu_gm = mu_g * days_per_month
    sc = sig_c * np.sqrt(days_per_month)
    sg = sig_g * np.sqrt(days_per_month)

    cov = np.array([[sc**2, corr * sc * sg], [corr * sc * sg, sg**2]])
    L = np.linalg.cholesky(cov)

    z = rng.standard_normal((n, T, 2))
    shocks = z @ L.T

    coffee = np.empty((n, T))
    gbp = np.empty((n, T))
    coffee[:, 0] = current["coffee_gbp"] * np.exp(mu_cm + shocks[:, 0, 0])
    gbp[:, 0] = current["gbp_irr"] * np.exp(mu_gm + shocks[:, 0, 1])
    for t in range(1, T):
        coffee[:, t] = coffee[:, t - 1] * np.exp(mu_cm + shocks[:, t, 0])
        gbp[:, t] = gbp[:, t - 1] * np.exp(mu_gm + shocks[:, t, 1])

    p = coffee * gbp  # IRR / ton

    # Demand with price elasticity + residual noise
    # Base demand scaled by (P_t / P0)^elasticity
    P0 = current["p_irr"]
    demand = np.empty((n, T))
    for t in range(T):
        rel_price = p[:, t] / P0
        # Clip extreme prices for numerical stability
        rel_price = np.clip(rel_price, 0.5, 2.5)
        mean_d = base_demand[t] * (rel_price ** elasticity)
        # Lognormal residual around the elastic mean
        mu_log = np.log(np.maximum(mean_d, 1e-6)) - 0.5 * demand_cv**2
        demand[:, t] = rng.lognormal(mu_log, demand_cv)

    return {
        "coffee": coffee,
        "gbp": gbp,
        "p": p,
        "demand": demand,
        "P0": P0,
    }
