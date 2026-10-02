#!/usr/bin/env python3
"""
Coffee Import Decision System under Uncertainty
Iran | Advanced Monte-Carlo + Adaptive Policies + Risk Metrics
"""
from pathlib import Path
import sys
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.data_loader import load_raw_series, compute_return_stats, get_current_state, load_config
from src.scenario_generator import generate_scenarios
from src.simulator import simulate_fixed_policy, simulate_adaptive_policy
from src.risk_metrics import compute_metrics, metrics_to_bn
from src.visualization import (
    plot_cost_distributions,
    plot_cvar_comparison,
    plot_efficient_frontier,
    plot_inventory_paths,
    plot_cost_components,
    plot_price_demand_scatter,
)

def main():
    print("=" * 72)
    print("  COFFEE PROCUREMENT RISK SYSTEM  |  Iran  |  Decision under Uncertainty")
    print("=" * 72)

    cfg = load_config(ROOT / "config" / "params.yaml")
    biz = cfg["business"]
    sim = cfg["simulation"]

    # ---------- Data ----------
    df = load_raw_series(ROOT / "data")
    stats, rets = compute_return_stats(df)
    current = get_current_state(df)

    print(f"\n[Market] Decision date : {current['date'].date()}")
    print(f"         Coffee        : {current['coffee_gbp']:.0f} GBP/ton")
    print(f"         GBP/IRR       : {current['gbp_irr']:,.0f}")
    print(f"         Price         : {current['p_irr']/1e9:.3f} bn IRR/ton")
    print(f"[Stats]  μ_c={stats['mu_c']:.5f}  σ_c={stats['sig_c']:.5f}")
    print(f"         μ_g={stats['mu_g']:.5f}  σ_g={stats['sig_g']:.5f}  ρ={stats['corr']:.3f}")

    # ---------- Scenarios ----------
    print(f"\n[Scenarios] Generating {sim['n_scenarios']:,} correlated paths ...")
    scens = generate_scenarios(
        current=current,
        stats=stats,
        base_demand=np.array(biz["base_demand"]),
        n_scenarios=sim["n_scenarios"],
        n_months=sim["n_months"],
        days_per_month=sim["trading_days_per_month"],
        demand_cv=biz["demand_cv"],
        elasticity=biz["price_elasticity"],
        seed=sim["seed"],
    )
    print(f"         Mean P by month (bn): {(scens['p'].mean(0)/1e9).round(3)}")
    print(f"         Mean D by month     : {scens['demand'].mean(0).round(1)}")

    # ---------- Policies ----------
    fixed_policies = {
        "A_BuyNow":          np.array([70.0, 0.0, 0.0]),
        "B_Wait":            np.array([0.0, 30.0, 40.0]),
        "C_Split":           np.array([35.0, 15.0, 20.0]),
        "D_FrontLoad":       np.array([50.0, 15.0, 15.0]),
        "E_SafetyStock":     np.array([45.0, 20.0, 25.0]),
        "F_HeavyFront":      np.array([60.0, 20.0, 10.0]),
        "G_Balanced":        np.array([30.0, 30.0, 30.0]),
    }

    results = {}
    metrics_rows = []

    print("\n[Simulation] Fixed policies ...")
    for name, Q in fixed_policies.items():
        res = simulate_fixed_policy(
            Q=Q,
            scens=scens,
            I0=biz["initial_inventory_ton"],
            h=biz["holding_cost_irr_per_ton_month"],
            lam=biz["emergency_premium"],
            r=biz["cost_of_capital_monthly"],
            capacity=biz["warehouse_capacity_ton"],
        )
        results[name] = res
        m = compute_metrics(res, alpha=sim["cvar_alpha"], budget=biz["budget_max_irr"])
        m_bn = metrics_to_bn(m)
        m_bn["Policy"] = name
        m_bn["Type"] = "Fixed"
        m_bn["Q"] = list(Q)
        metrics_rows.append(m_bn)
        print(f"  {name:<18} E[Cost]={m_bn['E_Cost']:7.2f}  CVaR95={m_bn['CVaR_95']:7.2f}  SO%={m_bn['Stockout_Prob']*100:5.1f}")

    # Adaptive policy
    print("\n[Simulation] Adaptive (MPC-style) policy ...")
    res_ad = simulate_adaptive_policy(
        scens=scens,
        I0=biz["initial_inventory_ton"],
        h=biz["holding_cost_irr_per_ton_month"],
        lam=biz["emergency_premium"],
        r=biz["cost_of_capital_monthly"],
        capacity=biz["warehouse_capacity_ton"],
        base_demand=np.array(biz["base_demand"]),
        safety_stock=biz["safety_stock_target"],
        elasticity=biz["price_elasticity"],
        P0=scens["P0"],
    )
    results["H_Adaptive"] = res_ad
    m = compute_metrics(res_ad, alpha=sim["cvar_alpha"], budget=biz["budget_max_irr"])
    m_bn = metrics_to_bn(m)
    m_bn["Policy"] = "H_Adaptive"
    m_bn["Type"] = "Adaptive"
    m_bn["Q"] = "dynamic"
    metrics_rows.append(m_bn)
    print(f"  {'H_Adaptive':<18} E[Cost]={m_bn['E_Cost']:7.2f}  CVaR95={m_bn['CVaR_95']:7.2f}  SO%={m_bn['Stockout_Prob']*100:5.1f}")

    # ---------- Tables ----------
    summary = pd.DataFrame(metrics_rows)
    # reorder columns
    cols = ["Policy", "Type", "E_Cost", "Median_Cost", "CVaR_95", "VaR_95",
            "Stockout_Prob", "E_Ending_I", "E_Cash", "E_Emergency",
            "E_Holding", "E_Financing", "E_Terminal", "E_Purchase", "P_Over_Budget"]
    summary = summary[[c for c in cols if c in summary.columns]]
    summary_path = ROOT / "outputs" / "tables" / "policy_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"\n[Output] Summary table → {summary_path}")

    # Detailed Excel
    with pd.ExcelWriter(ROOT / "outputs" / "tables" / "full_results.xlsx") as writer:
        summary.to_excel(writer, sheet_name="Summary", index=False)
        # cost quantiles
        qdf = pd.DataFrame({
            name: np.quantile(results[name]["total"] / 1e9, [0.05, 0.25, 0.5, 0.75, 0.95])
            for name in results
        }, index=["P5", "P25", "P50", "P75", "P95"]).T
        qdf.to_excel(writer, sheet_name="Cost_Quantiles")
        # mean adaptive Q
        if "Q_decided" in results["H_Adaptive"]:
            aq = pd.DataFrame({
                "Month": [1, 2, 3],
                "Mean_Q": results["H_Adaptive"]["Q_decided"].mean(0),
                "Std_Q": results["H_Adaptive"]["Q_decided"].std(0),
            })
            aq.to_excel(writer, sheet_name="Adaptive_Q", index=False)

    # ---------- Figures ----------
    fig_dir = ROOT / "outputs" / "figures"
    print("[Output] Generating figures ...")
    plot_cost_distributions(results, fig_dir / "01_cost_distributions.png")
    plot_cvar_comparison(metrics_rows, fig_dir / "02_risk_metrics.png")
    plot_efficient_frontier(metrics_rows, fig_dir / "03_efficient_frontier.png")
    plot_inventory_paths(results, fig_dir / "04_inventory_paths.png")
    plot_cost_components(metrics_rows, fig_dir / "05_cost_decomposition.png")
    plot_price_demand_scatter(scens, fig_dir / "06_price_elasticity.png")

    # ---------- Insight text ----------
    best_e = summary.loc[summary["E_Cost"].idxmin()]
    best_cvar = summary.loc[summary["CVaR_95"].idxmin()]
    best_so = summary.loc[summary["Stockout_Prob"].idxmin()]

    insights = f"""
# Executive Insights – Coffee Procurement under Uncertainty

## Market Context
- Decision date: {current['date'].date()}
- Spot price: {current['p_irr']/1e9:.3f} bn IRR / ton
- Calibrated on {stats['n_obs']} daily observations (Farvardin–Tir 1401)
- Price paths embed historical FX drift → nominal inventory appreciation is material

## Accounting Engine
TotalEconomicCost = Purchase + Emergency + Holding + Financing − TerminalInventoryValue
- Terminal value marks remaining inventory to the final month market price
- Financing charged on market value each month → captures opportunity cost & inflation effect
- Inventory held through FX depreciation/appreciation therefore has an economic P&L impact that can exceed pure holding cost

## Demand Response
Price elasticity ε = {biz['price_elasticity']} → higher local prices reduce demand endogenously

## Ranking Highlights
| Criterion              | Winner              | Value                  |
|------------------------|---------------------|------------------------|
| Lowest Expected Cost   | {best_e['Policy']:<19} | {best_e['E_Cost']:.2f} bn IRR |
| Lowest Tail Risk (CVaR)| {best_cvar['Policy']:<19} | {best_cvar['CVaR_95']:.2f} bn IRR |
| Lowest Stockout Prob   | {best_so['Policy']:<19} | {best_so['Stockout_Prob']*100:.1f}% |

## Key Trade-offs for Management
1. **Wait (B)** often looks good on average cost when prices drift up slowly, but produces the highest stockout probability and the worst CVaR — unacceptable for a service-sensitive importer.
2. **Front-loaded / Safety-stock policies** sacrifice a few billion IRR of expected cost to buy a large reduction in tail risk and near-zero stockouts.
3. **Adaptive policy** re-plans every month with the latest inventory & price information. It typically dominates pure fixed plans on the risk-adjusted frontier because it can buy less when prices spike and more when they soften, while protecting the service level.
4. Holding inventory is not pure cost: under the observed FX drift the mark-to-market gain can more than offset the 50 m IRR/ton/month holding cost, turning inventory into a partial inflation hedge.

## Recommendation Framework
- If risk tolerance is low (CVaR constraint or max stockout ≤ 5 %) → Adaptive or Heavy-Front / SafetyStock
- If cash is extremely tight → Split or Balanced with tighter budget constraint
- Always evaluate the full distribution, never a single forecast point

Generated automatically by the Coffee Risk Decision System v1.0
"""
    (ROOT / "outputs" / "reports" / "executive_insights.md").write_text(insights)
    print(insights)

    # Save raw scenario sample for transparency
    np.savez_compressed(
        ROOT / "outputs" / "tables" / "scenario_sample.npz",
        p=scens["p"][:500],
        demand=scens["demand"][:500],
        coffee=scens["coffee"][:500],
        gbp=scens["gbp"][:500],
    )

    print("\n" + "=" * 72)
    print("  ALL OUTPUTS WRITTEN TO outputs/")
    print("  Ready for GitHub / client presentation")
    print("=" * 72)


if __name__ == "__main__":
    main()
