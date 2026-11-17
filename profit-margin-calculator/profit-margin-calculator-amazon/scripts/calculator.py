#!/usr/bin/env python3
"""
Amazon Profit Calculator - Core Engine

Features:
- Cost breakdown calculation
- Profit margin calculation (gross/net)
- Break-even analysis
- Pricing recommendations
- Batch calculation support

Version: 1.0.0
"""

import json
import csv
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import sys


class ProfitStatus(Enum):
    HEALTHY = "healthy"      # >20% net margin
    WARNING = "warning"      # 5-20% net margin
    DANGER = "danger"        # <5% net margin
    LOSS = "loss"            # Negative margin


# ============================================================
# Amazon Referral Fee Rates (by category)
# ============================================================

REFERRAL_FEE_RATES = {
    # Category: Rate
    "default": 0.15,
    "electronics": 0.08,
    "computers": 0.08,
    "camera": 0.08,
    "video_games": 0.15,
    "books": 0.15,
    "clothing": 0.17,
    "shoes": 0.15,
    "jewelry": 0.20,
    "watches": 0.15,
    "furniture": 0.15,
    "home": 0.15,
    "kitchen": 0.15,
    "beauty": 0.15,
    "health": 0.15,
    "grocery": 0.15,
    "pet": 0.15,
    "toys": 0.15,
    "baby": 0.15,
    "sports": 0.15,
    "outdoors": 0.15,
    "automotive": 0.12,
    "industrial": 0.12,
    "office": 0.15,
}

# FBA Fulfillment Fee Reference (simplified, based on size tier)
FBA_FULFILLMENT_FEES = {
    "small_standard": 3.22,      # Small standard (<1lb)
    "large_standard_1lb": 4.75,  # Large standard (<1lb)
    "large_standard_2lb": 5.40,  # Large standard (1-2lb)
    "large_standard_3lb": 6.10,  # Large standard (2-3lb)
    "small_oversize": 9.73,      # Small oversize
    "medium_oversize": 19.05,    # Medium oversize
    "large_oversize": 89.98,     # Large oversize
}

# Profit margin thresholds
PROFIT_THRESHOLDS = {
    "healthy": 0.20,    # >20%
    "warning": 0.05,    # 5-20%
    "danger": 0.00,     # 0-5%
}


# ============================================================
# Data Structures
# ============================================================

@dataclass
class ProductInput:
    """Single product input data"""
    sku: str = "SKU001"
    name: str = "Product"
    
    # Selling price
    selling_price: float = 0.0
    
    # Cost items
    product_cost: float = 0.0           # Product cost (FOB)
    shipping_cost: float = 0.0          # Inbound shipping
    fba_fulfillment_fee: float = 0.0    # FBA fulfillment fee
    fba_storage_fee: float = 0.0        # FBA storage fee (monthly avg)
    
    # Optional costs
    ad_spend_ratio: float = 0.0         # Ad spend ratio (0-1)
    return_rate: float = 0.0            # Return rate (0-1)
    return_processing_fee: float = 0.0  # Return processing fee per unit
    other_fees: float = 0.0             # Other fees
    
    # Platform related
    category: str = "default"           # Category (for Referral Fee)
    referral_fee_rate: Optional[float] = None  # Custom commission rate
    
    # For batch calculation
    monthly_sales: int = 0              # Monthly sales (for fixed cost allocation)
    fixed_costs: float = 0.0            # Fixed costs (for break-even)


@dataclass
class CostBreakdown:
    """Cost breakdown"""
    selling_price: float
    product_cost: float
    shipping_cost: float
    fba_fulfillment_fee: float
    fba_storage_fee: float
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
            self.shipping_cost +
            self.fba_fulfillment_fee +
            self.fba_storage_fee +
            self.referral_fee +
            self.ad_cost +
            self.return_cost +
            self.other_fees
        )
        self.gross_profit = self.selling_price - self.product_cost - self.shipping_cost - self.fba_fulfillment_fee - self.referral_fee
        self.net_profit = self.selling_price - self.total_cost
        self.gross_margin = self.gross_profit / self.selling_price if self.selling_price > 0 else 0
        self.net_margin = self.net_profit / self.selling_price if self.selling_price > 0 else 0


