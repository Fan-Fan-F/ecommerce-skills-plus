#!/usr/bin/env python3
"""
Temu Profit Calculator - Core Engine
Tailored for Temu cross-border e-commerce sellers.

Features:
- Full-Managed Mode (全托管供货模式: 申报供货价、国内集运仓头程、质检罚款预留、售后货损)
- Semi-Managed Mode (半托管海外仓模式: 零售价USD、海外仓尾程派送、仅退款风险预留)
- Dual currency calculations (CNY / USD)
- Break-even quote / selling price calculation
- Bilingual report generation (English and Chinese)

Version: 1.0.0
"""

import json
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class TemuMode(Enum):
    FULL_MANAGED = "full_managed"   # 全托管供货
    SEMI_MANAGED = "semi_managed"   # 半托管本地履约


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
class TemuProductInput:
    sku: str = "TMU001"
    name: str = "Portable Wireless Blender"
    mode: str = "full_managed"
    # Exchange rate USD to CNY
    exchange_rate: float = 7.25

    # Full-managed fields (CNY)
    supply_price_cny: float = 38.00         # 商家供货价 (申报核价)
    product_cost_cny: float = 22.00        # 出厂采购成本 (FOB)
    domestic_shipping_cny: float = 1.50    # 发往Temu国内集运仓快递费 (单件分摊)
    packaging_cny: float = 1.00            # 条码贴标与定制透明袋包装
    quality_penalty_rate: float = 0.03     # 质检扣款/延误发货违规罚款预留 (3%)
    return_refund_loss_rate: float = 0.04  # 消费者售后退款/仅退款货损预留 (4%)

    # Semi-managed fields (USD)
    selling_price_usd: float = 18.99       # 前端零售售价 (USD)
    inbound_freight_usd: float = 1.80      # 海运头程至海外仓 (USD)
    local_delivery_usd: float = 4.20       # 海外仓一件代发尾程 (USD)
    storage_fee_usd: float = 0.20          # 海外仓月度仓储 (USD)
    platform_take_rate: float = 0.05       # 平台技术服务抽成 (5%)


@dataclass
class TemuCostBreakdown:
    mode: str
    revenue: float
    product_cost: float
    shipping_cost: float
    packaging_cost: float
    penalty_loss: float
    return_refund_loss: float
    platform_fee: float
    total_cost: float
    net_profit: float
    net_margin: float
    currency: str


@dataclass
class BreakEvenAnalysis:
    min_price: float
    safety_margin: float
    current_margin_above_min: float
    currency: str


@dataclass
class PricingSuggestion:
    target_margin: float
    suggested_price: float
    profit_per_unit: float
    currency: str


@dataclass
class TemuAnalysisResult:
    product: TemuProductInput
    cost_breakdown: TemuCostBreakdown
    break_even: BreakEvenAnalysis
    pricing_suggestions: List[PricingSuggestion]
    status: ProfitStatus
    summary: str


def calculate_costs_full_managed(product: TemuProductInput) -> TemuCostBreakdown:
    sp = product.supply_price_cny
    penalty_loss = sp * product.quality_penalty_rate
    return_loss = sp * product.return_refund_loss_rate
    total_cost = (
        product.product_cost_cny +
        product.domestic_shipping_cny +
        product.packaging_cny +
        penalty_loss +
        return_loss
    )
    net_profit = sp - total_cost
    net_margin = net_profit / sp if sp > 0 else 0

    return TemuCostBreakdown(
        mode="full_managed",
        revenue=sp,
        product_cost=product.product_cost_cny,
        shipping_cost=product.domestic_shipping_cny,
        packaging_cost=product.packaging_cny,
        penalty_loss=round(penalty_loss, 2),
        return_refund_loss=round(return_loss, 2),
        platform_fee=0.0,
        total_cost=round(total_cost, 2),
        net_profit=round(net_profit, 2),
        net_margin=net_margin,
        currency="CNY"
    )


