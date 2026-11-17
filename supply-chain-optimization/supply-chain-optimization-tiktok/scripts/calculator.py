#!/usr/bin/env python3
"""
TikTok Shop Supply Chain Analyzer - Core Calculator
Tailored for fast-paced social commerce, viral product lifecycles, and creator affiliate fulfillment.

Purpose: Calculate key TikTok Shop logistics metrics and diagnose viral stockout / cash flow bottlenecks
Version: 1.1.0 (Enhanced for TikTok Shop)
"""

import json
import sys
from dataclasses import dataclass
from typing import Optional, List, Dict
from enum import Enum


class HealthStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    DANGER = "danger"


BENCHMARKS = {
    "gross_margin": {"healthy": 0.45, "warning": 0.35, "danger": 0.25},
    "shipping_ratio": {"healthy": 0.05, "warning": 0.08, "danger": 0.12},
    "inventory_days": {"healthy": 30, "warning": 45, "danger": 60},
    "cash_cycle": {"healthy": 45, "warning": 65, "danger": 90},
    "net_margin": {"healthy": 0.18, "warning": 0.10, "danger": 0.04}
}


@dataclass
class TikTokSupplyChainInput:
    product_cost: float = 7.50
    supplier_payment_days: int = 15
    production_days: int = 12
    shipping_cost_per_unit: float = 1.80
    shipping_days: int = 18
    selling_price: float = 34.99
    fbt_fulfillment_fee: float = 4.20    # FBT or 3PL pick, pack & delivery
    storage_fee: float = 0.25            # Storage fee
    ad_spend_ratio: float = 0.08         # Shopping Ads spend
    affiliate_commission_ratio: float = 0.12 # Creator affiliate commission
    inventory_days: int = 35             # Fast turnover required for viral SKUs
    has_viral_spike_risk: bool = True    # High volatility / stockout risk
    platform: str = "tiktok"


@dataclass
class MetricResult:
    name: str
    value: float
    unit: str
    status: HealthStatus
    benchmark: float
    description: str


@dataclass 
class BottleneckItem:
    priority: int
    severity: str
    title: str
    problem: str
    impact: str
    suggestion: str


@dataclass
class AnalysisResult:
    metrics: List[MetricResult]
    cost_breakdown: Dict[str, float]
    bottlenecks: List[BottleneckItem]
    summary: str


def evaluate_status(value: float, thresholds: dict, higher_is_better: bool = True) -> HealthStatus:
    if higher_is_better:
        if value >= thresholds["healthy"]:
            return HealthStatus.HEALTHY
        elif value >= thresholds["warning"]:
            return HealthStatus.WARNING
        return HealthStatus.DANGER
    else:
        if value <= thresholds["healthy"]:
            return HealthStatus.HEALTHY
        elif value <= thresholds["warning"]:
            return HealthStatus.WARNING
        return HealthStatus.DANGER