@dataclass
class BreakEvenAnalysis:
    """Break-even analysis"""
    min_price: float              # Minimum price (break-even)
    break_even_units: int         # Break-even units
    safety_margin: float          # Safety margin
    current_margin_above_min: float  # Current price above minimum


@dataclass
class PricingSuggestion:
    """Pricing recommendation"""
    target_margin: float          # Target profit margin
    suggested_price: float        # Suggested price
    profit_per_unit: float        # Profit per unit


@dataclass
class AnalysisResult:
    """Complete analysis result"""
    product: ProductInput
    cost_breakdown: CostBreakdown
    break_even: BreakEvenAnalysis
    pricing_suggestions: List[PricingSuggestion]
    status: ProfitStatus
    summary: str


# ============================================================
# Core Calculation Functions
# ============================================================

def get_referral_fee_rate(category: str, custom_rate: Optional[float] = None) -> float:
    """Get Referral Fee rate"""
    if custom_rate is not None:
        return custom_rate
    return REFERRAL_FEE_RATES.get(category.lower(), REFERRAL_FEE_RATES["default"])


def calculate_costs(product: ProductInput) -> CostBreakdown:
    """Calculate cost breakdown"""
    # Referral Fee
    referral_rate = get_referral_fee_rate(product.category, product.referral_fee_rate)
    referral_fee = product.selling_price * referral_rate
    
    # Ad cost
    ad_cost = product.selling_price * product.ad_spend_ratio
    
    # Return cost = return rate × (processing fee + product cost loss ratio)
    return_cost = product.return_rate * (product.return_processing_fee + product.product_cost * 0.5)
    
    return CostBreakdown(
        selling_price=product.selling_price,
        product_cost=product.product_cost,
        shipping_cost=product.shipping_cost,
        fba_fulfillment_fee=product.fba_fulfillment_fee,
        fba_storage_fee=product.fba_storage_fee,
        referral_fee=round(referral_fee, 2),
        ad_cost=round(ad_cost, 2),
        return_cost=round(return_cost, 2),
        other_fees=product.other_fees
    )


def calculate_break_even(product: ProductInput, costs: CostBreakdown) -> BreakEvenAnalysis:
    """Calculate break-even point"""
    # Fixed-type unit costs independent of selling price
    fixed_unit_cost = (
        product.product_cost +
        product.shipping_cost +
        product.fba_fulfillment_fee +
        product.fba_storage_fee +
        product.other_fees +
        costs.return_cost
    )
    
    # Referral fee rate
    referral_rate = get_referral_fee_rate(product.category, product.referral_fee_rate)
    
    # Minimum price (cover variable cost + referral commission + ad spend)
    # min_price * (1 - referral_rate - ad_spend_ratio) = fixed_unit_cost
    denominator = 1 - referral_rate - product.ad_spend_ratio
    if denominator > 0:
        min_price = fixed_unit_cost / denominator
    else:
        min_price = fixed_unit_cost * 2  # Abnormal case
    
    # Break-even units (if fixed costs exist)
    if product.fixed_costs > 0 and costs.net_profit > 0:
        break_even_units = int(product.fixed_costs / costs.net_profit) + 1
    else:
        break_even_units = 0
    
    # Safety margin
    safety_margin = (product.selling_price - min_price) / product.selling_price if product.selling_price > 0 else 0
    margin_above_min = (product.selling_price - min_price) / min_price if min_price > 0 else 0
    
    return BreakEvenAnalysis(
        min_price=round(min_price, 2),
        break_even_units=break_even_units,
        safety_margin=round(safety_margin, 4),
        current_margin_above_min=round(margin_above_min, 4)
    )


