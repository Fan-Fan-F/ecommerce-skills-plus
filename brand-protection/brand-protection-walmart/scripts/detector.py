#!/usr/bin/env python3
"""
Brand Protection Detector - Core Engine
Brand ProtectionDetector - Core Engine

Features:
- Hijacker Detection (Hijacker Detection)
- PriceAbnormalMonitoring (Price Alert)
- CounterfeitIdentify (Counterfeit Detection)
- ImageStolenDetection (Image Theft)
- RiskEvaluate (Risk Assessment)
- Rights protectionRecommendation (Action Recommendations)

Version: 1.0.0
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime
import sys
import re


class RiskLevel(Enum):
    """RiskGrade"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ViolationType(Enum):
    """InfringementCategoryType"""
    HIJACKER = "hijacker"           # Hijacking
    COUNTERFEIT = "counterfeit"     # Counterfeit
    PRICE_VIOLATION = "price"       # PriceViolation
    IMAGE_THEFT = "image_theft"     # ImageStolen
    TRADEMARK = "trademark"         # TrademarkInfringement
    LISTING_ABUSE = "listing_abuse" # Listing Abuse


# ============================================================
# Data Structures
# ============================================================

@dataclass
class BrandInfo:
    """BrandInformation"""
    brand_name: str
    trademark_number: Optional[str] = None
    brand_registry: bool = False
    authorized_sellers: List[str] = field(default_factory=list)
    protected_asins: List[str] = field(default_factory=list)
    min_price: Optional[float] = None  # MAP  most  low price
    logo_url: Optional[str] = None


@dataclass
class SellerInfo:
    """SellerInformation"""
    seller_id: str
    seller_name: str
    price: float
    is_fba: bool = False
    rating: Optional[float] = None
    review_count: Optional[int] = None
    is_authorized: bool = False
    storefront_url: Optional[str] = None


@dataclass
class ListingInfo:
    """Listing Information"""
    asin: str
    title: str
    brand_in_title: bool = False
    price: float = 0.0
    image_urls: List[str] = field(default_factory=list)
    seller_count: int = 1
    sellers: List[SellerInfo] = field(default_factory=list)
    buy_box_seller: Optional[str] = None
    category: Optional[str] = None


@dataclass
class Violation:
    """InfringementRecord"""
    violation_type: ViolationType
    risk_level: RiskLevel
    seller: Optional[SellerInfo] = None
    listing: Optional[ListingInfo] = None
    evidence: List[str] = field(default_factory=list)
    description: str = ""
    description_zh: str = ""
    recommended_action: str = ""
    recommended_action_zh: str = ""


@dataclass
class DetectionResult:
    """DetectionResult"""
    brand: BrandInfo
    scan_time: str
    total_asins_scanned: int
    violations: List[Violation]
    risk_score: int  # 0-100
    risk_level: RiskLevel
    summary: str
    summary_zh: str
    action_plan: List[Dict[str, str]]


# ============================================================
# DetectionLogic
# ============================================================

def detect_hijackers(brand: BrandInfo, listing: ListingInfo) -> List[Violation]:
    """DetectionHijacking"""
    violations = []
    
    for seller in listing.sellers:
        # skip AuthorizedSeller
        if seller.seller_id in brand.authorized_sellers:
            continue
        if seller.is_authorized:
            continue
        
        # FoundnotAuthorizedSeller
        risk = RiskLevel.HIGH if listing.buy_box_seller == seller.seller_id else RiskLevel.MEDIUM
        
        violations.append(Violation(
            violation_type=ViolationType.HIJACKER,
            risk_level=risk,
            seller=seller,
            listing=listing,
            evidence=[
                f"Unauthorized seller on ASIN: {listing.asin}",
                f"Seller: {seller.seller_name} ({seller.seller_id})",
                f"Price: ${seller.price}",
            ],
            description=f"Unauthorized seller '{seller.seller_name}' found on your listing",
            description_zh=f"发现未经授权的跟卖卖家 '{seller.seller_name}' 正在跟卖抢占 Listing",
            recommended_action="File Brand Registry complaint or send cease & desist",
            recommended_action_zh="通过品牌注册通道 (Brand Registry) 投诉举报或发送停终侵权函 (Cease & Desist)",
        ))
    
    return violations


