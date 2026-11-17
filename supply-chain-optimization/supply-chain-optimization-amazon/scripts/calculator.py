#!/usr/bin/env python3
"""
Supply Chain Analyzer - Core Calculator
Supply Chain Analyzer - Core Calculator

Purpose: Calculate key metrics and diagnose bottlenecks
Version: 1.0.0
"""

import json
from dataclasses import dataclass
from typing import Optional, List, Dict
from enum import Enum


class HealthStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    DANGER = "danger"


# ============================================================
# Benchmark Configuration (customizable)
# ============================================================

BENCHMARKS = {
    "amazon": {
        "gross_margin": {
            "healthy": 0.40,    # >40% Healthy
            "warning": 0.30,    # 30-40% Warning
            "danger": 0.20      # <20% Danger
        },
        "shipping_ratio": {
            "healthy": 0.05,    # <5% Healthy
            "warning": 0.10,    # 5-10% Warning
            "danger": 0.15      # >15% Danger
        },
        "inventory_days": {
            "healthy": 45,      # <45days Healthy
            "warning": 60,      # 45-60days Warning
            "danger": 90        # >90days Danger
        },
        "cash_cycle": {
            "healthy": 90,      # <90days Healthy
            "warning": 120,     # 90-120days Warning
            "danger": 150       # >150days Danger
        },
        "net_margin": {
            "healthy": 0.20,    # >20% Healthy
            "warning": 0.10,    # 10-20% Warning
            "danger": 0.05      # <5% Danger
        }
    },
    "walmart": {
        "gross_margin": {
            "healthy": 0.35,    # Walmart Commission more  low 
            "warning": 0.25,
            "danger": 0.15
        },
        "shipping_ratio": {
            "healthy": 0.06,    # WFS ShippingSlightly higher
            "warning": 0.10,
            "danger": 0.15
        },
        "inventory_days": {
            "healthy": 45,
            "warning": 60,
            "danger": 90
        },
        "cash_cycle": {
            "healthy": 100,     # Payment CycleSlightly longer
            "warning": 130,
            "danger": 160
        },
        "net_margin": {
            "healthy": 0.18,
            "warning": 0.10,
            "danger": 0.05
        }
    },
    "tiktok": {
        "gross_margin": {
            "healthy": 0.45,    # NeedCoverInfluencerCommission
            "warning": 0.35,
            "danger": 0.25
        },
        "shipping_ratio": {
            "healthy": 0.05,
            "warning": 0.08,
            "danger": 0.12
        },
        "inventory_days": {
            "healthy": 30,      # TikTok Best sellerweeksPeriod short 
            "warning": 45,
            "danger": 60
        },
        "cash_cycle": {
            "healthy": 60,      # Fast payment
            "warning": 90,
            "danger": 120
        },
        "net_margin": {
            "healthy": 0.15,    # InfluencerShare after 
            "warning": 0.08,
            "danger": 0.03
        }
    },
    "shopify": {
        "gross_margin": {
            "healthy": 0.60,    # DTC Requires high gross marginAdvertising
            "warning": 0.50,
            "danger": 0.40
        },
        "shipping_ratio": {
            "healthy": 0.08,    # 3PL Fee
            "warning": 0.12,
            "danger": 0.18
        },
        "inventory_days": {
            "healthy": 45,
            "warning": 60,
            "danger": 90
        },
        "cash_cycle": {
            "healthy": 45,      # Fast payment (2-3days)
            "warning": 70,
            "danger": 100
        },
        "net_margin": {
            "healthy": 0.20,
            "warning": 0.12,
            "danger": 0.05
        }
    }
}


# ============================================================
# Data Structures
# ============================================================