def calculate_pricing_suggestions(product: ProductInput, target_margins: List[float] = None) -> List[PricingSuggestion]:
    """Calculate pricing recommendations"""
    if target_margins is None:
        target_margins = [0.15, 0.20, 0.25, 0.30]
    
    suggestions = []
    
    # Base cost (excluding Referral Fee and ad cost as they're % of price)
    base_cost = (
        product.product_cost +
        product.shipping_cost +
        product.fba_fulfillment_fee +
        product.fba_storage_fee +
        product.other_fees +
        product.return_rate * (product.return_processing_fee + product.product_cost * 0.5)
    )
    
    referral_rate = get_referral_fee_rate(product.category, product.referral_fee_rate)
    
    for target_margin in target_margins:
        # Target: net_profit / selling_price = target_margin
        # net_profit = selling_price - base_cost - selling_price * referral_rate - selling_price * ad_ratio
        # selling_price * target_margin = selling_price - base_cost - selling_price * (referral_rate + ad_ratio)
        # selling_price * (target_margin + referral_rate + ad_ratio - 1) = -base_cost
        # selling_price = base_cost / (1 - target_margin - referral_rate - ad_ratio)
        
        denominator = 1 - target_margin - referral_rate - product.ad_spend_ratio
        if denominator > 0:
            suggested_price = base_cost / denominator
            profit_per_unit = suggested_price * target_margin
            
            suggestions.append(PricingSuggestion(
                target_margin=target_margin,
                suggested_price=round(suggested_price, 2),
                profit_per_unit=round(profit_per_unit, 2)
            ))
    
    return suggestions


def evaluate_profit_status(net_margin: float) -> ProfitStatus:
    """Evaluate profit status"""
    if net_margin < 0:
        return ProfitStatus.LOSS
    elif net_margin < PROFIT_THRESHOLDS["warning"]:
        return ProfitStatus.DANGER
    elif net_margin < PROFIT_THRESHOLDS["healthy"]:
        return ProfitStatus.WARNING
    else:
        return ProfitStatus.HEALTHY


def analyze_product(product: ProductInput, target_margins: List[float] = None) -> AnalysisResult:
    """Analyze single product"""
    costs = calculate_costs(product)
    break_even = calculate_break_even(product, costs)
    pricing = calculate_pricing_suggestions(product, target_margins)
    status = evaluate_profit_status(costs.net_margin)
    
    # Generate summary without duplicated icon
    status_text = {
        ProfitStatus.HEALTHY: "Healthy",
        ProfitStatus.WARNING: "Warning",
        ProfitStatus.DANGER: "Danger",
        ProfitStatus.LOSS: "Loss",
    }
    summary = f"{status_text[status]} | Net Margin {costs.net_margin*100:.1f}% | Profit/Unit ${costs.net_profit:.2f}"
    
    return AnalysisResult(
        product=product,
        cost_breakdown=costs,
        break_even=break_even,
        pricing_suggestions=pricing,
        status=status,
        summary=summary
    )


def analyze_batch(products: List[ProductInput], target_margins: List[float] = None) -> List[AnalysisResult]:
    """Batch analysis"""
    return [analyze_product(p, target_margins) for p in products]


# ============================================================
# Output Formatting
# ============================================================