def calculate_costs_semi_managed(product: TemuProductInput) -> TemuCostBreakdown:
    sp = product.selling_price_usd
    prod_cost_usd = product.product_cost_cny / product.exchange_rate
    platform_fee = sp * product.platform_take_rate
    refund_loss = sp * product.return_refund_loss_rate

    total_cost = (
        prod_cost_usd +
        product.inbound_freight_usd +
        product.local_delivery_usd +
        product.storage_fee_usd +
        platform_fee +
        refund_loss
    )
    net_profit = sp - total_cost
    net_margin = net_profit / sp if sp > 0 else 0

    return TemuCostBreakdown(
        mode="semi_managed",
        revenue=sp,
        product_cost=round(prod_cost_usd, 2),
        shipping_cost=round(product.inbound_freight_usd + product.local_delivery_usd, 2),
        packaging_cost=round(product.storage_fee_usd, 2),
        penalty_loss=0.0,
        return_refund_loss=round(refund_loss, 2),
        platform_fee=round(platform_fee, 2),
        total_cost=round(total_cost, 2),
        net_profit=round(net_profit, 2),
        net_margin=net_margin,
        currency="USD"
    )


def calculate_break_even(product: TemuProductInput, costs: TemuCostBreakdown) -> BreakEvenAnalysis:
    if product.mode == "full_managed":
        fixed_cny = product.product_cost_cny + product.domestic_shipping_cny + product.packaging_cny
        rate = product.quality_penalty_rate + product.return_refund_loss_rate
        denom = 1 - rate
        min_price = fixed_cny / denom if denom > 0 else fixed_cny * 1.5
        curr_price = product.supply_price_cny
        curr = "CNY"
    else:
        prod_cost_usd = product.product_cost_cny / product.exchange_rate
        fixed_usd = prod_cost_usd + product.inbound_freight_usd + product.local_delivery_usd + product.storage_fee_usd
        rate = product.platform_take_rate + product.return_refund_loss_rate
        denom = 1 - rate
        min_price = fixed_usd / denom if denom > 0 else fixed_usd * 1.5
        curr_price = product.selling_price_usd
        curr = "USD"

    safety_margin = (curr_price - min_price) / curr_price if curr_price > 0 else 0
    margin_above_min = (curr_price - min_price) / min_price if min_price > 0 else 0

    return BreakEvenAnalysis(
        min_price=round(min_price, 2),
        safety_margin=round(safety_margin, 4),
        current_margin_above_min=round(margin_above_min, 4),
        currency=curr
    )