def detect_price_violations(brand: BrandInfo, listing: ListingInfo) -> List[Violation]:
    """DetectionPriceViolation"""
    violations = []
    
    if brand.min_price is None:
        return violations
    
    for seller in listing.sellers:
        if seller.price < brand.min_price:
            discount = (brand.min_price - seller.price) / brand.min_price * 100
            
            risk = RiskLevel.CRITICAL if discount > 30 else RiskLevel.HIGH if discount > 15 else RiskLevel.MEDIUM
            
            violations.append(Violation(
                violation_type=ViolationType.PRICE_VIOLATION,
                risk_level=risk,
                seller=seller,
                listing=listing,
                evidence=[
                    f"Price ${seller.price} below MAP ${brand.min_price}",
                    f"Discount: {discount:.1f}% below minimum",
                ],
                description=f"Seller '{seller.seller_name}' selling {discount:.1f}% below MAP",
                description_zh=f"卖家 '{seller.seller_name}' 售价低于最低限价 (MAP) {discount:.1f}%",
                recommended_action="Send MAP violation notice, consider distribution review",
                recommended_action_zh="发送限价违规通知函，核查渠道授权与窜货违规",
            ))
    
    return violations


def detect_counterfeit_signals(listing: ListingInfo, reviews: List[Dict] = None) -> List[Violation]:
    """DetectionCounterfeit Signals"""
    violations = []
    
    # SuspiciousKeywords
    counterfeit_keywords = [
        "fake", "counterfeit", "not genuine", "knockoff", "replica",
        "poor quality", "not authentic", "cheap copy", "different from picture",
        "假货", "仿冒", "山寨", "劣质", "与图片不符", "高仿", "做工粗糙",
    ]
    
    if reviews:
        suspicious_reviews = []
        for review in reviews:
            content = review.get("content", "").lower()
            for keyword in counterfeit_keywords:
                if keyword.lower() in content:
                    suspicious_reviews.append(review)
                    break
        
        if len(suspicious_reviews) >= 3:
            violations.append(Violation(
                violation_type=ViolationType.COUNTERFEIT,
                risk_level=RiskLevel.CRITICAL,
                listing=listing,
                evidence=[
                    f"Found {len(suspicious_reviews)} reviews mentioning counterfeit/fake",
                    "Sample keywords: " + ", ".join(counterfeit_keywords[:5]),
                ],
                description=f"Multiple reviews indicate potential counterfeit products",
                description_zh=f"多条买家评价提及假冒伪劣/山寨仿品，存在严重侵权风险",
                recommended_action="Initiate Test Buy to collect physical evidence",
                recommended_action_zh="启动官方试购 (Test Buy) 流程，固定实物取证并向平台立案",
            ))
    
    return violations


def detect_trademark_abuse(brand: BrandInfo, listing: ListingInfo) -> List[Violation]:
    """DetectionTrademarkAbuse"""
    violations = []
    
    # CheckWhether title abuses brand name
    title_lower = listing.title.lower()
    brand_lower = brand.brand_name.lower()
    
    # SuspiciousMode：Brandname + "compatible", "for", "replacement"
    abuse_patterns = [
        f"for {brand_lower}",
        f"compatible with {brand_lower}",
        f"{brand_lower} compatible",
        f"fits {brand_lower}",
        f"replacement for {brand_lower}",
    ]
    
    for pattern in abuse_patterns:
        if pattern in title_lower:
            violations.append(Violation(
                violation_type=ViolationType.TRADEMARK,
                risk_level=RiskLevel.MEDIUM,
                listing=listing,
                evidence=[
                    f"Title contains: '{pattern}'",
                    f"Full title: {listing.title}",
                ],
                description=f"Potential trademark abuse in listing title",
                description_zh=f"商品标题涉嫌存在商标侵权或违规搭便车滥用",
                recommended_action="File trademark complaint if unauthorized use",
                recommended_action_zh="若未获合法授权，向平台提交商标侵权纠纷投诉",
            ))
            break
    
    return violations