def format_cost_breakdown(costs: CostBreakdown) -> str:
    """Format cost breakdown"""
    def pct(val):
        return f"{val/costs.selling_price*100:.1f}%" if costs.selling_price > 0 else "0%"
    
    lines = [
        f"Selling Price         ${costs.selling_price:.2f}   100%",
        "─" * 40,
        f"Product Cost          -${costs.product_cost:.2f}    {pct(costs.product_cost)}",
        f"Inbound Shipping      -${costs.shipping_cost:.2f}    {pct(costs.shipping_cost)}",
        f"FBA Fulfillment       -${costs.fba_fulfillment_fee:.2f}    {pct(costs.fba_fulfillment_fee)}",
        f"FBA Storage           -${costs.fba_storage_fee:.2f}    {pct(costs.fba_storage_fee)}",
        f"Referral Fee          -${costs.referral_fee:.2f}    {pct(costs.referral_fee)}",
        f"Advertising           -${costs.ad_cost:.2f}    {pct(costs.ad_cost)}",
        f"Returns               -${costs.return_cost:.2f}    {pct(costs.return_cost)}",
        f"Other Fees            -${costs.other_fees:.2f}    {pct(costs.other_fees)}",
        "─" * 40,
        f"Total Cost            ${costs.total_cost:.2f}    {pct(costs.total_cost)}",
        f"Net Profit            ${costs.net_profit:.2f}    {costs.net_margin*100:.1f}%",
    ]
    return "\n".join(lines)


def format_break_even(be: BreakEvenAnalysis, current_price: float) -> str:
    """Format break-even analysis"""
    lines = [
        f"Break-even Price: ${be.min_price:.2f}",
        f"├── Below this price = Loss",
        f"",
        f"Current Price: ${current_price:.2f}",
        f"├── {be.current_margin_above_min*100:.1f}% above break-even",
        f"",
        f"Safety Margin: {be.safety_margin*100:.1f}%",
        f"├── Room for price reduction",
    ]
    if be.break_even_units > 0:
        lines.extend([
            f"",
            f"Break-even Units: {be.break_even_units}",
            f"├── Units needed to cover fixed costs",
        ])
    return "\n".join(lines)


def format_pricing_suggestions(suggestions: List[PricingSuggestion], current_price: float, current_margin: float) -> str:
    """Format pricing recommendations"""
    lines = [
        "| Target Margin | Recommended Price | Profit/Unit |",
        "|---------------|-------------------|-------------|",
    ]
    for s in suggestions:
        lines.append(f"| {s.target_margin*100:.0f}% | ${s.suggested_price:.2f} | ${s.profit_per_unit:.2f} |")
    
    lines.append(f"\nCurrent Price ${current_price:.2f} → Net Margin {current_margin*100:.1f}%")
    return "\n".join(lines)


def format_cost_breakdown_zh(costs: CostBreakdown) -> str:
    """Format cost breakdown in Chinese"""
    def pct(val):
        return f"{val/costs.selling_price*100:.1f}%" if costs.selling_price > 0 else "0%"
    
    lines = [
        f"商品售价 (Price)       ${costs.selling_price:.2f}   100%",
        "─" * 40,
        f"采购成本 (FOB)        -${costs.product_cost:.2f}    {pct(costs.product_cost)}",
        f"头程运费 (Shipping)   -${costs.shipping_cost:.2f}    {pct(costs.shipping_cost)}",
        f"FBA配送费 (Fulfillment) -${costs.fba_fulfillment_fee:.2f}    {pct(costs.fba_fulfillment_fee)}",
        f"FBA仓储费 (Storage)   -${costs.fba_storage_fee:.2f}    {pct(costs.fba_storage_fee)}",
        f"平台佣金 (Referral)   -${costs.referral_fee:.2f}    {pct(costs.referral_fee)}",
        f"广告支出 (Ad Spend)   -${costs.ad_cost:.2f}    {pct(costs.ad_cost)}",
        f"退货损失 (Returns)    -${costs.return_cost:.2f}    {pct(costs.return_cost)}",
        f"其他费用 (Other)      -${costs.other_fees:.2f}    {pct(costs.other_fees)}",
        "─" * 40,
        f"总成本 (Total Cost)   ${costs.total_cost:.2f}    {pct(costs.total_cost)}",
        f"净利润 (Net Profit)   ${costs.net_profit:.2f}    {costs.net_margin*100:.1f}%",
    ]
    return "\n".join(lines)