def calculate_pricing_suggestions(product: TemuProductInput) -> List[PricingSuggestion]:
    targets = [0.15, 0.20, 0.25, 0.30]
    suggestions = []

    if product.mode == "full_managed":
        fixed_cny = product.product_cost_cny + product.domestic_shipping_cny + product.packaging_cny
        rate = product.quality_penalty_rate + product.return_refund_loss_rate
        curr = "CNY"
        for t in targets:
            denom = 1 - t - rate
            if denom > 0:
                s_price = fixed_cny / denom
                suggestions.append(PricingSuggestion(
                    target_margin=t,
                    suggested_price=round(s_price, 2),
                    profit_per_unit=round(s_price * t, 2),
                    currency=curr
                ))
    else:
        prod_cost_usd = product.product_cost_cny / product.exchange_rate
        fixed_usd = prod_cost_usd + product.inbound_freight_usd + product.local_delivery_usd + product.storage_fee_usd
        rate = product.platform_take_rate + product.return_refund_loss_rate
        curr = "USD"
        for t in targets:
            denom = 1 - t - rate
            if denom > 0:
                s_price = fixed_usd / denom
                suggestions.append(PricingSuggestion(
                    target_margin=t,
                    suggested_price=round(s_price, 2),
                    profit_per_unit=round(s_price * t, 2),
                    currency=curr
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


def analyze_product(product: TemuProductInput) -> TemuAnalysisResult:
    if product.mode == "semi_managed":
        costs = calculate_costs_semi_managed(product)
    else:
        costs = calculate_costs_full_managed(product)

    be = calculate_break_even(product, costs)
    pricing = calculate_pricing_suggestions(product)
    status = evaluate_profit_status(costs.net_margin)
    sym = "¥" if costs.currency == "CNY" else "$"
    summary = f"Net Margin {costs.net_margin*100:.1f}% | Profit/Unit {sym}{costs.net_profit:.2f}"

    return TemuAnalysisResult(
        product=product,
        cost_breakdown=costs,
        break_even=be,
        pricing_suggestions=pricing,
        status=status,
        summary=summary
    )


def format_report(result: TemuAnalysisResult, lang: str = "en") -> str:
    status_icons = {
        ProfitStatus.HEALTHY: "✅",
        ProfitStatus.WARNING: "⚠️",
        ProfitStatus.DANGER: "🔴",
        ProfitStatus.LOSS: "💀",
    }
    c = result.cost_breakdown
    be = result.break_even
    sym = "¥" if c.currency == "CNY" else "$"

    if lang == "zh":
        mode_zh = "全托管供货模式" if c.mode == "full_managed" else "半托管海外仓自履约模式"
        status_text_zh = {
            ProfitStatus.HEALTHY: "健康良好",
            ProfitStatus.WARNING: "微利预警",
            ProfitStatus.DANGER: "亏损边缘",
            ProfitStatus.LOSS: "亏损倒贴",
        }
        status_str = f"{status_icons[result.status]} {status_text_zh[result.status]} | 净利率 {c.net_margin*100:.1f}% | 单件净利 {sym}{c.net_profit:.2f}"

        if c.mode == "full_managed":
            breakdown_lines = [
                f"Temu 申报供货价 (Quote)  {sym}{c.revenue:.2f}   100.0%",
                "────────────────────────────────────────",
                f"出厂采购成本 (FOB)        -{sym}{c.product_cost:.2f}    {c.product_cost/c.revenue*100:.1f}%",
                f"集运仓国内快递 (Logistics)-{sym}{c.shipping_cost:.2f}     {c.shipping_cost/c.revenue*100:.1f}%",
                f"贴标与外箱耗材 (Package)  -{sym}{c.packaging_cost:.2f}     {c.packaging_cost/c.revenue*100:.1f}%",
                f"质检扣款/违规罚款预留    -{sym}{c.penalty_loss:.2f}     {c.penalty_loss/c.revenue*100:.1f}%",
                f"售后退款/货损折旧预留    -{sym}{c.return_refund_loss:.2f}     {c.return_refund_loss/c.revenue*100:.1f}%",
                "────────────────────────────────────────",
                f"综合营业总成本           {sym}{c.total_cost:.2f}    {c.total_cost/c.revenue*100:.1f}%",
                f"供货实际净利润           {sym}{c.net_profit:.2f}    {c.net_margin*100:.1f}%"
            ]
        else:
            breakdown_lines = [
                f"Temu 零售标价 (Retail)    {sym}{c.revenue:.2f}   100.0%",
                "────────────────────────────────────────",
                f"采购成本换算 (COGS)       -{sym}{c.product_cost:.2f}    {c.product_cost/c.revenue*100:.1f}%",
                f"海运头程+尾程派送 (Ship)  -{sym}{c.shipping_cost:.2f}    {c.shipping_cost/c.revenue*100:.1f}%",
                f"海外仓仓储费 (Storage)    -{sym}{c.packaging_cost:.2f}     {c.packaging_cost/c.revenue*100:.1f}%",
                f"平台技术服务抽成 (5%)     -{sym}{c.platform_fee:.2f}     {c.platform_fee/c.revenue*100:.1f}%",
                f"仅退款与售后货损预留      -{sym}{c.return_refund_loss:.2f}     {c.return_refund_loss/c.revenue*100:.1f}%",
                "────────────────────────────────────────",
                f"综合营业总成本           {sym}{c.total_cost:.2f}    {c.total_cost/c.revenue*100:.1f}%",
                f"实际净利润               {sym}{c.net_profit:.2f}    {c.net_margin*100:.1f}%"
            ]

        suggestions_lines = [
            f"| 目标净利率 | 建议报价 ({c.currency}) | 单件净利润 |",
            "|------------|----------------|------------|",
        ]
        for s in result.pricing_suggestions:
            suggestions_lines.append(f"| {s.target_margin*100:.0f}% | {sym}{s.suggested_price:.2f} | {sym}{s.profit_per_unit:.2f} |")

        return f"""
💰 **Temu 跨境电商利润与供货核价分析报告**

**商品名称**: {result.product.name} ({result.product.sku})
**运营模式**: {mode_zh}
**结算币种**: {c.currency} (USD/CNY 汇率: {result.product.exchange_rate:.2f})
**财务状态**: {status_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **成本结构明细**

```
{chr(10).join(breakdown_lines)}
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 **保本核价分析 (Break-Even)**

保本底价: {sym}{be.min_price:.2f} (低于此申报供货价将出现亏损)
当前价格: {sym}{c.revenue:.2f} (高于保本价 {be.current_margin_above_min*100:.1f}%)
安全边际率: {be.safety_margin*100:.1f}% (抗平台多次压价缓冲空间)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 **目标净利率供货报价建议**

{chr(10).join(suggestions_lines)}
"""

    mode_en = "Full-Managed Mode" if c.mode == "full_managed" else "Semi-Managed Mode"
    status_str = f"{status_icons[result.status]} {result.status.value.title()} | Net Margin {c.net_margin*100:.1f}% | Profit/Unit {sym}{c.net_profit:.2f}"

    if c.mode == "full_managed":
        breakdown_lines = [
            f"Temu Supply Price       {sym}{c.revenue:.2f}   100.0%",
            "────────────────────────────────────────",
            f"FOB Sourcing Cost        -{sym}{c.product_cost:.2f}    {c.product_cost/c.revenue*100:.1f}%",
            f"Domestic Transit Freight -{sym}{c.shipping_cost:.2f}     {c.shipping_cost/c.revenue*100:.1f}%",
            f"Labeling & Packaging     -{sym}{c.packaging_cost:.2f}     {c.packaging_cost/c.revenue*100:.1f}%",
            f"Quality Penalty Reserve  -{sym}{c.penalty_loss:.2f}     {c.penalty_loss/c.revenue*100:.1f}%",
            f"Return & Damage Reserve  -{sym}{c.return_refund_loss:.2f}     {c.return_refund_loss/c.revenue*100:.1f}%",
            "────────────────────────────────────────",
            f"Total Operating Cost     {sym}{c.total_cost:.2f}    {c.total_cost/c.revenue*100:.1f}%",
            f"Net Supply Profit        {sym}{c.net_profit:.2f}    {c.net_margin*100:.1f}%"
        ]
    else:
        breakdown_lines = [
            f"Temu Retail Price        {sym}{c.revenue:.2f}   100.0%",
            "────────────────────────────────────────",
            f"COGS (Converted to USD)  -{sym}{c.product_cost:.2f}    {c.product_cost/c.revenue*100:.1f}%",
            f"Inbound & Local Delivery -{sym}{c.shipping_cost:.2f}    {c.shipping_cost/c.revenue*100:.1f}%",
            f"Overseas Warehouse Rent  -{sym}{c.packaging_cost:.2f}     {c.packaging_cost/c.revenue*100:.1f}%",
            f"Platform Fee (5%)        -{sym}{c.platform_fee:.2f}     {c.platform_fee/c.revenue*100:.1f}%",
            f"Refund Loss Reserve      -{sym}{c.return_refund_loss:.2f}     {c.return_refund_loss/c.revenue*100:.1f}%",
            "────────────────────────────────────────",
            f"Total Operating Cost     {sym}{c.total_cost:.2f}    {c.total_cost/c.revenue*100:.1f}%",
            f"Net Operating Profit     {sym}{c.net_profit:.2f}    {c.net_margin*100:.1f}%"
        ]

    suggestions_lines = [
        f"| Target Margin | Suggested Price ({c.currency}) | Profit/Unit |",
        "|---------------|-----------------------|-------------|",
    ]
    for s in result.pricing_suggestions:
        suggestions_lines.append(f"| {s.target_margin*100:.0f}% | {sym}{s.suggested_price:.2f} | {sym}{s.profit_per_unit:.2f} |")

    return f"""
💰 **Temu Cross-Border Profit Analysis Report**

**Product**: {result.product.name} ({result.product.sku})
**Mode**: {mode_en}
**Currency**: {c.currency} (USD/CNY Rate: {result.product.exchange_rate:.2f})
**Status**: {status_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **Cost Breakdown**

```
{chr(10).join(breakdown_lines)}
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 **Break-Even Analysis**

Break-even Price: {sym}{be.min_price:.2f} (Minimum quote to avoid loss)
Current Price: {sym}{c.revenue:.2f} ({be.current_margin_above_min*100:.1f}% above break-even)
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
  --demo            Run standard Temu full-managed demo product
  --zh              Output report in Chinese
  --json <string>   Pass JSON object with Temu parameters
  --help, -h        Show this help message
""")
        return

    test_product = TemuProductInput()
    if len(args) > 0 and args[0] != "--demo":
        try:
            data = json.loads(args[0])
            test_product = TemuProductInput(**data)
        except Exception as e:
            print(f"Error parsing JSON input: {e}")
            sys.exit(1)

    result = analyze_product(test_product)
    print(format_report(result, lang=lang))


if __name__ == "__main__":
    main()
