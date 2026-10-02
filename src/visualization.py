"""
Professional visualizations for client presentation.
"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")
import seaborn as sns
from pathlib import Path
from typing import Dict, List

sns.set_theme(style="whitegrid", context="talk", font_scale=0.9)
COLORS = sns.color_palette("husl", 10)


def plot_cost_distributions(
    results: Dict[str, Dict],
    out_path: Path,
    title: str = "Distribution of Total Economic Cost by Policy",
):
    fig, ax = plt.subplots(figsize=(12, 6))
    for i, (name, res) in enumerate(results.items()):
        costs = res["total"] / 1e9
        sns.kdeplot(costs, ax=ax, label=name, color=COLORS[i % len(COLORS)], linewidth=2.2, fill=True, alpha=0.25)
    ax.set_xlabel("Total Economic Cost (billion IRR)")
    ax.set_ylabel("Density")
    ax.set_title(title, fontweight="bold")
    ax.legend(loc="upper right", frameon=True)
    ax.axvline(0, color="gray", ls="--", alpha=0.5)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_cvar_comparison(
    metrics_list: List[Dict],
    out_path: Path,
):
    names = [m["Policy"] for m in metrics_list]
    e_cost = [m["E_Cost"] for m in metrics_list]
    cvar = [m["CVaR_95"] for m in metrics_list]
    so = [m["Stockout_Prob"] * 100 for m in metrics_list]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # E[Cost]
    axes[0].barh(names, e_cost, color=COLORS[0])
    axes[0].set_xlabel("E[Cost] (bn IRR)")
    axes[0].set_title("Expected Cost", fontweight="bold")

    # CVaR
    axes[1].barh(names, cvar, color=COLORS[2])
    axes[1].set_xlabel("CVaR 95% (bn IRR)")
    axes[1].set_title("Tail Risk (CVaR₉₅)", fontweight="bold")

    # Stockout
    axes[2].barh(names, so, color=COLORS[4])
    axes[2].set_xlabel("Stockout Probability (%)")
    axes[2].set_title("Service Level Risk", fontweight="bold")

    for ax in axes:
        ax.invert_yaxis()
    fig.suptitle("Risk-Return Profile of Procurement Policies", fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_efficient_frontier(
    metrics_list: List[Dict],
    out_path: Path,
):
    fig, ax = plt.subplots(figsize=(9, 7))
    e = np.array([m["E_Cost"] for m in metrics_list])
    c = np.array([m["CVaR_95"] for m in metrics_list])
    so = np.array([m["Stockout_Prob"] * 100 for m in metrics_list])
    names = [m["Policy"] for m in metrics_list]

    sc = ax.scatter(e, c, c=so, s=180, cmap="RdYlGn_r", edgecolors="k", linewidths=0.8, zorder=5)
    for i, name in enumerate(names):
        ax.annotate(name, (e[i], c[i]), textcoords="offset points", xytext=(8, 5), fontsize=9)
    cbar = plt.colorbar(sc, ax=ax)
    cbar.set_label("Stockout Probability (%)")
    ax.set_xlabel("Expected Cost (bn IRR)")
    ax.set_ylabel("CVaR 95% (bn IRR)")
    ax.set_title("Efficient Frontier: Expected Cost vs Tail Risk\n(color = stockout %)", fontweight="bold")
    ax.grid(True, alpha=0.4)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_inventory_paths(
    results: Dict[str, Dict],
    out_path: Path,
    n_sample: int = 200,
):
    """Fan chart style average inventory path + uncertainty band."""
    fig, axes = plt.subplots(1, len(results), figsize=(4 * len(results), 4), sharey=True)
    if len(results) == 1:
        axes = [axes]
    for ax, (name, res) in zip(axes, results.items()):
        I = res["inventory_path"]  # (n, T+1)
        mean = I.mean(axis=0)
        p10 = np.percentile(I, 10, axis=0)
        p90 = np.percentile(I, 90, axis=0)
        months = np.arange(I.shape[1])
        ax.fill_between(months, p10, p90, alpha=0.3, color=COLORS[0])
        ax.plot(months, mean, "o-", color=COLORS[0], lw=2, label="Mean")
        # sample paths
        idx = np.random.choice(I.shape[0], min(n_sample, I.shape[0]), replace=False)
        for i in idx:
            ax.plot(months, I[i], color="gray", alpha=0.05, lw=0.6)
        ax.set_title(name, fontsize=11)
        ax.set_xlabel("Month")
        ax.set_xticks(months)
    axes[0].set_ylabel("Inventory (ton)")
    fig.suptitle("Inventory Trajectories under Uncertainty", fontweight="bold")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_cost_components(
    metrics_list: List[Dict],
    out_path: Path,
):
    """Stacked bar of average cost components."""
    names = [m["Policy"] for m in metrics_list]
    purch = np.array([m["E_Purchase"] for m in metrics_list])
    emerg = np.array([m["E_Emergency"] for m in metrics_list])
    hold = np.array([m["E_Holding"] for m in metrics_list])
    fin = np.array([m["E_Financing"] for m in metrics_list])
    term = np.array([m["E_Terminal"] for m in metrics_list])

    fig, ax = plt.subplots(figsize=(11, 6))
    x = np.arange(len(names))
    w = 0.6
    ax.bar(x, purch, w, label="Purchase", color="#4C72B0")
    ax.bar(x, emerg, w, bottom=purch, label="Emergency", color="#C44E52")
    ax.bar(x, hold, w, bottom=purch + emerg, label="Holding", color="#55A868")
    ax.bar(x, fin, w, bottom=purch + emerg + hold, label="Financing", color="#8172B2")
    # Terminal as negative (credit)
    ax.bar(x, -term, w, bottom=0, label="−Terminal Value", color="#CCB974", alpha=0.7)

    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=25, ha="right")
    ax.set_ylabel("bn IRR")
    ax.set_title("Decomposition of Expected Economic Cost", fontweight="bold")
    ax.legend(loc="upper right", ncol=2)
    ax.axhline(0, color="k", lw=0.8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_price_demand_scatter(scens: Dict, out_path: Path):
    """Show the built-in price elasticity effect."""
    fig, ax = plt.subplots(figsize=(8, 6))
    # sample 2000 points from month 1
    idx = np.random.choice(scens["p"].shape[0], 2000, replace=False)
    ax.scatter(scens["p"][idx, 0] / 1e9, scens["demand"][idx, 0], alpha=0.25, s=12, c=COLORS[1])
    ax.set_xlabel("Coffee Price (bn IRR / ton)")
    ax.set_ylabel("Demand (ton)")
    ax.set_title("Price → Demand Elasticity in Scenarios\n(ε ≈ −0.45)", fontweight="bold")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