@dataclass
class SupplyChainInput:
    """Supply ChainInput Data"""
    # Procurementend
    product_cost: float          # ProductCost (FOB)
    supplier_payment_days: int   # SupplierPayment terms (days)
    production_days: int         # ProductionweeksPeriod (days)
    
    # Logisticsend
    shipping_cost_per_unit: float  # Single pieceInboundCost
    shipping_days: int             # TransportTimeeffect (days)
    
    # Saleend
    selling_price: float         # Selling Price
    fba_fee: float              # FBA Fulfillment
    storage_fee: float          # monthsaverageStoragefee ( each piece)
    ad_spend_ratio: float       # AdvertisingfeeProportion (0-1)
    
    # Inventoryend
    inventory_days: int         # CurrentInventorydays
    has_long_term_storage: bool #  is no has PeriodStoragefee
    
    # Optional:  from  API Get
    daily_sales: Optional[float] = None      # DayAverage sales
    current_inventory: Optional[int] = None  # CurrentInventoryquantity
    
    # Platform
    platform: str = "amazon"


@dataclass
class MetricResult:
    """singleItemMetricsResult"""
    name: str
    value: float
    unit: str
    status: HealthStatus
    benchmark: float
    description: str


@dataclass 
class BottleneckItem:
    """BottleneckItem"""
    priority: int           # excellent first Level 1-3
    severity: str          # High/ in / low 
    title: str
    problem: str
    impact: str
    suggestion: str


@dataclass
class AnalysisResult:
    """AnalyzeResult"""
    metrics: List[MetricResult]
    cost_breakdown: Dict[str, float]
    bottlenecks: List[BottleneckItem]
    summary: str


# ============================================================
# CoreCalculateFunction
# ============================================================

def evaluate_status(value: float, thresholds: dict, higher_is_better: bool = True) -> HealthStatus:
    """
    EvaluateMetricsHealthyStatus
    
    Args:
        value: MetricsValue
        thresholds: ThresholdDictionary {"healthy": x, "warning": y, "danger": z}
        higher_is_better: True=ValueexceedHighexceed good , False=Valueexceed low exceed good 
    """
    if higher_is_better:
        if value >= thresholds["healthy"]:
            return HealthStatus.HEALTHY
        elif value >= thresholds["warning"]:
            return HealthStatus.WARNING
        else:
            return HealthStatus.DANGER
    else:
        if value <= thresholds["healthy"]:
            return HealthStatus.HEALTHY
        elif value <= thresholds["warning"]:
            return HealthStatus.WARNING
        else:
            return HealthStatus.DANGER


