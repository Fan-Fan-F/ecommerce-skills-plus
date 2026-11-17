#!/usr/bin/env python3
"""
Walmart Marketplace Profit Calculator - Core Engine
Tailored for Walmart Marketplace sellers using Walmart Fulfillment Services (WFS) or seller fulfillment.

Features:
- Walmart category commission tiers (6% - 15%)
- WFS (Walmart Fulfillment Services) pick, pack & storage schedule
- Walmart Connect advertising ad spend ratio
- Break-even calculation & target margin recommendations
- Bilingual report generation (English and Chinese)

Version: 1.1.0 (Enhanced for Walmart Marketplace)
"""

import json
import csv
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import sys


class ProfitStatus(Enum):
    HEALTHY = "healthy"      # >20% net margin
    WARNING = "warning"      # 8-20% net margin
    DANGER = "danger"        # 0-8% net margin
    LOSS = "loss"            # Negative margin


PROFIT_THRESHOLDS = {
    "healthy": 0.20,
    "warning": 0.08,
    "danger": 0.00,
}

WALMART_COMMISSION_RATES = {
    "default": 0.15,
    "apparel": 0.15,
    "beauty": 0.15,
    "electronics": 0.08,
    "computers": 0.08,
    "camera": 0.08,
    "home": 0.15,
    "kitchen": 0.15,
    "toys": 0.15,
    "automotive": 0.12,
    "grocery": 0.15,
    "sports": 0.15,
}


@dataclass
class WalmartProductInput:
    """Walmart Marketplace Product input data"""
    sku: str = "WMT001"
    name: str = "Stainless Steel Cookware Set"
    selling_price: float = 39.99
    product_cost: float = 9.00           # FOB manufacturing cost
    inbound_shipping: float = 2.20       # Freight to WFS fulfillment center
    wfs_fulfillment_fee: float = 6.45    # WFS pick, pack & delivery fee
    wfs_storage_fee: float = 0.40        # Monthly WFS storage fee per unit
    category: str = "kitchen"            # Category for Walmart commission
    custom_referral_rate: Optional[float] = None
    ad_spend_ratio: float = 0.10         # Walmart Connect ad spend ratio
    return_rate: float = 0.04            # Return rate
    return_processing_fee: float = 2.50  # Return restocking/inspection fee
    other_fees: float = 0.50             # Packaging / barcode labels
    monthly_sales: int = 400
    fixed_costs: float = 0.0


@dataclass
class WalmartCostBreakdown:
    selling_price: float
    product_cost: float
    inbound_shipping: float
    wfs_fulfillment_fee: float
    wfs_storage_fee: float
    referral_fee: float
    ad_cost: float
    return_cost: float
    other_fees: float
    total_cost: float = 0.0
    gross_profit: float = 0.0
    net_profit: float = 0.0
    gross_margin: float = 0.0
    net_margin: float = 0.0

    def __post_init__(self):
        self.total_cost = (
            self.product_cost +
            self.inbound_shipping +
            self.wfs_fulfillment_fee +
            self.wfs_storage_fee +
            self.referral_fee +
            self.ad_cost +
            self.return_cost +
            self.other_fees
        )
        self.gross_profit = self.selling_price - self.product_cost - self.inbound_shipping - self.wfs_fulfillment_fee - self.referral_fee
        self.net_profit = self.selling_price - self.total_cost
        self.gross_margin = self.gross_profit / self.selling_price if self.selling_price > 0 else 0
        self.net_margin = self.net_profit / self.selling_price if self.selling_price > 0 else 0


@dataclass
class BreakEvenAnalysis:
    min_price: float
    break_even_units: int
    safety_margin: float
    current_margin_above_min: float


@dataclass
class PricingSuggestion:
    target_margin: float
    suggested_price: float
    profit_per_unit: float


@dataclass
class WalmartAnalysisResult:
    product: WalmartProductInput
    cost_breakdown: WalmartCostBreakdown
    break_even: BreakEvenAnalysis
    pricing_suggestions: List[PricingSuggestion]
    status: ProfitStatus
    summary: str


def get_commission_rate(category: str, custom_rate: Optional[float] = None) -> float:
    if custom_rate is not None:
        return custom_rate
    return WALMART_COMMISSION_RATES.get(category.lower(), WALMART_COMMISSION_RATES["default"])


def calculate_costs(product: WalmartProductInput) -> WalmartCostBreakdown:
    sp = product.selling_price
    rate = get_commission_rate(product.category, product.custom_referral_rate)
    referral_fee = sp * rate
    ad_cost = sp * product.ad_spend_ratio
    return_cost = product.return_rate * (product.return_processing_fee + product.product_cost * 0.5)

    return WalmartCostBreakdown(
        selling_price=sp,
        product_cost=product.product_cost,
        inbound_shipping=product.inbound_shipping,
        wfs_fulfillment_fee=product.wfs_fulfillment_fee,
        wfs_storage_fee=product.wfs_storage_fee,
        referral_fee=round(referral_fee, 2),
        ad_cost=round(ad_cost, 2),
        return_cost=round(return_cost, 2),
        other_fees=product.other_fees,
    )