def calculate_metrics(data: TikTokSupplyChainInput) -> List[MetricResult]:
    metrics = []
    sp = data.selling_price if data.selling_price > 0 else 1.0

    # 1. Gross Margin
    gross_profit = data.selling_price - data.product_cost - data.shipping_cost_per_unit - data.fbt_fulfillment_fee
    gross_margin = gross_profit / sp
    metrics.append(MetricResult(
        name="Gross Margin",
        value=round(gross_margin * 100, 1),
        unit="%",
        status=evaluate_status(gross_margin, BENCHMARKS["gross_margin"], higher_is_better=True),
        benchmark=BENCHMARKS["gross_margin"]["healthy"] * 100,
        description="Gross margin after product cost and FBT fulfillment"
    ))

    # 2. Inbound Freight Ratio
    shipping_ratio = data.shipping_cost_per_unit / sp
    metrics.append(MetricResult(
        name="Inbound Freight Ratio",
        value=round(shipping_ratio * 100, 1),
        unit="%",
        status=evaluate_status(shipping_ratio, BENCHMARKS["shipping_ratio"], higher_is_better=False),
        benchmark=BENCHMARKS["shipping_ratio"]["healthy"] * 100,
        description="Inbound shipping cost as % of selling price"
    ))

    # 3. Net Margin
    ad_cost = data.selling_price * data.ad_spend_ratio
    affiliate_cost = data.selling_price * data.affiliate_commission_ratio
    platform_fee = data.selling_price * 0.06
    other_cost = data.selling_price * 0.04
    net_profit = gross_profit - data.storage_fee - ad_cost - affiliate_cost - platform_fee - other_cost
    net_margin = net_profit / sp
    metrics.append(MetricResult(
        name="Net Margin",
        value=round(net_margin * 100, 1),
        unit="%",
        status=evaluate_status(net_margin, BENCHMARKS["net_margin"], higher_is_better=True),
        benchmark=BENCHMARKS["net_margin"]["healthy"] * 100,
        description="Net margin after TikTok platform fees, creator commissions & ads"
    ))

    # 4. Inventory Days
    metrics.append(MetricResult(
        name="Inventory Turnover Days",
        value=data.inventory_days,
        unit="days",
        status=evaluate_status(data.inventory_days, BENCHMARKS["inventory_days"], higher_is_better=False),
        benchmark=BENCHMARKS["inventory_days"]["healthy"],
        description="Days of inventory on hand (fast rotation required on TikTok)"
    ))

    # 5. Cash Cycle (TikTok payout cycle ~7 days)
    cash_cycle = (
        data.production_days + 
        data.shipping_days + 
        data.inventory_days + 
        7  # TikTok settlement payout cycle
        - data.supplier_payment_days
    )
    metrics.append(MetricResult(
        name="Cash-to-Cash Cycle",
        value=cash_cycle,
        unit="days",
        status=evaluate_status(cash_cycle, BENCHMARKS["cash_cycle"], higher_is_better=False),
        benchmark=BENCHMARKS["cash_cycle"]["healthy"],
        description="Working capital cycle from supplier outlay to TikTok cash settlement"
    ))

    return metrics


def calculate_cost_breakdown(data: TikTokSupplyChainInput) -> Dict[str, float]:
    ad_cost = data.selling_price * data.ad_spend_ratio
    affiliate_cost = data.selling_price * data.affiliate_commission_ratio
    platform_fee = data.selling_price * 0.06
    other_cost = data.selling_price * 0.04
    net_profit = (
        data.selling_price 
        - data.product_cost 
        - data.shipping_cost_per_unit 
        - data.fbt_fulfillment_fee 
        - data.storage_fee 
        - ad_cost 
        - affiliate_cost
        - platform_fee
        - other_cost
    )
    sp = data.selling_price if data.selling_price > 0 else 1.0

    return {
        "selling_price": data.selling_price,
        "product_cost": data.product_cost,
        "shipping_cost": data.shipping_cost_per_unit,
        "fulfillment_fee": data.fbt_fulfillment_fee,
        "storage_fee": data.storage_fee,
        "platform_fee": round(platform_fee, 2),
        "affiliate_cost": round(affiliate_cost, 2),
        "ad_cost": round(ad_cost, 2),
        "other_cost": round(other_cost, 2),
        "net_profit": round(net_profit, 2),
        "product_cost_ratio": round(data.product_cost / sp * 100, 1),
        "shipping_ratio": round(data.shipping_cost_per_unit / sp * 100, 1),
        "fulfillment_ratio": round(data.fbt_fulfillment_fee / sp * 100, 1),
        "storage_ratio": round(data.storage_fee / sp * 100, 1),
        "platform_ratio": 6.0,
        "affiliate_ratio": round(data.affiliate_commission_ratio * 100, 1),
        "ad_ratio": round(ad_cost / sp * 100, 1),
        "net_margin": round(net_profit / sp * 100, 1)
    }