def calculate_risk_score(violations: List[Violation]) -> tuple:
    """CalculateRiskRating"""
    if not violations:
        return 0, RiskLevel.LOW
    
    # Weight
    weights = {
        RiskLevel.LOW: 5,
        RiskLevel.MEDIUM: 15,
        RiskLevel.HIGH: 30,
        RiskLevel.CRITICAL: 50,
    }
    
    total_score = sum(weights[v.risk_level] for v in violations)
    score = min(100, total_score)
    
    if score >= 70:
        level = RiskLevel.CRITICAL
    elif score >= 40:
        level = RiskLevel.HIGH
    elif score >= 20:
        level = RiskLevel.MEDIUM
    else:
        level = RiskLevel.LOW
    
    return score, level


def generate_action_plan(violations: List[Violation], brand: BrandInfo) -> List[Dict[str, str]]:
    """GenerateRights action plan"""
    actions = []
    
    #  by CategoryTypeGroup
    hijackers = [v for v in violations if v.violation_type == ViolationType.HIJACKER]
    counterfeits = [v for v in violations if v.violation_type == ViolationType.COUNTERFEIT]
    price_violations = [v for v in violations if v.violation_type == ViolationType.PRICE_VIOLATION]
    
    # Hijacking Process
    if hijackers:
        if brand.brand_registry:
            actions.append({
                "priority": "1",
                "action": "Report via Brand Registry",
                "action_zh": "通过品牌备案通道 (Brand Registry) 举报跟卖",
                "detail": f"Report {len(hijackers)} unauthorized seller(s) via Amazon Brand Registry portal",
                "detail_zh": f"通过平台官方 Brand Registry 侵权举报门户举报 {len(hijackers)} 个未授权跟卖卖家",
                "timeline": "24-48 hours",
            })
        else:
            actions.append({
                "priority": "1",
                "action": "Send Cease & Desist",
                "action_zh": "发送律师侵权告知函 (Cease & Desist)",
                "detail": "Contact sellers directly with legal notice",
                "detail_zh": "直接联系违规卖家后台并发送正式停终侵权警告信",
                "timeline": "3-5 business days",
            })
    
    # Counterfeit Process
    if counterfeits:
        actions.append({
            "priority": "1",
            "action": "Initiate Test Buy",
            "action_zh": "启动官方试购 (Test Buy 取证)",
            "detail": "Purchase product from suspected seller to collect physical evidence",
            "detail_zh": "从可疑跟卖店铺下单购买实物，拍照并留存发票与包装实物证据",
            "timeline": "7-14 days",
        })
        actions.append({
            "priority": "2",
            "action": "File Counterfeit Report",
            "action_zh": "提交平台假冒仿品纠纷投诉",
            "detail": "Submit counterfeit complaint with evidence to Amazon",
            "detail_zh": "将试购实物对比照片与商标证书一并提交平台举报封禁",
            "timeline": "After test buy",
        })
    
    # Price Violation Process
    if price_violations:
        actions.append({
            "priority": "2",
            "action": "Send MAP Violation Notice",
            "action_zh": "发送最低控价 (MAP) 违规整改通知函",
            "detail": f"Notify {len(price_violations)} seller(s) of MAP policy violation",
            "detail_zh": f"向 {len(price_violations)} 家违规降价卖家发送通告，限期纠正价格",
            "timeline": "48-72 hours",
        })
    
    # General Recommendation
    if not brand.brand_registry and violations:
        actions.append({
            "priority": "3",
            "action": "Enroll in Brand Registry",
            "action_zh": "完成品牌官方备案 (Brand Registry)",
            "detail": "Get enhanced brand protection tools from Amazon",
            "detail_zh": "通过官方备案解锁防跟卖与极速下架等核心知识产权保护工具",
            "timeline": "2-4 weeks (requires trademark)",
        })
    
    return actions


# ============================================================
# Main Detection Function
# ============================================================