def calculate_break_even(product: WalmartProductInput, costs: WalmartCostBreakdown) -> BreakEvenAnalysis:
    rate = get_commission_rate(product.category, product.custom_referral_rate)
    fixed_unit_cost = (
        product.product_cost +
        product.inbound_shipping +
        product.wfs_fulfillment_fee +
        product.wfs_storage_fee +
        product.other_fees +
        costs.return_cost
    )
    denominator = 1 - rate - product.ad_spend_ratio
    if denominator > 0:
        min_price = fixed_unit_cost / denominator
    else:
        min_price = fixed_unit_cost * 2

    if product.fixed_costs > 0 and costs.net_profit > 0:
        break_even_units = int(product.fixed_costs / costs.net_profit) + 1
    else:
        break_even_units = 0

    safety_margin = (product.selling_price - min_price) / product.selling_price if product.selling_price > 0 else 0
    margin_above_min = (product.selling_price - min_price) / min_price if min_price > 0 else 0

    return BreakEvenAnalysis(
        min_price=round(min_price, 2),
        break_even_units=break_even_units,
        safety_margin=round(safety_margin, 4),
        current_margin_above_min=round(margin_above_min, 4)
    )


def calculate_pricing_suggestions(product: WalmartProductInput, target_margins: List[float] = None) -> List[PricingSuggestion]:
    if target_margins is None:
        target_margins = [0.15, 0.20, 0.25, 0.30]

    rate = get_commission_rate(product.category, product.custom_referral_rate)
    return_cost = product.return_rate * (product.return_processing_fee + product.product_cost * 0.5)
    fixed_unit_cost = (
        product.product_cost +
        product.inbound_shipping +
        product.wfs_fulfillment_fee +
        product.wfs_storage_fee +
        product.other_fees +
        return_cost
    )

    suggestions = []
    for target in target_margins:
        denominator = 1 - target - rate - product.ad_spend_ratio
        if denominator > 0:
            suggested_price = fixed_unit_cost / denominator
            suggestions.append(PricingSuggestion(
                target_margin=target,
                suggested_price=round(suggested_price, 2),
                profit_per_unit=round(suggested_price * target, 2)
            ))
    return suggestions


def evaluate_profit_status(net_margin: float) -> ProfitStatus:
    if net_margin < 0:
        return ProfitStatus.LOSS
    elif net_margin < PROFIT_THRESHOLDS["warning"]:
        return ProfitStatus.DANGER
    elif net_margin < PROFIT_THRESHOLDS["healthy"]:
        return ProfitStatus.WARNING
    return ProfitStatus.HEALTHY


def analyze_product(product: WalmartProductInput, target_margins: List[float] = None) -> WalmartAnalysisResult:
    costs = calculate_costs(product)
    be = calculate_break_even(product, costs)
    pricing = calculate_pricing_suggestions(product, target_margins)
    status = evaluate_profit_status(costs.net_margin)
    summary = f"Net Margin {costs.net_margin*100:.1f}% | Profit/Unit ${costs.net_profit:.2f}"
    return WalmartAnalysisResult(
        product=product,
        cost_breakdown=costs,
        break_even=be,
        pricing_suggestions=pricing,
        status=status,
        summary=summary
    )