def calculate_metrics(data: SupplyChainInput) -> List[MetricResult]:
    """Calculate all key metrics"""
    benchmarks = BENCHMARKS.get(data.platform, BENCHMARKS["amazon"])
    metrics = []
    
    # 1. Gross Margin
    gross_profit = data.selling_price - data.product_cost - data.shipping_cost_per_unit - data.fba_fee
    gross_margin = gross_profit / data.selling_price if data.selling_price > 0 else 0
    metrics.append(MetricResult(
        name="Gross Margin",
        value=round(gross_margin * 100, 1),
        unit="%",
        status=evaluate_status(gross_margin, benchmarks["gross_margin"], higher_is_better=True),
        benchmark=benchmarks["gross_margin"]["healthy"] * 100,
        description="(Selling Price - Product Cost - Inbound Freight - Fulfillment Fee) / Selling Price"
    ))
    
    # 2. Inbound Shipping Ratio
    shipping_ratio = data.shipping_cost_per_unit / data.selling_price if data.selling_price > 0 else 0
    metrics.append(MetricResult(
        name="Inbound Freight Ratio",
        value=round(shipping_ratio * 100, 1),
        unit="%",
        status=evaluate_status(shipping_ratio, benchmarks["shipping_ratio"], higher_is_better=False),
        benchmark=benchmarks["shipping_ratio"]["healthy"] * 100,
        description="Inbound Freight Cost / Selling Price"
    ))
    
    # 3. Net Margin
    ad_cost = data.selling_price * data.ad_spend_ratio
    other_cost = data.selling_price * 0.05  # Other fees estimate ~5%
    net_profit = gross_profit - data.storage_fee - ad_cost - other_cost
    net_margin = net_profit / data.selling_price if data.selling_price > 0 else 0
    metrics.append(MetricResult(
        name="Net Margin",
        value=round(net_margin * 100, 1),
        unit="%",
        status=evaluate_status(net_margin, benchmarks["net_margin"], higher_is_better=True),
        benchmark=benchmarks["net_margin"]["healthy"] * 100,
        description="Net Profit Margin after all costs and fees"
    ))
    
    # 4. Inventory Days
    metrics.append(MetricResult(
        name="Inventory Turnover Days",
        value=data.inventory_days,
        unit="days",
        status=evaluate_status(data.inventory_days, benchmarks["inventory_days"], higher_is_better=False),
        benchmark=benchmarks["inventory_days"]["healthy"],
        description="Days of inventory currently on hand"
    ))
    
    # 5. Cash Cycle
    cash_cycle = (
        data.production_days + 
        data.shipping_days + 
        data.inventory_days + 
        14  # Amazon payout cycle (~14 days)
        - data.supplier_payment_days
    )
    metrics.append(MetricResult(
        name="Cash-to-Cash Cycle",
        value=cash_cycle,
        unit="days",
        status=evaluate_status(cash_cycle, benchmarks["cash_cycle"], higher_is_better=False),
        benchmark=benchmarks["cash_cycle"]["healthy"],
        description="Days between paying suppliers and receiving customer payout"
    ))
    
    return metrics


def calculate_cost_breakdown(data: SupplyChainInput) -> Dict[str, float]:
    """Calculate cost structure breakdown"""
    ad_cost = data.selling_price * data.ad_spend_ratio
    other_cost = data.selling_price * 0.05
    
    net_profit = (
        data.selling_price 
        - data.product_cost 
        - data.shipping_cost_per_unit 
        - data.fba_fee 
        - data.storage_fee 
        - ad_cost 
        - other_cost
    )
    
    sp = data.selling_price if data.selling_price > 0 else 1.0
    return {
        "selling_price": data.selling_price,
        "product_cost": data.product_cost,
        "shipping_cost": data.shipping_cost_per_unit,
        "fba_fee": data.fba_fee,
        "storage_fee": data.storage_fee,
        "ad_cost": round(ad_cost, 2),
        "other_cost": round(other_cost, 2),
        "net_profit": round(net_profit, 2),
        "product_cost_ratio": round(data.product_cost / sp * 100, 1),
        "shipping_ratio": round(data.shipping_cost_per_unit / sp * 100, 1),
        "fba_ratio": round(data.fba_fee / sp * 100, 1),
        "storage_ratio": round(data.storage_fee / sp * 100, 1),
        "ad_ratio": round(ad_cost / sp * 100, 1),
        "net_margin": round(net_profit / sp * 100, 1)
    }