def detect(
    brand: BrandInfo,
    listings: List[ListingInfo],
    reviews: Dict[str, List[Dict]] = None
) -> DetectionResult:
    """Main Detection Function"""
    
    all_violations = []
    
    for listing in listings:
        # Hijacker Detection
        all_violations.extend(detect_hijackers(brand, listing))
        
        # Price Violation Detection
        all_violations.extend(detect_price_violations(brand, listing))
        
        # Trademark Abuse Detection
        all_violations.extend(detect_trademark_abuse(brand, listing))
        
        # Counterfeit Signals Detection
        if reviews and listing.asin in reviews:
            all_violations.extend(detect_counterfeit_signals(listing, reviews[listing.asin]))
    
    # Calculate Risk Rating
    risk_score, risk_level = calculate_risk_score(all_violations)
    
    # Generate Action Plan
    action_plan = generate_action_plan(all_violations, brand)
    
    # Generate Summary
    hijacker_count = len([v for v in all_violations if v.violation_type == ViolationType.HIJACKER])
    counterfeit_count = len([v for v in all_violations if v.violation_type == ViolationType.COUNTERFEIT])
    
    if risk_level == RiskLevel.CRITICAL:
        status = "🚨 CRITICAL"
        status_zh = "🚨 极高侵权风险"
    elif risk_level == RiskLevel.HIGH:
        status = "🔴 HIGH RISK"
        status_zh = "🔴 高风险侵权"
    elif risk_level == RiskLevel.MEDIUM:
        status = "⚠️ MEDIUM RISK"
        status_zh = "⚠️ 中度风险"
    else:
        status = "✅ LOW RISK"
        status_zh = "✅ 低风险 (品牌状态良好)"
    
    summary = f"{status} | {len(all_violations)} violation(s) found | {hijacker_count} hijacker(s), {counterfeit_count} counterfeit signal(s)"
    summary_zh = f"{status_zh} | 共发现 {len(all_violations)} 项侵权违规 | 疑似跟卖 {hijacker_count} 家，假货仿品隐患 {counterfeit_count} 起"
    
    return DetectionResult(
        brand=brand,
        scan_time=datetime.now().isoformat(),
        total_asins_scanned=len(listings),
        violations=all_violations,
        risk_score=risk_score,
        risk_level=risk_level,
        summary=summary,
        summary_zh=summary_zh,
        action_plan=action_plan,
    )


# ============================================================
# Output Format
# ============================================================

def format_report(result: DetectionResult, lang: str = "en") -> str:
    """Format Report"""
    b = result.brand
    
    if lang == "zh":
        lines = [
            "🛡️ **品牌维权与防跟卖检测报告**",
            "",
            f"**品牌名称**: {b.brand_name}",
            f"**官方品牌备案**: {'✅ 已备案 (Brand Registry)' if b.brand_registry else '❌ 未备案'}",
            f"**扫描时间**: {result.scan_time[:19]}",
            f"**扫描 ASIN 数量**: {result.total_asins_scanned}",
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            f"## 🎯 品牌风险指数: {result.risk_score}/100",
            "",
            result.summary_zh,
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "## ⚠️ 侵权与违规线索详情",
            "",
        ]
        
        if not result.violations:
            lines.append("✅ 未检测到侵权与跟卖违规行为")
        else:
            for i, v in enumerate(result.violations[:10], 1):
                risk_icon = {"critical": "🚨", "high": "🔴", "medium": "⚠️", "low": "✅"}[v.risk_level.value]
                lines.append(f"**{i}. [{v.violation_type.value.upper()}] {risk_icon}**")
                lines.append(f"   {v.description_zh}")
                if v.seller:
                    lines.append(f"   违规卖家: {v.seller.seller_name} | 售价: ${v.seller.price}")
                lines.append(f"   处置建议: {v.recommended_action_zh}")
                lines.append("")
        
        if result.action_plan:
            lines.extend([
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                "",
                "## 📋 维权行动优先级计划",
                "",
            ])
            for action in result.action_plan:
                lines.append(f"**[P{action['priority']}] {action['action_zh']}**")
                lines.append(f"   具体行动: {action['detail_zh']}")
                lines.append(f"   建议时效: {action['timeline']}")
                lines.append("")
    else:
        lines = [
            "🛡️ **Brand Protection Detection Report**",
            "",
            f"**Brand**: {b.brand_name}",
            f"**Brand Registry**: {'✅ Enrolled' if b.brand_registry else '❌ Not Enrolled'}",
            f"**Scan Time**: {result.scan_time[:19]}",
            f"**ASINs Scanned**: {result.total_asins_scanned}",
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            f"## 🎯 Risk Score: {result.risk_score}/100",
            "",
            result.summary,
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "## ⚠️ Violations Found",
            "",
        ]
        
        if not result.violations:
            lines.append("✅ No violations detected")
        else:
            for i, v in enumerate(result.violations[:10], 1):
                risk_icon = {"critical": "🚨", "high": "🔴", "medium": "⚠️", "low": "✅"}[v.risk_level.value]
                lines.append(f"**{i}. [{v.violation_type.value.upper()}] {risk_icon}**")
                lines.append(f"   {v.description}")
                if v.seller:
                    lines.append(f"   Seller: {v.seller.seller_name} | Price: ${v.seller.price}")
                lines.append(f"   Action: {v.recommended_action}")
                lines.append("")
        
        if result.action_plan:
            lines.extend([
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                "",
                "## 📋 Action Plan",
                "",
            ])
            for action in result.action_plan:
                lines.append(f"**[P{action['priority']}] {action['action']}**")
                lines.append(f"   {action['detail']}")
                lines.append(f"   Timeline: {action['timeline']}")
                lines.append("")
    
    return "\n".join(lines)