def format_report(result: WalmartAnalysisResult, lang: str = "en") -> str:
    status_icons = {
        ProfitStatus.HEALTHY: "✅",
        ProfitStatus.WARNING: "⚠️",
        ProfitStatus.DANGER: "🔴",
        ProfitStatus.LOSS: "💀",
    }
    c = result.cost_breakdown
    be = result.break_even
    sp = c.selling_price if c.selling_price > 0 else 1.0

    if lang == "zh":
        status_text_zh = {
            ProfitStatus.HEALTHY: "健康良好",
            ProfitStatus.WARNING: "中度预警",
            ProfitStatus.DANGER: "低利危险",
            ProfitStatus.LOSS: "严重亏损",
        }
        status_str = f"{status_icons[result.status]} {status_text_zh[result.status]} | 净利率 {c.net_margin*100:.1f}% | 单件净利 ${c.net_profit:.2f}"

        suggestions_lines = [
            "| 目标净利率 | 建议零售价 | 单件净利润 |",
            "|------------|------------|------------|",
        ]
        for s in result.pricing_suggestions:
            suggestions_lines.append(f"| {s.target_margin*100:.0f}% | ${s.suggested_price:.2f} | ${s.profit_per_unit:.2f} |")

        return f"""
🏬 **Walmart Marketplace 利润与保本分析报告**

**商品**: {result.product.name} ({result.product.sku})
**类目**: {result.product.category}
**状态**: {status_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **成本结构拆解 (Walmart Unit Economics)**

```
商品零售价 (Price)        ${c.selling_price:.2f}   100.0%
────────────────────────────────────────
商品采购成本 (FOB)        -${c.product_cost:.2f}    {c.product_cost/sp*100:.1f}%
头程海空运费 (Inbound)    -${c.inbound_shipping:.2f}     {c.inbound_shipping/sp*100:.1f}%
WFS 官方履约费 (Delivery) -${c.wfs_fulfillment_fee:.2f}    {c.wfs_fulfillment_fee/sp*100:.1f}%
WFS 月度仓储费 (Storage)  -${c.wfs_storage_fee:.2f}     {c.wfs_storage_fee/sp*100:.1f}%
Walmart平台佣金 (Referral)-${c.referral_fee:.2f}    {c.referral_fee/sp*100:.1f}%
Walmart Connect广告支出   -${c.ad_cost:.2f}    {c.ad_cost/sp*100:.1f}%
退货货损与再上架 (Returns)-${c.return_cost:.2f}     {c.return_cost/sp*100:.1f}%
其他包装耗材 (Packaging)  -${c.other_fees:.2f}     {c.other_fees/sp*100:.1f}%
────────────────────────────────────────
总运营成本 (Total Cost)   ${c.total_cost:.2f}    {c.total_cost/sp*100:.1f}%
实际净利润 (Net Profit)   ${c.net_profit:.2f}    {c.net_margin*100:.1f}%
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 **保本点分析 (Break-Even)**

保本售价: ${be.min_price:.2f} (低于此售价将亏损)
当前售价: ${c.selling_price:.2f} (高于保本价 {be.current_margin_above_min*100:.1f}%)
安全边际率: {be.safety_margin*100:.1f}% (抗价格战与促销降价空间)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 **目标净利率定价建议**

{chr(10).join(suggestions_lines)}
"""

    status_str = f"{status_icons[result.status]} {result.status.value.title()} | Net Margin {c.net_margin*100:.1f}% | Profit/Unit ${c.net_profit:.2f}"
    suggestions_lines = [
        "| Target Margin | Recommended Price | Profit/Unit |",
        "|---------------|-------------------|-------------|",
    ]
    for s in result.pricing_suggestions:
        suggestions_lines.append(f"| {s.target_margin*100:.0f}% | ${s.suggested_price:.2f} | ${s.profit_per_unit:.2f} |")

    return f"""
🏬 **Walmart Marketplace Profit Analysis Report**

**Product**: {result.product.name} ({result.product.sku})
**Category**: {result.product.category}
**Status**: {status_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **Cost Breakdown (Walmart Economics)**

```
Selling Price (Price)   ${c.selling_price:.2f}   100.0%
────────────────────────────────────────
Product Cost (FOB)      -${c.product_cost:.2f}    {c.product_cost/sp*100:.1f}%
Inbound Shipping        -${c.inbound_shipping:.2f}     {c.inbound_shipping/sp*100:.1f}%
WFS Fulfillment Fee     -${c.wfs_fulfillment_fee:.2f}    {c.wfs_fulfillment_fee/sp*100:.1f}%
WFS Monthly Storage     -${c.wfs_storage_fee:.2f}     {c.wfs_storage_fee/sp*100:.1f}%
Walmart Commission      -${c.referral_fee:.2f}    {c.referral_fee/sp*100:.1f}%
Walmart Connect Ads     -${c.ad_cost:.2f}    {c.ad_cost/sp*100:.1f}%
Returns & Restocking    -${c.return_cost:.2f}     {c.return_cost/sp*100:.1f}%
Packaging & Labels      -${c.other_fees:.2f}     {c.other_fees/sp*100:.1f}%
────────────────────────────────────────
Total Cost              ${c.total_cost:.2f}    {c.total_cost/sp*100:.1f}%
Net Profit              ${c.net_profit:.2f}    {c.net_margin*100:.1f}%
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 **Break-Even Analysis**

Break-even Price: ${be.min_price:.2f}
Current Price: ${c.selling_price:.2f} ({be.current_margin_above_min*100:.1f}% above break-even)
Safety Margin: {be.safety_margin*100:.1f}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 **Pricing Recommendations**

{chr(10).join(suggestions_lines)}
"""


def main():
    args = sys.argv[1:]
    lang = "zh" if "--zh" in args else "en"
    args = [a for a in args if a != "--zh"]

    if "--help" in args or "-h" in args:
        print("""Usage: python3 calculator.py [OPTIONS] [JSON_STRING]
Options:
  --demo            Run standard Walmart Marketplace demo product
  --zh              Output report in Chinese
  --json <string>   Pass JSON object with Walmart parameters
  --help, -h        Show this help message
""")
        return

    test_product = WalmartProductInput()
    if len(args) > 0 and args[0] != "--demo":
        try:
            data = json.loads(args[0])
            test_product = WalmartProductInput(**data)
        except Exception as e:
            print(f"Error parsing JSON input: {e}")
            sys.exit(1)

    result = analyze_product(test_product)
    print(format_report(result, lang=lang))


if __name__ == "__main__":
    main()