def diagnose_bottlenecks(data: SupplyChainInput, metrics: List[MetricResult]) -> List[BottleneckItem]:
    """Diagnose bottlenecks and prioritize top issues"""
    bottlenecks = []
    benchmarks = BENCHMARKS.get(data.platform, BENCHMARKS["amazon"])
    
    for metric in metrics:
        if metric.status == HealthStatus.DANGER:
            severity = "High"
            priority = 1
        elif metric.status == HealthStatus.WARNING:
            severity = "Medium"
            priority = 2
        else:
            continue
            
        if metric.name == "Inventory Turnover Days":
            bottlenecks.append(BottleneckItem(
                priority=priority,
                severity=severity,
                title="Slow Inventory Turnover",
                problem=f"Current {metric.value} days vs benchmark <{benchmarks['inventory_days']['healthy']} days",
                impact="Ties up working capital and risks aging / long-term storage fees",
                suggestion="1. Clear slow-moving SKUs  2. Optimize safety stock formula  3. Smaller batch, higher frequency restock"
            ))
        elif metric.name == "Cash-to-Cash Cycle":
            bottlenecks.append(BottleneckItem(
                priority=priority,
                severity=severity,
                title="Extended Cash Conversion Cycle",
                problem=f"Current {metric.value} days vs benchmark <{benchmarks['cash_cycle']['healthy']} days",
                impact="Inefficient capital utilization and higher financing risk",
                suggestion="1. Negotiate supplier credit terms  2. Shorten lead times  3. Utilize supply chain trade finance"
            ))
        elif metric.name == "Inbound Freight Ratio":
            bottlenecks.append(BottleneckItem(
                priority=priority,
                severity=severity,
                title="High Inbound Logistics Cost",
                problem=f"Current {metric.value}% vs benchmark <{benchmarks['shipping_ratio']['healthy']*100}%",
                impact="Directly erodes gross profit margin",
                suggestion="1. Switch air freight to ocean shipping  2. Consolidate LCL into FCL  3. Bid across multiple freight forwarders"
            ))
        elif metric.name == "Gross Margin":
            bottlenecks.append(BottleneckItem(
                priority=priority,
                severity=severity,
                title="Low Gross Margin",
                problem=f"Current {metric.value}% vs benchmark >{benchmarks['gross_margin']['healthy']*100}%",
                impact="Vulnerable to price competition and high advertising cost pressure",
                suggestion="1. Increase price or optimize listing conversion  2. Negotiate BOM/procurement cost  3. Optimize product bundling"
            ))
        elif metric.name == "Net Margin":
            bottlenecks.append(BottleneckItem(
                priority=priority,
                severity=severity,
                title="Compressed Net Margin",
                problem=f"Current {metric.value}% vs benchmark >{benchmarks['net_margin']['healthy']*100}%",
                impact="Weak profitability undermines sustainable business operations",
                suggestion="1. Optimize ad ACOS / reduce wasted spend  2. Control long-term storage fees  3. Increase AOV (Average Order Value)"
            ))
    
    if data.has_long_term_storage:
        bottlenecks.append(BottleneckItem(
            priority=2,
            severity="Medium",
            title="Aged Inventory / Long-Term Storage Surcharges",
            problem="Part of warehouse inventory exceeds 180-365 days",
            impact="Incurring punitive storage surcharges that burn operating margin",
            suggestion="1. Export FBA inventory age report  2. Create outlet/promotional discount clearance  3. Create removal or liquidation orders"
        ))
    
    bottlenecks.sort(key=lambda x: x.priority)
    return bottlenecks[:3]


def analyze(data: SupplyChainInput) -> AnalysisResult:
    """Execute complete supply chain analysis"""
    metrics = calculate_metrics(data)
    cost_breakdown = calculate_cost_breakdown(data)
    bottlenecks = diagnose_bottlenecks(data, metrics)
    
    danger_count = sum(1 for m in metrics if m.status == HealthStatus.DANGER)
    warning_count = sum(1 for m in metrics if m.status == HealthStatus.WARNING)
    
    if danger_count > 0:
        summary = f"Found {danger_count} critical issue(s) requiring immediate action"
    elif warning_count > 0:
        summary = f"Found {warning_count} potential optimization opportunity(s)"
    else:
        summary = "Supply chain operations are healthy; continue monitoring"
    
    return AnalysisResult(
        metrics=metrics,
        cost_breakdown=cost_breakdown,
        bottlenecks=bottlenecks,
        summary=summary
    )