def format_break_even_zh(be: BreakEvenAnalysis, current_price: float) -> str:
    """Format break-even analysis in Chinese"""
    lines = [
        f"保本价格 (Break-even): ${be.min_price:.2f}",
        f"├── 低于此价格将发生亏损",
        f"",
        f"当前售价: ${current_price:.2f}",
        f"├── 高于保本价 {be.current_margin_above_min*100:.1f}%",
        f"",
        f"安全边际率: {be.safety_margin*100:.1f}%",
        f"├── 具有降价促销/应对价格战空间",
    ]
    if be.break_even_units > 0:
        lines.extend([
            f"",
            f"保本销量: {be.break_even_units} 件",
            f"├── 覆盖固定成本所需达到的最低销售件数",
        ])
    return "\n".join(lines)


def format_pricing_suggestions_zh(suggestions: List[PricingSuggestion], current_price: float, current_margin: float) -> str:
    """Format pricing recommendations in Chinese"""
    lines = [
        "| 目标净利率 | 建议售价 | 单件利润 |",
        "|------------|----------|----------|",
    ]
    for s in suggestions:
        lines.append(f"| {s.target_margin*100:.0f}% | ${s.suggested_price:.2f} | ${s.profit_per_unit:.2f} |")
    
    lines.append(f"\n当前售价 ${current_price:.2f} → 当前净利率 {current_margin*100:.1f}%")
    return "\n".join(lines)


def format_full_report(result: AnalysisResult, lang: str = "en") -> str:
    """Generate full report"""
    status_icons = {
        ProfitStatus.HEALTHY: "✅",
        ProfitStatus.WARNING: "⚠️",
        ProfitStatus.DANGER: "🔴",
        ProfitStatus.LOSS: "💀",
    }
    
    if lang == "zh":
        status_text_zh = {
            ProfitStatus.HEALTHY: "健康良好",
            ProfitStatus.WARNING: "轻度预警",
            ProfitStatus.DANGER: "危险微利",
            ProfitStatus.LOSS: "亏损警告",
        }
        summary_zh = f"{status_text_zh[result.status]} | 净利率 {result.cost_breakdown.net_margin*100:.1f}% | 单件净利 ${result.cost_breakdown.net_profit:.2f}"
        return f"""
💰 **亚马逊利润与保本分析报告**

**商品**: {result.product.name} ({result.product.sku})
**状态**: {status_icons[result.status]} {summary_zh}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **成本结构明细**

```
{format_cost_breakdown_zh(result.cost_breakdown)}
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 **保本点分析 (Break-Even)**

{format_break_even_zh(result.break_even, result.product.selling_price)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 **目标净利率定价建议**

{format_pricing_suggestions_zh(result.pricing_suggestions, result.product.selling_price, result.cost_breakdown.net_margin)}
"""
    
    report = f"""
💰 **Amazon Profit Analysis Report**

**Product**: {result.product.name} ({result.product.sku})
**Status**: {status_icons[result.status]} {result.summary}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **Cost Breakdown**

```
{format_cost_breakdown(result.cost_breakdown)}
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 **Break-Even Analysis**

{format_break_even(result.break_even, result.product.selling_price)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 **Pricing Recommendations**

{format_pricing_suggestions(result.pricing_suggestions, result.product.selling_price, result.cost_breakdown.net_margin)}
"""
    return report


