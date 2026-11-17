#!/usr/bin/env python3
"""
Walmart Marketplace Supply Chain Analyzer - Core Calculator
Tailored for Walmart Marketplace sellers using Walmart Fulfillment Services (WFS) or seller fulfillment.

Purpose: Calculate key Walmart supply chain metrics and diagnose WFS inventory bottlenecks
Version: 1.1.0 (Enhanced for Walmart Marketplace)
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
    "gross_margin": {"healthy": 0.35, "warning": 0.25, "danger": 0.15},
    "shipping_ratio": {"healthy": 0.06, "warning": 0.10, "danger": 0.15},
    "inventory_days": {"healthy": 45, "warning": 60, "danger": 90},
    "cash_cycle": {"healthy": 80, "warning": 110, "danger": 140},
    "net_margin": {"healthy": 0.18, "warning": 0.10, "danger": 0.05}
}


@dataclass
class WalmartSupplyChainInput:
    product_cost: float = 9.00
    supplier_payment_days: int = 20
    production_days: int = 20
    shipping_cost_per_unit: float = 2.20
    shipping_days: int = 30
    selling_price: float = 39.99
    wfs_fulfillment_fee: float = 6.45    # WFS pick, pack & domestic shipping
    wfs_storage_fee: float = 0.40        # Monthly WFS storage per unit
    walmart_commission_rate: float = 0.15 # 15% standard commission
    ad_spend_ratio: float = 0.10         # Walmart Connect ad spend
    inventory_days: int = 55
    has_wfs_storage_cap_risk: bool = True # WFS inventory level/storage limit
    platform: str = "walmart"


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


def calculate_metrics(data: WalmartSupplyChainInput) -> List[MetricResult]:
    metrics = []
    sp = data.selling_price if data.selling_price > 0 else 1.0

    # 1. Gross Margin
    gross_profit = data.selling_price - data.product_cost - data.shipping_cost_per_unit - data.wfs_fulfillment_fee
    gross_margin = gross_profit / sp
    metrics.append(MetricResult(
        name="Gross Margin",
        value=round(gross_margin * 100, 1),
        unit="%",
        status=evaluate_status(gross_margin, BENCHMARKS["gross_margin"], higher_is_better=True),
        benchmark=BENCHMARKS["gross_margin"]["healthy"] * 100,
        description="Gross margin after FOB cost, inbound freight and WFS fulfillment"
    ))

    # 2. Inbound Freight Ratio
    shipping_ratio = data.shipping_cost_per_unit / sp
    metrics.append(MetricResult(
        name="Inbound Freight Ratio",
        value=round(shipping_ratio * 100, 1),
        unit="%",
        status=evaluate_status(shipping_ratio, BENCHMARKS["shipping_ratio"], higher_is_better=False),
        benchmark=BENCHMARKS["shipping_ratio"]["healthy"] * 100,
        description="Inbound freight as % of retail price"
    ))

    # 3. Net Margin
    ad_cost = data.selling_price * data.ad_spend_ratio
    comm_cost = data.selling_price * data.walmart_commission_rate
    other_cost = data.selling_price * 0.04
    net_profit = gross_profit - data.wfs_storage_fee - ad_cost - comm_cost - other_cost
    net_margin = net_profit / sp
    metrics.append(MetricResult(
        name="Net Margin",
        value=round(net_margin * 100, 1),
        unit="%",
        status=evaluate_status(net_margin, BENCHMARKS["net_margin"], higher_is_better=True),
        benchmark=BENCHMARKS["net_margin"]["healthy"] * 100,
        description="Net margin after Walmart commission, WFS fees, ads and other costs"
    ))

    # 4. Inventory Days
    metrics.append(MetricResult(
        name="Inventory Turnover Days",
        value=data.inventory_days,
        unit="days",
        status=evaluate_status(data.inventory_days, BENCHMARKS["inventory_days"], higher_is_better=False),
        benchmark=BENCHMARKS["inventory_days"]["healthy"],
        description="Days of inventory held in WFS fulfillment centers"
    ))

    # 5. Cash Cycle (Walmart payout cycle ~14 days)
    cash_cycle = (
        data.production_days + 
        data.shipping_days + 
        data.inventory_days + 
        14  # Walmart bi-weekly payout
        - data.supplier_payment_days
    )
    metrics.append(MetricResult(
        name="Cash-to-Cash Cycle",
        value=cash_cycle,
        unit="days",
        status=evaluate_status(cash_cycle, BENCHMARKS["cash_cycle"], higher_is_better=False),
        benchmark=BENCHMARKS["cash_cycle"]["healthy"],
        description="Cash conversion cycle from supplier payment to Walmart bank disbursement"
    ))

    return metrics


def calculate_cost_breakdown(data: WalmartSupplyChainInput) -> Dict[str, float]:
    ad_cost = data.selling_price * data.ad_spend_ratio
    comm_cost = data.selling_price * data.walmart_commission_rate
    other_cost = data.selling_price * 0.04
    net_profit = (
        data.selling_price 
        - data.product_cost 
        - data.shipping_cost_per_unit 
        - data.wfs_fulfillment_fee 
        - data.wfs_storage_fee 
        - ad_cost 
        - comm_cost
        - other_cost
    )
    sp = data.selling_price if data.selling_price > 0 else 1.0

    return {
        "selling_price": data.selling_price,
        "product_cost": data.product_cost,
        "shipping_cost": data.shipping_cost_per_unit,
        "fulfillment_fee": data.wfs_fulfillment_fee,
        "storage_fee": data.wfs_storage_fee,
        "commission": round(comm_cost, 2),
        "ad_cost": round(ad_cost, 2),
        "other_cost": round(other_cost, 2),
        "net_profit": round(net_profit, 2),
        "product_cost_ratio": round(data.product_cost / sp * 100, 1),
        "shipping_ratio": round(data.shipping_cost_per_unit / sp * 100, 1),
        "fulfillment_ratio": round(data.wfs_fulfillment_fee / sp * 100, 1),
        "storage_ratio": round(data.wfs_storage_fee / sp * 100, 1),
        "commission_ratio": round(data.walmart_commission_rate * 100, 1),
        "ad_ratio": round(ad_cost / sp * 100, 1),
        "net_margin": round(net_profit / sp * 100, 1)
    }


def diagnose_bottlenecks(data: WalmartSupplyChainInput, metrics: List[MetricResult]) -> List[BottleneckItem]:
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
                title="WFS Inventory Turnover Lagging",
                problem=f"Current {m.value} days vs benchmark <{BENCHMARKS['inventory_days']['healthy']} days",
                impact="Risk of exceeding WFS storage volume limits and incurring aged inventory penalties",
                suggestion="1. Set automated restock triggers based on 30-day velocity  2. Lower replenish lot sizes  3. Run Rollback promotions"
            ))
        elif m.name == "Cash-to-Cash Cycle":
            bottlenecks.append(BottleneckItem(
                priority=priority,
                severity=severity,
                title="Extended Cash Cycle on Walmart Marketplace",
                problem=f"Current {m.value} days vs benchmark <{BENCHMARKS['cash_cycle']['healthy']} days",
                impact="Slows capital reinvestment into top-performing Walmart categories",
                suggestion="1. Optimize factory lead times  2. Request ocean carrier express service  3. Negotiate supplier milestone payments"
            ))

    if data.has_wfs_storage_cap_risk:
        bottlenecks.append(BottleneckItem(
            priority=2,
            severity="Medium",
            title="WFS Storage Cap & Inbound Routing Constraints",
            problem="Peak season inbound allocations may restrict additional inventory shipments",
            impact="Stockout risks during Walmart Deals events or Q4 holiday shopping spikes",
            suggestion="1. Maintain safety stock in domestic 3PL for emergency WFS replenishment  2. Strict adherence to SQEP packaging guidelines  3. Monitor WFS inventory health dashboard weekly"
        ))

    bottlenecks.sort(key=lambda x: x.priority)
    return bottlenecks[:3]


def analyze(data: WalmartSupplyChainInput) -> AnalysisResult:
    metrics = calculate_metrics(data)
    costs = calculate_cost_breakdown(data)
    bottlenecks = diagnose_bottlenecks(data, metrics)
    danger = sum(1 for m in metrics if m.status == HealthStatus.DANGER)
    warning = sum(1 for m in metrics if m.status == HealthStatus.WARNING)
    if danger > 0:
        summary = f"Found {danger} critical Walmart supply chain bottleneck(s)"
    elif warning > 0:
        summary = f"Found {warning} optimization opportunity(s)"
    else:
        summary = "Walmart WFS supply chain metrics are performing within target thresholds"
    return AnalysisResult(metrics=metrics, cost_breakdown=costs, bottlenecks=bottlenecks, summary=summary)


def format_report(result: AnalysisResult, lang: str = "en") -> str:
    status_icons = {HealthStatus.HEALTHY: "✅", HealthStatus.WARNING: "⚠️", HealthStatus.DANGER: "🔴"}
    zh_names = {
        "Gross Margin": "毛利率",
        "Inbound Freight Ratio": "头程运费占比",
        "Net Margin": "净利率",
        "Inventory Turnover Days": "WFS仓储周转天数",
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
            f"WFS 官方履约费 (Delivery) -${c['fulfillment_fee']:.2f}    {c['fulfillment_ratio']}%",
            f"WFS 月度仓储费 (Storage)  -${c['storage_fee']:.2f}     {c['storage_ratio']}%",
            f"Walmart平台佣金 (15%)     -${c['commission']:.2f}    {c['commission_ratio']}%",
            f"Walmart Connect广告支出   -${c['ad_cost']:.2f}    {c['ad_ratio']}%",
            f"其他运营与耗材 (Other)    -${c['other_cost']:.2f}     4.0%",
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
🔍 **Walmart Marketplace 供应链与 WFS 履约诊断报告**

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
        f"Retail Price             ${c['selling_price']:.2f}   100.0%",
        "─────────────────────────────",
        f"Product Cost (FOB)       -${c['product_cost']:.2f}    {c['product_cost_ratio']}%",
        f"Inbound Freight          -${c['shipping_cost']:.2f}     {c['shipping_ratio']}%",
        f"WFS Fulfillment Fee      -${c['fulfillment_fee']:.2f}    {c['fulfillment_ratio']}%",
        f"WFS Monthly Storage      -${c['storage_fee']:.2f}     {c['storage_ratio']}%",
        f"Walmart Commission (15%) -${c['commission']:.2f}    {c['commission_ratio']}%",
        f"Walmart Connect Ads      -${c['ad_cost']:.2f}    {c['ad_ratio']}%",
        f"Other Operating Fees     -${c['other_cost']:.2f}     4.0%",
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
🔍 **Walmart Marketplace Supply Chain & WFS Diagnosis Report**

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
  --demo            Run standard Walmart WFS supply chain demo
  --zh              Output report in Chinese
  --json <string>   Pass JSON object of Walmart supply chain inputs
  --help, -h        Show this help message
""")
        return

    test_data = WalmartSupplyChainInput()
    if len(args) > 0 and args[0] != "--demo":
        try:
            data = json.loads(args[0])
            test_data = WalmartSupplyChainInput(**data)
        except Exception as e:
            print(f"Error parsing input: {e}")
            sys.exit(1)

    result = analyze(test_data)
    print(format_report(result, lang=lang))


if __name__ == "__main__":
    main()
