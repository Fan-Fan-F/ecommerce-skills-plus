#!/usr/bin/env python3
"""
TikTok Shop Profit Calculator - Core Engine
Tailored for TikTok Shop merchants and social commerce creators.

Features:
- Platform commission & transaction fees
- Creator affiliate commission modeling (open/target collaboration)
- FBT (Fulfilled by TikTok) vs Merchant self-fulfillment costs
- Impulse-buy return rate & damaged goods modeling
- Break-even selling price and target margin recommendations
- Bilingual report generation (English and Chinese)

Version: 1.1.0 (Enhanced for TikTok Shop)
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
class TikTokProductInput:
    """TikTok Shop Product input data"""
    sku: str = "TTS001"
    name: str = "Viral Beauty LED Mirror"
    selling_price: float = 34.99
    product_cost: float = 7.50           # FOB manufacturing cost
    inbound_shipping: float = 1.80       # Shipping to fulfillment center
    fbt_fulfillment_fee: float = 4.20    # FBT or 3PL pick, pack & delivery
    storage_fee: float = 0.25            # Monthly storage per unit
    platform_commission_rate: float = 0.06 # TikTok Shop platform commission (6%)
    affiliate_commission_rate: float = 0.12 # Creator affiliate commission (12%)
    transaction_fee_rate: float = 0.02   # Payment processing fee (2%)
    ad_spend_ratio: float = 0.08         # Shopping Ads (PSA/VSA) spend ratio
    creator_sample_cost_ratio: float = 0.02 # Free samples to creators
    return_rate: float = 0.07            # Return rate (7% for social commerce)
    return_processing_fee: float = 2.50  # Return inspection & restocking
    other_fees: float = 0.50             # Custom packaging box
    monthly_sales: int = 1000
    fixed_costs: float = 0.0


@dataclass
class TikTokCostBreakdown:
    selling_price: float
    product_cost: float
    inbound_shipping: float
    fbt_fulfillment_fee: float
    storage_fee: float
    platform_commission: float
    affiliate_commission: float
    transaction_fee: float
    ad_cost: float
    creator_sample_cost: float
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
            self.fbt_fulfillment_fee +
            self.storage_fee +
            self.platform_commission +
            self.affiliate_commission +
            self.transaction_fee +
            self.ad_cost +
            self.creator_sample_cost +
            self.return_cost +
            self.other_fees
        )
        self.gross_profit = self.selling_price - self.product_cost - self.inbound_shipping - self.fbt_fulfillment_fee - self.platform_commission
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
class TikTokAnalysisResult:
    product: TikTokProductInput
    cost_breakdown: TikTokCostBreakdown
    break_even: BreakEvenAnalysis
    pricing_suggestions: List[PricingSuggestion]
    status: ProfitStatus
    summary: str


def calculate_costs(product: TikTokProductInput) -> TikTokCostBreakdown:
    sp = product.selling_price
    platform_comm = sp * product.platform_commission_rate
    affiliate_comm = sp * product.affiliate_commission_rate
    trans_fee = sp * product.transaction_fee_rate
    ad_cost = sp * product.ad_spend_ratio
    sample_cost = sp * product.creator_sample_cost_ratio
    return_cost = product.return_rate * (product.return_processing_fee + product.product_cost * 0.5)

    return TikTokCostBreakdown(
        selling_price=sp,
        product_cost=product.product_cost,
        inbound_shipping=product.inbound_shipping,
        fbt_fulfillment_fee=product.fbt_fulfillment_fee,
        storage_fee=product.storage_fee,
        platform_commission=round(platform_comm, 2),
        affiliate_commission=round(affiliate_comm, 2),
        transaction_fee=round(trans_fee, 2),
        ad_cost=round(ad_cost, 2),
        creator_sample_cost=round(sample_cost, 2),
        return_cost=round(return_cost, 2),
        other_fees=product.other_fees,
    )


def calculate_break_even(product: TikTokProductInput, costs: TikTokCostBreakdown) -> BreakEvenAnalysis:
    fixed_unit_cost = (
        product.product_cost +
        product.inbound_shipping +
        product.fbt_fulfillment_fee +
        product.storage_fee +
        product.other_fees +
        costs.return_cost
    )
    variable_rate = (
        product.platform_commission_rate +
        product.affiliate_commission_rate +
        product.transaction_fee_rate +
        product.ad_spend_ratio +
        product.creator_sample_cost_ratio
    )
    denominator = 1 - variable_rate
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


def calculate_pricing_suggestions(product: TikTokProductInput, target_margins: List[float] = None) -> List[PricingSuggestion]:
    if target_margins is None:
        target_margins = [0.15, 0.20, 0.25, 0.30]

    return_cost = product.return_rate * (product.return_processing_fee + product.product_cost * 0.5)
    fixed_unit_cost = (
        product.product_cost +
        product.inbound_shipping +
        product.fbt_fulfillment_fee +
        product.storage_fee +
        product.other_fees +
        return_cost
    )
    variable_rate = (
        product.platform_commission_rate +
        product.affiliate_commission_rate +
        product.transaction_fee_rate +
        product.ad_spend_ratio +
        product.creator_sample_cost_ratio
    )

    suggestions = []
    for target in target_margins:
        denominator = 1 - target - variable_rate
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


def analyze_product(product: TikTokProductInput, target_margins: List[float] = None) -> TikTokAnalysisResult:
    costs = calculate_costs(product)
    be = calculate_break_even(product, costs)
    pricing = calculate_pricing_suggestions(product, target_margins)
    status = evaluate_profit_status(costs.net_margin)
    summary = f"Net Margin {costs.net_margin*100:.1f}% | Profit/Unit ${costs.net_profit:.2f}"
    return TikTokAnalysisResult(
        product=product,
        cost_breakdown=costs,
        break_even=be,
        pricing_suggestions=pricing,
        status=status,
        summary=summary
    )


def format_report(result: TikTokAnalysisResult, lang: str = "en") -> str:
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
            "| 目标净利率 | 建议标价 | 单件净利润 |",
            "|------------|----------|------------|",
        ]
        for s in result.pricing_suggestions:
            suggestions_lines.append(f"| {s.target_margin*100:.0f}% | ${s.suggested_price:.2f} | ${s.profit_per_unit:.2f} |")

        return f"""