def diagnose_bottlenecks(data: TikTokSupplyChainInput, metrics: List[MetricResult]) -> List[BottleneckItem]:
    bottlenecks = []
    for m in metrics:
        if m.status == HealthStatus.DANGER:
            severity = "High"
            priority = 1
        elif m.status == HealthStatus.WARNING:
            severity = "Medium"
            priority = 2
        else:
            continue

        if m.name == "Inventory Turnover Days":
            bottlenecks.append(BottleneckItem(
                priority=priority,
                severity=severity,
                title="Inventory Turnover Above Social Commerce Benchmark",
                problem=f"Current {m.value} days vs benchmark <{BENCHMARKS['inventory_days']['healthy']} days",
                impact="Risk of inventory obsolescence when short-video trends fade",
                suggestion="1. Tighten production batches to 7-10 days  2. Establish creator pre-launch sample feedback  3. Move to flexible on-demand supplier lines"
            ))
        elif m.name == "Cash-to-Cash Cycle":
            bottlenecks.append(BottleneckItem(
                priority=priority,
                severity=severity,
                title="Extended Cash Cycle for High-Velocity Platform",
                problem=f"Current {m.value} days vs benchmark <{BENCHMARKS['cash_cycle']['healthy']} days",
                impact="Slow capital turnover limits ability to re-invest in scaling ad spend and creator seeding",
                suggestion="1. Leverage TikTok fast payout feature  2. Negotiate tiered volume payments with suppliers  3. Air freight emergency batches"
            ))

    if data.has_viral_spike_risk:
        bottlenecks.append(BottleneckItem(
            priority=1,
            severity="High",
            title="Viral Traffic Surge Stockout Vulnerability",
            problem="Single trending creator video can spike orders 5-10x within 48 hours",
            impact="Stockouts degrade TikTok Shop shop performance rating and cause cancellation penalties",
            suggestion="1. Contract secondary reserve supplier  2. Keep buffer raw materials at factory  3. Set up pre-sale threshold rules"
        ))

    bottlenecks.sort(key=lambda x: x.priority)
    return bottlenecks[:3]


def analyze(data: TikTokSupplyChainInput) -> AnalysisResult:
    metrics = calculate_metrics(data)
    costs = calculate_cost_breakdown(data)
    bottlenecks = diagnose_bottlenecks(data, metrics)
    danger = sum(1 for m in metrics if m.status == HealthStatus.DANGER)
    warning = sum(1 for m in metrics if m.status == HealthStatus.WARNING)
    if danger > 0:
        summary = f"Found {danger} critical TikTok Shop supply chain risk(s)"
    elif warning > 0:
        summary = f"Found {warning} optimization opportunity(s)"
    else:
        summary = "TikTok Shop supply chain velocity is healthy and agile"
    return AnalysisResult(metrics=metrics, cost_breakdown=costs, bottlenecks=bottlenecks, summary=summary)