def format_metrics_table(metrics: List[MetricResult], lang: str = "en") -> str:
    """Format metrics table"""
    status_icons = {
        HealthStatus.HEALTHY: "✅",
        HealthStatus.WARNING: "⚠️",
        HealthStatus.DANGER: "🔴"
    }
    
    zh_names = {
        "Gross Margin": "毛利率",
        "Inbound Freight Ratio": "头程运费占比",
        "Net Margin": "净利率",
        "Inventory Turnover Days": "库存周转天数",
        "Cash-to-Cash Cycle": "现金周转周期",
    }
    
    if lang == "zh":
        lines = ["| 核心指标 | 当前数值 | 行业基准 | 状态 |", "|----------|----------|----------|------|"]
        for m in metrics:
            icon = status_icons[m.status]
            name = zh_names.get(m.name, m.name)
            unit = "天" if m.unit == "days" else m.unit
            lines.append(f"| {name} | {m.value}{unit} | {m.benchmark}{unit} | {icon} |")
        return "\n".join(lines)
        
    lines = ["| Metric | Value | Benchmark | Status |", "|--------|-------|-----------|--------|"]
    for m in metrics:
        icon = status_icons[m.status]
        lines.append(f"| {m.name} | {m.value}{m.unit} | {m.benchmark}{m.unit} | {icon} |")
    return "\n".join(lines)


def format_cost_breakdown(breakdown: Dict[str, float], lang: str = "en") -> str:
    """Format cost breakdown"""
    if lang == "zh":
        lines = [
            f"商品售价 (Price)            ${breakdown['selling_price']:.2f}   100%",
            "─────────────────────────────",
            f"采购成本 (FOB)            -${breakdown['product_cost']:.2f}    {breakdown['product_cost_ratio']}%",
            f"头程运费 (Inbound)        -${breakdown['shipping_cost']:.2f}     {breakdown['shipping_ratio']}%",
            f"履约配送费 (Fulfillment)  -${breakdown['fba_fee']:.2f}    {breakdown['fba_ratio']}%",
            f"月度仓储费 (Storage)      -${breakdown['storage_fee']:.2f}     {breakdown['storage_ratio']}%",
            f"广告营销费 (Ads)          -${breakdown['ad_cost']:.2f}    {breakdown['ad_ratio']}%",
            f"其他杂费 (Other)          -${breakdown['other_cost']:.2f}     5.0%",
            "─────────────────────────────",
            f"净利润 (Net Profit)       ${breakdown['net_profit']:.2f}     {breakdown['net_margin']}%"
        ]
        return "\n".join(lines)
        
    lines = [
        f"Selling Price            ${breakdown['selling_price']:.2f}   100%",
        "─────────────────────────────",
        f"Product Cost        -${breakdown['product_cost']:.2f}    {breakdown['product_cost_ratio']}%",
        f"Inbound Freight     -${breakdown['shipping_cost']:.2f}     {breakdown['shipping_ratio']}%",
        f"Fulfillment Fee     -${breakdown['fba_fee']:.2f}    {breakdown['fba_ratio']}%",
        f"Storage Fee         -${breakdown['storage_fee']:.2f}     {breakdown['storage_ratio']}%",
        f"Advertising         -${breakdown['ad_cost']:.2f}    {breakdown['ad_ratio']}%",
        f"Other Fees          -${breakdown['other_cost']:.2f}     5.0%",
        "─────────────────────────────",
        f"Net Profit          ${breakdown['net_profit']:.2f}     {breakdown['net_margin']}%"
    ]
    return "\n".join(lines)


def format_bottlenecks(bottlenecks: List[BottleneckItem], lang: str = "en") -> str:
    """Format bottlenecks list"""
    if not bottlenecks:
        return "✅ 未发现明显供应链瓶颈" if lang == "zh" else "✅ No obvious bottleneck found"
    
    lines = []
    priority_icons = {1: "🥇", 2: "🥈", 3: "🥉"}
    
    for i, b in enumerate(bottlenecks, 1):
        icon = priority_icons.get(i, "•")
        if lang == "zh":
            severity_zh = {"High": "高风险", "Medium": "中风险", "Low": "低风险"}.get(b.severity, b.severity)
            lines.append(f"\n{icon} **【{severity_zh}】{b.title}**")
            lines.append(f"   问题诊断: {b.problem}")
            lines.append(f"   业务影响: {b.impact}")
            lines.append(f"   改善建议: {b.suggestion}")
        else:
            lines.append(f"\n{icon} **[{b.severity}] {b.title}**")
            lines.append(f"   Issue: {b.problem}")
            lines.append(f"   Impact: {b.impact}")
            lines.append(f"   Action: {b.suggestion}")
    
    return "\n".join(lines)