🎵 **TikTok Shop 爆款利润与保本分析报告**

**商品**: {result.product.name} ({result.product.sku})
**状态**: {status_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **成本结构拆解 (TikTok Shop Unit Economics)**

```
商品售价 (Price)          ${c.selling_price:.2f}   100.0%
────────────────────────────────────────
商品采购成本 (FOB)        -${c.product_cost:.2f}    {c.product_cost/sp*100:.1f}%
头程干线运费 (Inbound)    -${c.inbound_shipping:.2f}     {c.inbound_shipping/sp*100:.1f}%
FBT/3PL履约配送 (Shipping)-${c.fbt_fulfillment_fee:.2f}    {c.fbt_fulfillment_fee/sp*100:.1f}%
仓储租金 (Storage)        -${c.storage_fee:.2f}     {c.storage_fee/sp*100:.1f}%
TikTok平台佣金 (Commission)-${c.platform_commission:.2f}     {c.platform_commission/sp*100:.1f}%
达人分销带货佣金 (Affiliate)-${c.affiliate_commission:.2f}    {c.affiliate_commission/sp*100:.1f}%
支付交易手续费 (Gateway)  -${c.transaction_fee:.2f}     {c.transaction_fee/sp*100:.1f}%
TikTok投流广告 (Ads)      -${c.ad_cost:.2f}     {c.ad_cost/sp*100:.1f}%
达人寄样与公关成本 (Sample)-${c.creator_sample_cost:.2f}     {c.creator_sample_cost/sp*100:.1f}%
冲动消费退款货损 (Returns)-${c.return_cost:.2f}     {c.return_cost/sp*100:.1f}%
定制包装防震 (Packaging)  -${c.other_fees:.2f}     {c.other_fees/sp*100:.1f}%
────────────────────────────────────────
总营业成本 (Total Cost)   ${c.total_cost:.2f}    {c.total_cost/sp*100:.1f}%
实际净利润 (Net Profit)   ${c.net_profit:.2f}    {c.net_margin*100:.1f}%
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 **保本点分析 (Break-Even)**

保本售价: ${be.min_price:.2f} (低于此售价将亏损)
当前售价: ${c.selling_price:.2f} (高于保本价 {be.current_margin_above_min*100:.1f}%)
安全边际率: {be.safety_margin*100:.1f}% (预留达人加码与折扣空间)

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
🎵 **TikTok Shop Profit Analysis Report**

**Product**: {result.product.name} ({result.product.sku})
**Status**: {status_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **Cost Breakdown (TikTok Shop Economics)**

```
Selling Price (Price)   ${c.selling_price:.2f}   100.0%
────────────────────────────────────────
Product Cost (FOB)      -${c.product_cost:.2f}    {c.product_cost/sp*100:.1f}%
Inbound Shipping        -${c.inbound_shipping:.2f}     {c.inbound_shipping/sp*100:.1f}%
FBT/3PL Fulfillment     -${c.fbt_fulfillment_fee:.2f}    {c.fbt_fulfillment_fee/sp*100:.1f}%
Storage Fee             -${c.storage_fee:.2f}     {c.storage_fee/sp*100:.1f}%
TikTok Platform Fee     -${c.platform_commission:.2f}     {c.platform_commission/sp*100:.1f}%
Creator Affiliate Fee   -${c.affiliate_commission:.2f}    {c.affiliate_commission/sp*100:.1f}%
Transaction Fee         -${c.transaction_fee:.2f}     {c.transaction_fee/sp*100:.1f}%
TikTok Shopping Ads     -${c.ad_cost:.2f}     {c.ad_cost/sp*100:.1f}%
Creator Samples & Seed  -${c.creator_sample_cost:.2f}     {c.creator_sample_cost/sp*100:.1f}%
Returns & Damages       -${c.return_cost:.2f}     {c.return_cost/sp*100:.1f}%
Packaging & Insert      -${c.other_fees:.2f}     {c.other_fees/sp*100:.1f}%
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
  --demo            Run standard TikTok Shop demo product
  --zh              Output report in Chinese
  --json <string>   Pass JSON object with TikTok Shop parameters
  --help, -h        Show this help message
""")
        return

    test_product = TikTokProductInput()
    if len(args) > 0 and args[0] != "--demo":
        try:
            data = json.loads(args[0])
            test_product = TikTokProductInput(**data)
        except Exception as e:
            print(f"Error parsing JSON input: {e}")
            sys.exit(1)

    result = analyze_product(test_product)
    print(format_report(result, lang=lang))


if __name__ == "__main__":
    main()
