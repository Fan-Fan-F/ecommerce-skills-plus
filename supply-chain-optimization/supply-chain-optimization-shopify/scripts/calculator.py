#!/usr/bin/env python3
"""
Shopify DTC Supply Chain Analyzer - Core Calculator
Tailored for Shopify Direct-to-Consumer (DTC) brands and 3PL warehousing.

Purpose: Calculate key DTC metrics and diagnose inventory/cash flow bottlenecks
Version: 1.1.0 (Enhanced for Shopify DTC)
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
    "gross_margin": {"healthy": 0.60, "warning": 0.50, "danger": 0.40},
    "shipping_ratio": {"healthy": 0.08, "warning": 0.12, "danger": 0.18},
    "inventory_days": {"healthy": 45, "warning": 60, "danger": 90},
    "cash_cycle": {"healthy": 45, "warning": 70, "danger": 100},
    "net_margin": {"healthy": 0.20, "warning": 0.12, "danger": 0.05}
}


@dataclass
class DTCSupplyChainInput:
    product_cost: float = 12.00
    supplier_payment_days: int = 30
    production_days: int = 20
    shipping_cost_per_unit: float = 2.00
    shipping_days: int = 25
    selling_price: float = 49.99
    fulfillment_fee: float = 5.50       # 3PL pick, pack & domestic postage
    storage_fee: float = 0.35           # Monthly 3PL pallet/bin storage
    ad_spend_ratio: float = 0.22        # DTC CAC / ad spend ratio
    inventory_days: int = 50
    has_aged_inventory: bool = False
    platform: str = "shopify"


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


def calculate_metrics(data: DTCSupplyChainInput) -> List[MetricResult]:
    metrics = []
    sp = data.selling_price if data.selling_price > 0 else 1.0

    # 1. Gross Margin
    gross_profit = data.selling_price - data.product_cost - data.shipping_cost_per_unit - data.fulfillment_fee
    gross_margin = gross_profit / sp
    metrics.append(MetricResult(
        name="Gross Margin",
        value=round(gross_margin * 100, 1),
        unit="%",
        status=evaluate_status(gross_margin, BENCHMARKS["gross_margin"], higher_is_better=True),
        benchmark=BENCHMARKS["gross_margin"]["healthy"] * 100,
        description="Gross margin after COGS and 3PL fulfillment"
    ))

    # 2. Inbound Shipping Ratio
    shipping_ratio = data.shipping_cost_per_unit / sp
    metrics.append(MetricResult(
        name="Inbound Freight Ratio",
        value=round(shipping_ratio * 100, 1),
        unit="%",
        status=evaluate_status(shipping_ratio, BENCHMARKS["shipping_ratio"], higher_is_better=False),
        benchmark=BENCHMARKS["shipping_ratio"]["healthy"] * 100,
        description="Freight cost as % of retail price"
    ))

    # 3. Net Margin
    ad_cost = data.selling_price * data.ad_spend_ratio
    other_cost = data.selling_price * 0.05
    net_profit = gross_profit - data.storage_fee - ad_cost - other_cost
    net_margin = net_profit / sp
    metrics.append(MetricResult(
        name="Net Margin",
        value=round(net_margin * 100, 1),
        unit="%",
        status=evaluate_status(net_margin, BENCHMARKS["net_margin"], higher_is_better=True),
        benchmark=BENCHMARKS["net_margin"]["healthy"] * 100,
        description="Bottom-line net margin after all DTC costs and CAC"
    ))

    # 4. Inventory Days
    metrics.append(MetricResult(
        name="Inventory Turnover Days",
        value=data.inventory_days,
        unit="days",
        status=evaluate_status(data.inventory_days, BENCHMARKS["inventory_days"], higher_is_better=False),
        benchmark=BENCHMARKS["inventory_days"]["healthy"],
        description="Days of inventory currently held in 3PL warehouse"
    ))

    # 5. Cash Cycle (Shopify Payments has fast 2-3 day payout)
    cash_cycle = (
        data.production_days + 
        data.shipping_days + 
        data.inventory_days + 
        3  # Fast DTC payment gateway payout
        - data.supplier_payment_days
    )
    metrics.append(MetricResult(
        name="Cash-to-Cash Cycle",
        value=cash_cycle,
        unit="days",
        status=evaluate_status(cash_cycle, BENCHMARKS["cash_cycle"], higher_is_better=False),
        benchmark=BENCHMARKS["cash_cycle"]["healthy"],
        description="Operating cash conversion cycle from supplier payment to cash collection"
    ))

    return metrics


def calculate_cost_breakdown(data: DTCSupplyChainInput) -> Dict[str, float]:
    ad_cost = data.selling_price * data.ad_spend_ratio
    other_cost = data.selling_price * 0.05
    net_profit = (
        data.selling_price 
        - data.product_cost 
        - data.shipping_cost_per_unit 
        - data.fulfillment_fee 
        - data.storage_fee 
        - ad_cost 
        - other_cost
    )
    sp = data.selling_price if data.selling_price > 0 else 1.0

    return {
        "selling_price": data.selling_price,
        "product_cost": data.product_cost,
        "shipping_cost": data.shipping_cost_per_unit,
        "fulfillment_fee": data.fulfillment_fee,
        "storage_fee": data.storage_fee,
        "ad_cost": round(ad_cost, 2),
        "other_cost": round(other_cost, 2),
        "net_profit": round(net_profit, 2),
        "product_cost_ratio": round(data.product_cost / sp * 100, 1),
        "shipping_ratio": round(data.shipping_cost_per_unit / sp * 100, 1),
        "fulfillment_ratio": round(data.fulfillment_fee / sp * 100, 1),
        "storage_ratio": round(data.storage_fee / sp * 100, 1),
        "ad_ratio": round(ad_cost / sp * 100, 1),
        "net_margin": round(net_profit / sp * 100, 1)
    }


def diagnose_bottlenecks(data: DTCSupplyChainInput, metrics: List[MetricResult]) -> List[BottleneckItem]:
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

        if m.name == "Cash-to-Cash Cycle":
            bottlenecks.append(BottleneckItem(
                priority=priority,
                severity=severity,
                title="Extended Working Capital Cycle",
                problem=f"Current {m.value} days vs benchmark <{BENCHMARKS['cash_cycle']['healthy']} days",
                impact="Constrains DTC marketing cash flow and replenishment velocity",
                suggestion="1. Negotiate Net-60 supplier terms  2. Shorten freight transit via ocean express  3. Sync ad scaling with inventory arrivals"
            ))
        elif m.name == "Inventory Turnover Days":
            bottlenecks.append(BottleneckItem(
                priority=priority,
                severity=severity,
                title="Elevated 3PL Inventory Holding",
                problem=f"Current {m.value} days vs benchmark <{BENCHMARKS['inventory_days']['healthy']} days",
                impact="Increases 3PL storage fees and risk of deadstock",
                suggestion="1. Bundle slow-moving variants  2. Implement just-in-time replenishment  3. Use pre-orders for high-demand drops"
            ))
        elif m.name == "Gross Margin":
            bottlenecks.append(BottleneckItem(
                priority=priority,
                severity=severity,
                title="Gross Margin Compressed for DTC",
                problem=f"Current {m.value}% vs benchmark >{BENCHMARKS['gross_margin']['healthy']*100}%",
                impact="Insufficient room to absorb Meta/Google CAC fluctuations",
                suggestion="1. Raise pricing via value-add bundles  2. Re-negotiate contract manufacturing volume pricing  3. Increase customer AOV"
            ))

    if data.has_aged_inventory:
        bottlenecks.append(BottleneckItem(
            priority=2,
            severity="Medium",
            title="Aged 3PL Stock Accumulation",
            problem="Older batches lingering in warehouse over 120 days",
            impact="Consuming recurring storage rent without generating revenue",
            suggestion="1. Run exclusive email subscriber flash sales  2. Offer BOGO (Buy One Get One) promos  3. Liquidate surplus via secondary channels"
        ))

    bottlenecks.sort(key=lambda x: x.priority)
    return bottlenecks[:3]


def analyze(data: DTCSupplyChainInput) -> AnalysisResult:
    metrics = calculate_metrics(data)
    costs = calculate_cost_breakdown(data)
    bottlenecks = diagnose_bottlenecks(data, metrics)
    danger = sum(1 for m in metrics if m.status == HealthStatus.DANGER)
    warning = sum(1 for m in metrics if m.status == HealthStatus.WARNING)
    if danger > 0:
        summary = f"Found {danger} critical DTC supply chain bottleneck(s) requiring immediate attention"
    elif warning > 0:
        summary = f"Found {warning} potential optimization opportunity(s)"
    else:
        summary = "Shopify DTC supply chain operations are balanced and healthy"
    return AnalysisResult(metrics=metrics, cost_breakdown=costs, bottlenecks=bottlenecks, summary=summary)


def format_report(result: AnalysisResult, lang: str = "en") -> str:
    status_icons = {HealthStatus.HEALTHY: "✅", HealthStatus.WARNING: "⚠️", HealthStatus.DANGER: "🔴"}
    zh_names = {
        "Gross Margin": "毛利率",
        "Inbound Freight Ratio": "头程运费占比",
        "Net Margin": "净利率",
        "Inventory Turnover Days": "3PL库存周转天数",
        "Cash-to-Cash Cycle": "现金转换周期",
    }
    
    if lang == "zh":
        m_lines = ["| 核心指标 | 当前数值 | 行业基准 | 状态 |", "|----------|----------|----------|------|"]
        for m in result.metrics:
            unit = "天" if m.unit == "days" else m.unit
            m_lines.append(f"| {zh_names.get(m.name, m.name)} | {m.value}{unit} | {m.benchmark}{unit} | {status_icons[m.status]} |")

        c = result.cost_breakdown
        c_lines = [
            f"商品零售价 (AOV)         ${c['selling_price']:.2f}   100.0%",
            "─────────────────────────────",
            f"商品采购成本 (COGS)       -${c['product_cost']:.2f}    {c['product_cost_ratio']}%",
            f"头程干线运费 (Freight)    -${c['shipping_cost']:.2f}     {c['shipping_ratio']}%",
            f"3PL 仓配履约 (Pick&Pack) -${c['fulfillment_fee']:.2f}    {c['fulfillment_ratio']}%",
            f"3PL 仓储租金 (Storage)   -${c['storage_fee']:.2f}     {c['storage_ratio']}%",
            f"DTC 广告获客 (CAC)        -${c['ad_cost']:.2f}    {c['ad_ratio']}%",
            f"其他杂费支出 (Other)      -${c['other_cost']:.2f}     5.0%",
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
🔍 **Shopify DTC 独立站供应链与现金流诊断报告**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **核心指标健康度**

{chr(10).join(m_lines)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 **DTC 单件成本拆解**

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
        f"Retail Price (AOV)       ${c['selling_price']:.2f}   100.0%",
        "─────────────────────────────",
        f"Product Cost (COGS)      -${c['product_cost']:.2f}    {c['product_cost_ratio']}%",
        f"Inbound Freight          -${c['shipping_cost']:.2f}     {c['shipping_ratio']}%",
        f"3PL Pick & Pack          -${c['fulfillment_fee']:.2f}    {c['fulfillment_ratio']}%",
        f"3PL Storage Rent         -${c['storage_fee']:.2f}     {c['storage_ratio']}%",
        f"DTC Ad Spend (CAC)       -${c['ad_cost']:.2f}    {c['ad_ratio']}%",
        f"Other Fees               -${c['other_cost']:.2f}     5.0%",
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
🔍 **Shopify DTC Supply Chain & Working Capital Diagnosis Report**

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
  --demo            Run standard Shopify DTC supply chain demo
  --zh              Output report in Chinese
  --json <string>   Pass JSON object of DTC supply chain inputs
  --help, -h        Show this help message
""")
        return

    test_data = DTCSupplyChainInput()
    if len(args) > 0 and args[0] != "--demo":
        try:
            data = json.loads(args[0])
            test_data = DTCSupplyChainInput(**data)
        except Exception as e:
            print(f"Error parsing input: {e}")
            sys.exit(1)

    result = analyze(test_data)
    print(format_report(result, lang=lang))


if __name__ == "__main__":
    main()