# ============================================================
# DemoData
# ============================================================

def get_demo_data():
    """GetDemoData"""
    brand = BrandInfo(
        brand_name="TechGadget",
        trademark_number="US12345678",
        brand_registry=True,
        authorized_sellers=["A1B2C3D4E5F6G7"],
        protected_asins=["B08XXXXXX1", "B08XXXXXX2"],
        min_price=29.99,
    )
    
    listings = [
        ListingInfo(
            asin="B08XXXXXX1",
            title="TechGadget Premium Wireless Charger",
            brand_in_title=True,
            price=29.99,
            seller_count=3,
            buy_box_seller="A1B2C3D4E5F6G7",
            sellers=[
                SellerInfo(
                    seller_id="A1B2C3D4E5F6G7",
                    seller_name="TechGadget Official",
                    price=29.99,
                    is_fba=True,
                    rating=4.8,
                    is_authorized=True,
                ),
                SellerInfo(
                    seller_id="X9Y8Z7W6V5U4T3",
                    seller_name="CheapDeals123",
                    price=18.99,
                    is_fba=False,
                    rating=3.2,
                    is_authorized=False,
                ),
                SellerInfo(
                    seller_id="M1N2O3P4Q5R6S7",
                    seller_name="BestPriceStore",
                    price=24.99,
                    is_fba=True,
                    rating=4.1,
                    is_authorized=False,
                ),
            ],
        ),
        ListingInfo(
            asin="B09YYYYYY1",
            title="Compatible with TechGadget Wireless Charger Case",
            brand_in_title=True,
            price=9.99,
            seller_count=1,
            sellers=[
                SellerInfo(
                    seller_id="K1L2M3N4O5P6Q7",
                    seller_name="AccessoryWorld",
                    price=9.99,
                    is_fba=True,
                    rating=4.0,
                    is_authorized=False,
                ),
            ],
        ),
    ]
    
    reviews = {
        "B08XXXXXX1": [
            {"content": "Great product, works perfectly!", "rating": 5},
            {"content": "Received a fake product, not genuine TechGadget", "rating": 1},
            {"content": "This is counterfeit, poor quality", "rating": 1},
            {"content": "Not authentic, different from picture", "rating": 2},
            {"content": "Amazing charger, fast shipping", "rating": 5},
        ],
    }
    
    return brand, listings, reviews


# ============================================================
# CLI
# ============================================================

def main():
    lang = "zh" if "--zh" in sys.argv else "en"
    
    # DemoMode
    brand, listings, reviews = get_demo_data()
    
    # ExecuteDetection
    result = detect(brand, listings, reviews)
    
    # OutputReport
    print(format_report(result, lang))


if __name__ == "__main__":
    main()