def format_batch_summary(results: List[AnalysisResult]) -> str:
    """Format batch analysis summary"""
    status_icons = {
        ProfitStatus.HEALTHY: "✅",
        ProfitStatus.WARNING: "⚠️",
        ProfitStatus.DANGER: "🔴",
        ProfitStatus.LOSS: "💀",
    }
    
    lines = [
        "📊 **Batch Analysis Summary**",
        "",
        "| SKU | Price | Total Cost | Net Profit | Margin | Status |",
        "|-----|-------|------------|------------|--------|--------|",
    ]
    
    total_profit = 0
    for r in results:
        c = r.cost_breakdown
        icon = status_icons[r.status]
        lines.append(f"| {r.product.sku} | ${c.selling_price:.2f} | ${c.total_cost:.2f} | ${c.net_profit:.2f} | {c.net_margin*100:.1f}% | {icon} |")
        total_profit += c.net_profit
    
    lines.append("")
    lines.append(f"**Total**: {len(results)} SKUs | Avg Profit/Unit ${total_profit/len(results):.2f}")
    
    # Statistics
    healthy = sum(1 for r in results if r.status == ProfitStatus.HEALTHY)
    warning = sum(1 for r in results if r.status == ProfitStatus.WARNING)
    danger = sum(1 for r in results if r.status == ProfitStatus.DANGER)
    loss = sum(1 for r in results if r.status == ProfitStatus.LOSS)
    
    lines.append(f"**Status Distribution**: ✅ {healthy} | ⚠️ {warning} | 🔴 {danger} | 💀 {loss}")
    
    return "\n".join(lines)


# ============================================================
# CSV Batch Processing
# ============================================================

def parse_csv(csv_content: str) -> List[ProductInput]:
    """Parse CSV content"""
    products = []
    reader = csv.DictReader(csv_content.strip().split('\n'))
    
    for row in reader:
        product = ProductInput(
            sku=row.get('sku', 'SKU'),
            name=row.get('name', 'Product'),
            selling_price=float(row.get('selling_price', 0)),
            product_cost=float(row.get('product_cost', 0)),
            shipping_cost=float(row.get('shipping_cost', 0)),
            fba_fulfillment_fee=float(row.get('fba_fee', 0)),
            fba_storage_fee=float(row.get('storage_fee', 0)),
            ad_spend_ratio=float(row.get('ad_ratio', 0)),
            return_rate=float(row.get('return_rate', 0)),
            return_processing_fee=float(row.get('return_fee', 0)),
            other_fees=float(row.get('other_fees', 0)),
            category=row.get('category', 'default'),
        )
        products.append(product)
    
    return products


# ============================================================
# CLI Entry Point
# ============================================================

def main():
    """Command line entry"""
    # Default test data
    test_product = ProductInput(
        sku="TEST001",
        name="Kitchen Gadget",
        selling_price=29.99,
        product_cost=6.00,
        shipping_cost=1.50,
        fba_fulfillment_fee=5.50,
        fba_storage_fee=0.30,
        ad_spend_ratio=0.10,
        return_rate=0.03,
        return_processing_fee=2.00,
        other_fees=0.50,
        category="kitchen",
    )
    
    args = sys.argv[1:]
    lang = "zh" if "--zh" in args else "en"
    args = [a for a in args if a != "--zh"]
    
    if "--help" in args or "-h" in args:
        print("""Usage: python3 calculator.py [OPTIONS] [JSON_STRING]
Options:
  --demo            Run with standard demo product
  --zh              Output report in Chinese
  --json <string>   Pass JSON object or array of products
  --csv <file>      Read and batch analyze from CSV file
  --help, -h        Show this help message
""")
        return
        
    csv_file = None
    if "--csv" in args:
        idx = args.index("--csv")
        if idx + 1 < len(args):
            csv_file = args[idx + 1]
            args.pop(idx + 1)
        args.pop(idx)
        
    if csv_file:
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                products = parse_csv(f.read())
            results = analyze_batch(products)
            print(format_batch_summary(results))
            return
        except Exception as e:
            print(f"Error reading CSV file '{csv_file}': {e}")
            sys.exit(1)
            
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
            input_data = json.loads(json_str)
            if isinstance(input_data, list):
                products = [ProductInput(**p) for p in input_data]
                results = analyze_batch(products)
                print(format_batch_summary(results))
                return
            else:
                test_product = ProductInput(**input_data)
        except Exception as e:
            print(f"Error parsing JSON input: {e}")
            sys.exit(1)
            
    # Single product analysis
    result = analyze_product(test_product)
    print(format_full_report(result, lang=lang))


if __name__ == "__main__":
    main()
