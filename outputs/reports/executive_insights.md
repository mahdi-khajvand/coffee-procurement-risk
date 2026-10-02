
# Executive Insights – Coffee Procurement under Uncertainty

## Market Context
- Decision date: 2022-06-22
- Spot price: 0.822 bn IRR / ton
- Calibrated on 40 daily observations (Farvardin–Tir 1401)
- Price paths embed historical FX drift → nominal inventory appreciation is material

## Accounting Engine
TotalEconomicCost = Purchase + Emergency + Holding + Financing − TerminalInventoryValue
- Terminal value marks remaining inventory to the final month market price
- Financing charged on market value each month → captures opportunity cost & inflation effect
- Inventory held through FX depreciation/appreciation therefore has an economic P&L impact that can exceed pure holding cost

## Demand Response
Price elasticity ε = -0.45 → higher local prices reduce demand endogenously

## Ranking Highlights
| Criterion              | Winner              | Value                  |
|------------------------|---------------------|------------------------|
| Lowest Expected Cost   | B_Wait              | 62.04 bn IRR |
| Lowest Tail Risk (CVaR)| G_Balanced          | 81.55 bn IRR |
| Lowest Stockout Prob   | E_SafetyStock       | 1.8% |

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
