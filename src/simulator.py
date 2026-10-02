"""
Inventory dynamics + economic cost engine.
Locked accounting formula with full mark-to-market of inventory.
Inflation/FX appreciation of inventory is captured via Terminal Value
and intermediate mark-to-market financing on market value.
"""
import numpy as np
from typing import Dict, Optional, Tuple


def simulate_fixed_policy(
    Q: np.ndarray,
    scens: Dict[str, np.ndarray],
    I0: float,
    h: float,
    lam: float,
    r: float,
    capacity: float,
) -> Dict[str, np.ndarray]:
    """
    Fixed (open-loop) procurement plan Q = [Q1, Q2, Q3].
    Returns full cost components and diagnostics for every scenario.
    """
    p = scens["p"]
    D = scens["demand"]
    n, T = p.shape
    Q = np.asarray(Q, dtype=float)

    I = np.zeros((n, T + 1))
    I[:, 0] = I0
    S = np.zeros((n, T))
    purch = np.zeros(n)
    emerg = np.zeros(n)
    hold = np.zeros(n)
    fin = np.zeros(n)
    cash = np.zeros(n)
    q_eff = np.zeros((n, T))

    for t in range(T):
        # Capacity constraint
        avail = np.maximum(0.0, capacity - I[:, t])
        qe = np.minimum(Q[t], avail)
        q_eff[:, t] = qe

        net = I[:, t] + qe - D[:, t]
        S[:, t] = np.maximum(0.0, -net)
        I[:, t + 1] = np.maximum(0.0, net)

        purch += qe * p[:, t]
        emerg += S[:, t] * p[:, t] * (1.0 + lam)
        hold += I[:, t + 1] * h
        # Financing on end-of-month market value (captures capital tied + inflation effect)
        fin += I[:, t + 1] * p[:, t] * r
        cash += qe * p[:, t]

    terminal = I[:, T] * p[:, T - 1]
    total = purch + emerg + hold + fin - terminal
    stockout = (S.sum(axis=1) > 1e-8).astype(float)

    return {
        "total": total,
        "purchase": purch,
        "emergency": emerg,
        "holding": hold,
        "financing": fin,
        "terminal": terminal,
        "stockout": stockout,
        "ending_I": I[:, T],
        "cash": cash,
        "shortages": S,
        "inventory_path": I,
        "q_effective": q_eff,
    }


def simulate_adaptive_policy(
    scens: Dict[str, np.ndarray],
    I0: float,
    h: float,
    lam: float,
    r: float,
    capacity: float,
    base_demand: np.ndarray,
    safety_stock: float = 15.0,
    elasticity: float = -0.45,
    P0: float = None,
) -> Dict[str, np.ndarray]:
    """
    Adaptive (closed-loop) policy:
    At the beginning of each month t, given current inventory I_{t-1}
    and the realized price path so far, decide Q_t to target
    remaining expected demand + safety stock, adjusted for price elasticity
    and remaining horizon.
    
    This is a practical Model-Predictive style heuristic that re-plans
    every period with the latest information (no look-ahead into future
    price/demand realizations beyond the current month).
    """
    p = scens["p"]
    D = scens["demand"]  # for evaluation only; decisions do not see future D
    n, T = p.shape
    if P0 is None:
        P0 = p[:, 0].mean()  # fallback

    I = np.zeros((n, T + 1))
    I[:, 0] = I0
    S = np.zeros((n, T))
    purch = np.zeros(n)
    emerg = np.zeros(n)
    hold = np.zeros(n)
    fin = np.zeros(n)
    cash = np.zeros(n)
    Q_decided = np.zeros((n, T))

    for t in range(T):
        # --- Decision based on information available at t ---
        # Current inventory and current price (already realized for month t)
        remaining_horizon = T - t
        # Expected remaining demand under current relative price
        rel = np.clip(p[:, t] / P0, 0.5, 2.5)
        expected_remaining = 0.0
        for k in range(t, T):
            expected_remaining += base_demand[k] * (rel ** elasticity)
        # Target ending inventory after this purchase: safety stock scaled by remaining months
        target_end = safety_stock * (remaining_horizon / T)
        needed = expected_remaining + target_end - I[:, t]
        Q_t = np.maximum(0.0, needed)
        # Capacity
        avail = np.maximum(0.0, capacity - I[:, t])
        Q_t = np.minimum(Q_t, avail)
        Q_decided[:, t] = Q_t

        # --- Transition (now demand realizes) ---
        net = I[:, t] + Q_t - D[:, t]
        S[:, t] = np.maximum(0.0, -net)
        I[:, t + 1] = np.maximum(0.0, net)

        purch += Q_t * p[:, t]
        emerg += S[:, t] * p[:, t] * (1.0 + lam)
        hold += I[:, t + 1] * h
        fin += I[:, t + 1] * p[:, t] * r
        cash += Q_t * p[:, t]

    terminal = I[:, T] * p[:, T - 1]
    total = purch + emerg + hold + fin - terminal
    stockout = (S.sum(axis=1) > 1e-8).astype(float)

    return {
        "total": total,
        "purchase": purch,
        "emergency": emerg,
        "holding": hold,
        "financing": fin,
        "terminal": terminal,
        "stockout": stockout,
        "ending_I": I[:, T],
        "cash": cash,
        "shortages": S,
        "inventory_path": I,
        "Q_decided": Q_decided,
    }