def format_report(result: AnalysisResult, lang: str = "en") -> str:
    status_icons = {HealthStatus.HEALTHY: "✅", HealthStatus.WARNING: "⚠️", HealthStatus.DANGER: "🔴"}
    zh_names = {
        "Gross Margin": "毛利率",
        "Inbound Freight Ratio": "头程运费占比",
        "Net Margin": "净利率",
        "Inventory Turnover Days": "爆款库存周转天数",
        "Cash-to-Cash Cycle": "现金周转周期",
    }
    
    if lang == "zh":
        m_lines = ["| 核心指标 | 当前数值 | 行业基准 | 状态 |", "|----------|----------|----------|------|"]
        for m in result.metrics:
            unit = "天" if m.unit == "days" else m.unit
            m_lines.append(f"| {zh_names.get(m.name, m.name)} | {m.value}{unit} | {m.benchmark}{unit} | {status_icons[m.status]} |")

        c = result.cost_breakdown
        c_lines = [
            f"商品零售标价 (Price)     ${c['selling_price']:.2f}   100.0%",
            "─────────────────────────────",
            f"商品采购成本 (FOB)        -${c['product_cost']:.2f}    {c['product_cost_ratio']}%",
            f"头程干线运费 (Freight)    -${c['shipping_cost']:.2f}     {c['shipping_ratio']}%",
            f"FBT/仓配履约 (Shipping)   -${c['fulfillment_fee']:.2f}    {c['fulfillment_ratio']}%",
            f"仓储租金 (Storage)        -${c['storage_fee']:.2f}     {c['storage_ratio']}%",
            f"TikTok平台佣金 (6%)       -${c['platform_fee']:.2f}     {c['platform_ratio']}%",
            f"达人分销带货佣金 (Affiliate)-${c['affiliate_cost']:.2f}    {c['affiliate_ratio']}%",
            f"短视频投流广告 (Ads)      -${c['ad_cost']:.2f}     {c['ad_ratio']}%",
            f"其他运营与损耗 (Other)    -${c['other_cost']:.2f}     4.0%",
            "─────────────────────────────",
            f"实际净利润 (Net Profit)   ${c['net_profit']:.2f}     {c['net_margin']}%"
        ]

        b_lines = []
        priority_icons = {1: "🥇", 2: "🥈", 3: "🥉"}
        for i, b in enumerate(result.bottlenecks, 1):
            sev_zh = {"High": "高风险", "Medium": "中风险", "Low": "低风险"}.get(b.severity, b.severity)
            b_lines.append(f"\n{priority_icons.get(i, '•')} **【{sev_zh}】{b.title}**")
            b_lines.append(f"   问题诊断: {b.problem}")
            b_lines.append(f"   业务影响: {b.impact}")
            b_lines.append(f"   行动建议: {b.suggestion}")

        return f"""
🔍 **TikTok Shop 供应链敏捷度与履约诊断报告**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **核心指标健康度**

{chr(10).join(m_lines)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 **单件综合成本拆解**

```
{chr(10).join(c_lines)}
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 **关键供应链瓶颈诊断 (Top 3)**

{chr(10).join(b_lines) if b_lines else '✅ 未发现明显供应链瓶颈'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 **诊断总结**: {result.summary}
"""

    m_lines = ["| Metric | Value | Benchmark | Status |", "|--------|-------|-----------|--------|"]
    for m in result.metrics:
        m_lines.append(f"| {m.name} | {m.value}{m.unit} | {m.benchmark}{m.unit} | {status_icons[m.status]} |")

    c = result.cost_breakdown
    c_lines = [
        f"Retail Price (GMV)       ${c['selling_price']:.2f}   100.0%",
        "─────────────────────────────",
        f"Product Cost (FOB)       -${c['product_cost']:.2f}    {c['product_cost_ratio']}%",
        f"Inbound Freight          -${c['shipping_cost']:.2f}     {c['shipping_ratio']}%",
        f"FBT / 3PL Fulfillment    -${c['fulfillment_fee']:.2f}    {c['fulfillment_ratio']}%",
        f"Storage Fee              -${c['storage_fee']:.2f}     {c['storage_ratio']}%",
        f"TikTok Platform Fee (6%) -${c['platform_fee']:.2f}     {c['platform_ratio']}%",
        f"Creator Affiliate Fee    -${c['affiliate_cost']:.2f}    {c['affiliate_ratio']}%",
        f"TikTok Ads Spend         -${c['ad_cost']:.2f}     {c['ad_ratio']}%",
        f"Other Fees & Damages     -${c['other_cost']:.2f}     4.0%",
        "─────────────────────────────",
        f"Net Profit               ${c['net_profit']:.2f}     {c['net_margin']}%"
    ]

    b_lines = []
    priority_icons = {1: "🥇", 2: "🥈", 3: "🥉"}
    for i, b in enumerate(result.bottlenecks, 1):
        b_lines.append(f"\n{priority_icons.get(i, '•')} **[{b.severity}] {b.title}**")
        b_lines.append(f"   Issue: {b.problem}")
        b_lines.append(f"   Impact: {b.impact}")
        b_lines.append(f"   Action: {b.suggestion}")

    return f"""
🔍 **TikTok Shop Supply Chain Velocity & Fulfillment Diagnosis Report**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **Key Metrics Health**

{chr(10).join(m_lines)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 **Cost Breakdown (Per Unit)**

```
{chr(10).join(c_lines)}
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 **Top 3 Bottleneck Diagnosis**

{chr(10).join(b_lines) if b_lines else '✅ No obvious bottleneck found'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 **Summary**: {result.summary}
"""


def main():
    args = sys.argv[1:]
    lang = "zh" if "--zh" in args else "en"
    args = [a for a in args if a != "--zh"]

    if "--help" in args or "-h" in args:
        print("""Usage: python3 calculator.py [OPTIONS] [JSON_STRING]
Options:
  --demo            Run standard TikTok Shop supply chain demo
  --zh              Output report in Chinese
  --json <string>   Pass JSON object of TikTok supply chain inputs
  --help, -h        Show this help message
""")
        return

    test_data = TikTokSupplyChainInput()
    if len(args) > 0 and args[0] != "--demo":
        try:
            data = json.loads(args[0])
            test_data = TikTokSupplyChainInput(**data)
        except Exception as e:
            print(f"Error parsing input: {e}")
            sys.exit(1)

    result = analyze(test_data)
    print(format_report(result, lang=lang))


if __name__ == "__main__":
    main()