def format_full_report(result: AnalysisResult, lang: str = "en") -> str:
    """Generate complete report"""
    if lang == "zh":
        danger_count = sum(1 for m in result.metrics if m.status == HealthStatus.DANGER)
        warning_count = sum(1 for m in result.metrics if m.status == HealthStatus.WARNING)
        if danger_count > 0:
            summary_zh = f"发现 {danger_count} 个高风险瓶颈，建议立即推进改善"
        elif warning_count > 0:
            summary_zh = f"发现 {warning_count} 个潜在优化点，可制定优化排期"
        else:
            summary_zh = "供应链整体健康，请持续保持运营指标"
            
        return f"""
🔍 **供应链瓶颈与成本诊断报告**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **核心指标诊断**

{format_metrics_table(result.metrics, lang="zh")}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 **单件成本结构拆解**

```
{format_cost_breakdown(result.cost_breakdown, lang="zh")}
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 **关键瓶颈诊断与行动建议 (Top 3)**

{format_bottlenecks(result.bottlenecks, lang="zh")}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 **诊断总结**: {summary_zh}
"""

    return f"""
🔍 **Supply Chain Bottleneck Diagnosis Report**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **Key Metrics**

{format_metrics_table(result.metrics, lang="en")}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 **Cost Breakdown (Per Unit)**

```
{format_cost_breakdown(result.cost_breakdown, lang="en")}
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 **Top 3 Bottleneck Diagnosis**

{format_bottlenecks(result.bottlenecks, lang="en")}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 **Summary**: {result.summary}
"""


def main():
    """CLI Entry Point"""
    import sys
    
    test_data = SupplyChainInput(
        product_cost=8.00,
        supplier_payment_days=0,
        production_days=25,
        shipping_cost_per_unit=0.75,
        shipping_days=35,
        selling_price=25.00,
        fba_fee=5.00,
        storage_fee=0.50,
        ad_spend_ratio=0.10,
        inventory_days=60,
        has_long_term_storage=True,
        platform="amazon"
    )
    
    args = sys.argv[1:]
    lang = "zh" if "--zh" in args else "en"
    args = [a for a in args if a != "--zh"]
    
    if "--help" in args or "-h" in args:
        print("""Usage: python3 calculator.py [OPTIONS] [JSON_STRING]
Options:
  --demo            Run with standard demo supply chain data
  --zh              Output report in Chinese
  --json <string>   Pass JSON object of supply chain inputs
  --help, -h        Show this help message
""")
        return
        
    json_str = None
    if "--json" in args:
        idx = args.index("--json")
        if idx + 1 < len(args):
            json_str = args[idx + 1]
            args.pop(idx + 1)
        args.pop(idx)
    elif len(args) > 0 and args[0] != "--demo":
        json_str = args[0]
        
    if json_str:
        try:
            input_json = json.loads(json_str)
            test_data = SupplyChainInput(**input_json)
        except Exception as e:
            print(f"Error parsing input: {e}")
            sys.exit(1)
            
    result = analyze(test_data)
    print(format_full_report(result, lang=lang))
    
    # Output JSON (For program call)
    # print(json.dumps({
    #     "metrics": [{"name": m.name, "value": m.value, "status": m.status.value} for m in result.metrics],
    #     "bottlenecks": [{"title": b.title, "severity": b.severity} for b in result.bottlenecks],
    #     "summary": result.summary
    # }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
