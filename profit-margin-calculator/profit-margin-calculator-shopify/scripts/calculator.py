#!/usr/bin/env python3
"""
Shopify DTC Profit Calculator - Core Engine
Tailored for Direct-to-Consumer (DTC) e-commerce brands on Shopify.

Features:
- DTC Unit economics (COGS, 3PL pick/pack, payment gateway, ad spend/CAC)
- Shopify Payments fee calculation (2.9% + $0.30 standard)
- Store subscription and app stack fee allocation
- Break-even analysis and target margin pricing
- Bilingual report generation (English and Chinese)

Version: 1.1.0 (Enhanced for Shopify DTC)
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


@dataclass
class ShopifyProductInput:
    """Shopify DTC Product input data"""
    sku: str = "DTC001"
    name: str = "Premium Leather Wallet"
    selling_price: float = 49.99
    product_cost: float = 12.00          # FOB manufacturing cost
    inbound_shipping: float = 2.00       # Freight to domestic 3PL warehouse
    fulfillment_fee: float = 5.50        # 3PL pick, pack & domestic shipping
    storage_fee: float = 0.35            # Monthly 3PL warehousing per unit
    payment_rate: float = 0.029          # Shopify Payments rate (2.9%)
    payment_fixed: float = 0.30          # Gateway fixed fee ($0.30)
    shopify_plan_fee: float = 0.50       # Shopify subscription & apps cost per unit
    ad_spend_ratio: float = 0.22         # DTC Ad Spend (Meta/Google CAC ratio)
    return_rate: float = 0.04            # Return rate (4%)
    return_processing_fee: float = 3.50  # Return label & inspection
    other_fees: float = 0.75             # Custom unboxing packaging, insert cards
    monthly_sales: int = 500
    fixed_costs: float = 0.0


@dataclass
class ShopifyCostBreakdown:
    selling_price: float
    product_cost: float
    inbound_shipping: float
    fulfillment_fee: float
    storage_fee: float
    payment_fee: float
    shopify_plan_fee: float
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
            self.fulfillment_fee +
            self.storage_fee +
            self.payment_fee +
            self.shopify_plan_fee +
            self.ad_cost +
            self.return_cost +
            self.other_fees
        )
        self.gross_profit = self.selling_price - self.product_cost - self.inbound_shipping - self.fulfillment_fee
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
class ShopifyAnalysisResult:
    product: ShopifyProductInput
    cost_breakdown: ShopifyCostBreakdown
    break_even: BreakEvenAnalysis
    pricing_suggestions: List[PricingSuggestion]
    status: ProfitStatus
    summary: str


def calculate_costs(product: ShopifyProductInput) -> ShopifyCostBreakdown:
    payment_fee = product.selling_price * product.payment_rate + product.payment_fixed
    ad_cost = product.selling_price * product.ad_spend_ratio
    return_cost = product.return_rate * (product.return_processing_fee + product.product_cost * 0.5)

    return ShopifyCostBreakdown(
        selling_price=product.selling_price,
        product_cost=product.product_cost,
        inbound_shipping=product.inbound_shipping,
        fulfillment_fee=product.fulfillment_fee,
        storage_fee=product.storage_fee,
        payment_fee=round(payment_fee, 2),
        shopify_plan_fee=product.shopify_plan_fee,
        ad_cost=round(ad_cost, 2),
        return_cost=round(return_cost, 2),
        other_fees=product.other_fees,
    )


def calculate_break_even(product: ShopifyProductInput, costs: ShopifyCostBreakdown) -> BreakEvenAnalysis:
    fixed_unit_cost = (
        product.product_cost +
        product.inbound_shipping +
        product.fulfillment_fee +
        product.storage_fee +
        product.payment_fixed +
        product.shopify_plan_fee +
        product.other_fees +
        costs.return_cost
    )
    denominator = 1 - product.payment_rate - product.ad_spend_ratio
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


def calculate_pricing_suggestions(product: ShopifyProductInput, target_margins: List[float] = None) -> List[PricingSuggestion]:
    if target_margins is None:
        target_margins = [0.15, 0.20, 0.25, 0.30]

    return_cost = product.return_rate * (product.return_processing_fee + product.product_cost * 0.5)
    fixed_unit_cost = (
        product.product_cost +
        product.inbound_shipping +
        product.fulfillment_fee +
        product.storage_fee +
        product.payment_fixed +
        product.shopify_plan_fee +
        product.other_fees +
        return_cost
    )

    suggestions = []
    for target in target_margins:
        denominator = 1 - target - product.payment_rate - product.ad_spend_ratio
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


def analyze_product(product: ShopifyProductInput, target_margins: List[float] = None) -> ShopifyAnalysisResult:
    costs = calculate_costs(product)
    be = calculate_break_even(product, costs)
    pricing = calculate_pricing_suggestions(product, target_margins)
    status = evaluate_profit_status(costs.net_margin)
    summary = f"Net Margin {costs.net_margin*100:.1f}% | Profit/Unit ${costs.net_profit:.2f}"
    return ShopifyAnalysisResult(
        product=product,
        cost_breakdown=costs,
        break_even=be,
        pricing_suggestions=pricing,
        status=status,
        summary=summary
    )


def format_report(result: ShopifyAnalysisResult, lang: str = "en") -> str:
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
🛍️ **Shopify DTC 独立站利润与保本分析报告**

**商品**: {result.product.name} ({result.product.sku})
**状态**: {status_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **成本结构明细 (DTC Unit Economics)**

```
商品零售价 (AOV)         ${c.selling_price:.2f}   100.0%
────────────────────────────────────────
商品采购成本 (COGS)       -${c.product_cost:.2f}    {c.product_cost/sp*100:.1f}%
头程干线运费 (Inbound)    -${c.inbound_shipping:.2f}     {c.inbound_shipping/sp*100:.1f}%
3PL 仓配履约 (Pick&Pack) -${c.fulfillment_fee:.2f}    {c.fulfillment_fee/sp*100:.1f}%
3PL 仓储租金 (Storage)   -${c.storage_fee:.2f}     {c.storage_fee/sp*100:.1f}%
支付网关手续费 (Stripe)   -${c.payment_fee:.2f}     {c.payment_fee/sp*100:.1f}%
Shopify月租与SaaS分摊    -${c.shopify_plan_fee:.2f}     {c.shopify_plan_fee/sp*100:.1f}%
Meta/Google广告费 (CAC)   -${c.ad_cost:.2f}    {c.ad_cost/sp*100:.1f}%
退换货成本损耗 (Returns)  -${c.return_cost:.2f}     {c.return_cost/sp*100:.1f}%
品牌包装与卡片 (Unboxing) -${c.other_fees:.2f}     {c.other_fees/sp*100:.1f}%
────────────────────────────────────────
总营业成本 (Total Cost)   ${c.total_cost:.2f}    {c.total_cost/sp*100:.1f}%
实际净利润 (Net Profit)   ${c.net_profit:.2f}    {c.net_margin*100:.1f}%
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 **保本点分析 (Break-Even)**

保本售价: ${be.min_price:.2f} (低于此售价将亏损)
当前售价: ${c.selling_price:.2f} (高于保本价 {be.current_margin_above_min*100:.1f}%)
安全边际率: {be.safety_margin*100:.1f}% (降价促销缓冲空间)

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
🛍️ **Shopify DTC Profit Analysis Report**

**Product**: {result.product.name} ({result.product.sku})
**Status**: {status_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **Cost Breakdown (DTC Unit Economics)**

```
Selling Price (AOV)     ${c.selling_price:.2f}   100.0%
────────────────────────────────────────
Product Cost (COGS)     -${c.product_cost:.2f}    {c.product_cost/sp*100:.1f}%
Inbound Shipping        -${c.inbound_shipping:.2f}     {c.inbound_shipping/sp*100:.1f}%
3PL Pick & Pack         -${c.fulfillment_fee:.2f}    {c.fulfillment_fee/sp*100:.1f}%
3PL Storage Fee         -${c.storage_fee:.2f}     {c.storage_fee/sp*100:.1f}%
Payment Gateway Fee     -${c.payment_fee:.2f}     {c.payment_fee/sp*100:.1f}%
Shopify Plan & Apps     -${c.shopify_plan_fee:.2f}     {c.shopify_plan_fee/sp*100:.1f}%
Ad Spend / CAC          -${c.ad_cost:.2f}    {c.ad_cost/sp*100:.1f}%
Returns & Damages       -${c.return_cost:.2f}     {c.return_cost/sp*100:.1f}%
Packaging & Inserts     -${c.other_fees:.2f}     {c.other_fees/sp*100:.1f}%
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
  --demo            Run standard Shopify DTC demo product
  --zh              Output report in Chinese
  --json <string>   Pass JSON object with Shopify parameters
  --help, -h        Show this help message
""")
        return

    test_product = ShopifyProductInput()
    if len(args) > 0 and args[0] != "--demo":
        try:
            data = json.loads(args[0])
            test_product = ShopifyProductInput(**data)
        except Exception as e:
            print(f"Error parsing JSON input: {e}")
            sys.exit(1)

    result = analyze_product(test_product)
    print(format_report(result, lang=lang))


if __name__ == "__main__":
    main()
