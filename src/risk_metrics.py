"""
Risk metrics: Expected Cost, VaR, CVaR, Stockout, etc.
"""
import numpy as np
from typing import Dict


def compute_metrics(res: Dict[str, np.ndarray], alpha: float = 0.95, budget: float = None) -> Dict:
    c = res["total"]
    metrics = {
        "E_Cost": float(c.mean()),
        "Median_Cost": float(np.median(c)),
        "Std_Cost": float(c.std()),
        "Stockout_Prob": float(res["stockout"].mean()),
        f"VaR_{int(alpha*100)}": float(np.quantile(c, alpha)),
        f"CVaR_{int(alpha*100)}": float(c[c >= np.quantile(c, alpha)].mean()),
        "E_Ending_I": float(res["ending_I"].mean()),
        "E_Cash": float(res["cash"].mean()),
        "E_Emergency": float(res["emergency"].mean()),
        "E_Holding": float(res["holding"].mean()),
        "E_Financing": float(res["financing"].mean()),
        "E_Terminal": float(res["terminal"].mean()),
        "E_Purchase": float(res["purchase"].mean()),
    }
    if budget is not None:
        metrics["P_Over_Budget"] = float((res["cash"] > budget).mean())
    return metrics


def metrics_to_bn(m: Dict) -> Dict:
    """Convert IRR values to billion IRR for readability."""
    out = {}
    for k, v in m.items():
        if k in ("Stockout_Prob", "P_Over_Budget", "E_Ending_I"):
            out[k] = v
        else:
            out[k] = v / 1e9
    return out
