#!/usr/bin/env python3
"""
Amazon Review Checker - Core Analyzer
AmazonReviewAuthenticityDetection - CoreAnalyzeEngine

Features:
- ProgressiveAnalyze ( has  many  few Data，Give conclusion)
-  many dimensionDegreeDetection (Time/Content/Rating/Account/VP)
- Friendly guidance (HintCanDeepenDirection)

Version: 1.0.0
"""

import json
import re
import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import Counter
from enum import Enum
import sys


class RiskLevel(Enum):
    LOW = "low"           # 0-30
    MEDIUM = "medium"     # 31-60
    HIGH = "high"         # 61-80
    CRITICAL = "critical" # 81-100


class AnalysisLevel(Enum):
    L1_BASIC = "L1"      # onlyContent
    L2_TIMED = "L2"      # + Time
    L3_SCORED = "L3"     # + Rating
    L4_FULL = "L4"       #  all Field


# ============================================================
# Data Structures
# ============================================================

@dataclass
class Review:
    """Single itemReview"""
    content: str
    rating: Optional[int] = None          # 1-5 star
    date: Optional[str] = None            # DayPeriod
    reviewer_name: Optional[str] = None   # Reviewperson
    verified_purchase: Optional[bool] = None  # VP
    helpful_votes: Optional[int] = None   #  has Help
    reviewer_reviews_count: Optional[int] = None  # ReviewTotalReview Count
    
    @property
    def has_rating(self) -> bool:
        return self.rating is not None
    
    @property
    def has_date(self) -> bool:
        return self.date is not None
    
    @property
    def has_vp(self) -> bool:
        return self.verified_purchase is not None


@dataclass
class DimensionResult:
    """Single dimensionDegreeDetectionResult"""
    name: str
    name_zh: str
    score: float          # 0-100, exceedHighexceedSuspicious
    status: str           # ✅ ⚠️ 🔴
    detail: str
    detail_zh: str
    weight: float = 0.0


@dataclass
class SuspiciousReview:
    """SuspiciousReview"""
    content: str
    risk_score: float
    reasons: List[str]
    reasons_zh: List[str]


@dataclass
class AnalysisResult:
    """AnalyzeResult"""
    asin: str
    total_reviews: int
    analysis_level: AnalysisLevel
    authenticity_score: int       # 0-100, exceedHighexceedReal
    risk_level: RiskLevel
    dimensions: List[DimensionResult]
    suspicious_reviews: List[SuspiciousReview]
    available_fields: List[str]
    missing_fields: List[str]
    deepening_hints: List[str]
    deepening_hints_zh: List[str]
    summary: str
    summary_zh: str


# ============================================================
# DetectionAlgorithm
# ============================================================

def tokenize_text(text: str) -> List[str]:
    """Tokenize text supporting both English words and Chinese CJK characters"""
    if re.search(r'[\u4e00-\u9fff]', text):
        clean = re.sub(r'[^\w\u4e00-\u9fff]+', '', text.lower())
        if len(clean) <= 1:
            return list(clean)
        # Bi-gram sliding window for CJK text
        return [clean[i:i+2] for i in range(len(clean)-1)]
    return text.lower().split()


def detect_content_similarity(reviews: List[Review]) -> DimensionResult:
    """Detection Content Similarity"""
    if len(reviews) < 2:
        return DimensionResult(
            name="Content Similarity",
            name_zh="内容相似度",
            score=0,
            status="✅",
            detail="Not enough reviews to compare",
            detail_zh="评价数量不足，无法进行相似度对比",
            weight=0.20
        )
    
    contents = [r.content.lower() for r in reviews]
    
    # Extract n-grams supporting both English and CJK text
    def get_ngrams(text, n=3):
        if re.search(r'[\u4e00-\u9fff]', text):
            clean = re.sub(r'[^\w\u4e00-\u9fff]+', '', text.lower())
            return [clean[i:i+n] for i in range(len(clean)-n+1)]
        else:
            words = re.findall(r'\w+', text.lower())
            return [' '.join(words[i:i+n]) for i in range(len(words)-n+1)]
    
    all_ngrams = []
    for content in contents:
        all_ngrams.extend(get_ngrams(content))
    
    ngram_counts = Counter(all_ngrams)
    repeated = sum(1 for count in ngram_counts.values() if count > 1)
    total = len(ngram_counts) if ngram_counts else 1
    
    similarity_ratio = repeated / total if total > 0 else 0
    score = min(100, similarity_ratio * 500)
    
    # Check similar pairs using language-aware tokens
    similar_pairs = 0
    for i, c1 in enumerate(contents):
        for c2 in contents[i+1:]:
            if len(c1) >= 10 and len(c2) >= 10:
                tokens1 = set(tokenize_text(c1))
                tokens2 = set(tokenize_text(c2))
                if tokens1 and tokens2:
                    jaccard = len(tokens1 & tokens2) / len(tokens1 | tokens2)
                    if jaccard > 0.45:
                        similar_pairs += 1
    
    if similar_pairs > 0:
        score = max(score, 50 + similar_pairs * 10)
    
    score = min(100, score)
    
    if score < 30:
        status = "✅"
    elif score < 60:
        status = "⚠️"
    else:
        status = "🔴"
    
    return DimensionResult(
        name="Content Similarity",
        name_zh="内容相似度 (水军模板)",
        score=round(score, 1),
        status=status,
        detail=f"Found {similar_pairs} similar review pairs",
        detail_zh=f"检测到 {similar_pairs} 组高度重复/相似评价",
        weight=0.20
    )


def detect_time_clustering(reviews: List[Review]) -> Optional[DimensionResult]:
    """Detection Time Clustering"""
    dated_reviews = [r for r in reviews if r.has_date]
    
    if len(dated_reviews) < 5:
        return None
    
    dates = []
    for r in dated_reviews:
        try:
            for fmt in ['%Y-%m-%d', '%B %d, %Y', '%d %B %Y', '%m/%d/%Y']:
                try:
                    dates.append(datetime.strptime(r.date, fmt))
                    break
                except:
                    continue
        except:
            pass
    
    if len(dates) < 5:
        return None
    
    dates.sort()
    intervals = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
    if not intervals:
        return None
    
    short_intervals = sum(1 for i in intervals if i <= 1)
    clustering_ratio = short_intervals / len(intervals)
    
    burst_count = 0
    window_size = 2
    for i in range(len(dates) - 1):
        count_in_window = sum(1 for d in dates if 0 <= (d - dates[i]).days <= window_size)
        burst_count = max(burst_count, count_in_window)
    
    score = 0
    if clustering_ratio > 0.5:
        score += 40
    if clustering_ratio > 0.7:
        score += 20
    if burst_count > len(dates) * 0.3:
        score += 30
    
    score = min(100, score)
    
    if score < 30:
        status = "✅"
    elif score < 60:
        status = "⚠️"
    else:
        status = "🔴"
    
    return DimensionResult(
        name="Time Clustering",
        name_zh="时间聚合度 (集中刷评)",
        score=round(score, 1),
        status=status,
        detail=f"Max {burst_count} reviews in 48h window, {clustering_ratio*100:.0f}% within 1 day",
        detail_zh=f"48小时内最高爆发 {burst_count} 条评价，{clustering_ratio*100:.0f}% 集中在1天内",
        weight=0.25
    )


def detect_rating_distribution(reviews: List[Review]) -> Optional[DimensionResult]:
    """DetectionRating Distribution"""
    rated_reviews = [r for r in reviews if r.has_rating]
    
    if len(rated_reviews) < 5:
        return None
    
    ratings = [r.rating for r in rated_reviews]
    rating_counts = Counter(ratings)
    total = len(ratings)
    
    # CalculateDistribution
    five_star_ratio = rating_counts.get(5, 0) / total
    one_star_ratio = rating_counts.get(1, 0) / total
    extreme_ratio = five_star_ratio + one_star_ratio
    
    # Natural distribution usually is：5star ~50-60%, 4star ~20%, 3star ~10%, 2star ~5%, 1star ~10%
    # Abnormal case： all 5star、Polarized
    
    score = 0
    anomaly_detail = []
    
    if five_star_ratio > 0.85:
        score += 50
        anomaly_detail.append(f"{five_star_ratio*100:.0f}% 5-star (abnormal)")
    elif five_star_ratio > 0.75:
        score += 30
        anomaly_detail.append(f"{five_star_ratio*100:.0f}% 5-star (suspicious)")
    
    # Polarized
    if extreme_ratio > 0.9 and one_star_ratio > 0.1:
        score += 30
        anomaly_detail.append("Polarized distribution")
    
    # MissingMiddleRating
    mid_ratings = sum(rating_counts.get(r, 0) for r in [2, 3, 4])
    if mid_ratings / total < 0.1 and total > 10:
        score += 20
        anomaly_detail.append("Missing mid-range ratings")
    
    score = min(100, score)
    
    if score < 30:
        status = "✅"
    elif score < 60:
        status = "⚠️"
    else:
        status = "🔴"
    
    dist_str = ", ".join([f"{r}★:{rating_counts.get(r,0)}" for r in [5,4,3,2,1]])
    anomaly_zh = []
    if five_star_ratio > 0.85:
        anomaly_zh.append(f"五星好评占比过高 ({five_star_ratio*100:.0f}%)")
    if extreme_ratio > 0.9 and one_star_ratio > 0.1:
        anomaly_zh.append("两极分化严重 (刷单与差评冲突)")
    if mid_ratings / total < 0.1 and total > 10:
        anomaly_zh.append("中评断层缺失")
    
    return DimensionResult(
        name="Rating Distribution",
        name_zh="评分分布异常度",
        score=round(score, 1),
        status=status,
        detail=f"Distribution: {dist_str}. {'; '.join(anomaly_detail) if anomaly_detail else 'Normal'}",
        detail_zh=f"星级分布: {dist_str}。{'; '.join(anomaly_zh) if anomaly_zh else '分布自然'}",
        weight=0.20
    )


def detect_vp_ratio(reviews: List[Review]) -> Optional[DimensionResult]:
    """Detection Verified Purchase Ratio"""
    vp_reviews = [r for r in reviews if r.has_vp]
    
    if len(vp_reviews) < 5:
        return None
    
    vp_count = sum(1 for r in vp_reviews if r.verified_purchase)
    vp_ratio = vp_count / len(vp_reviews)
    
    score = 0
    if vp_ratio < 0.4:
        score = 70
    elif vp_ratio < 0.5:
        score = 50
    elif vp_ratio < 0.6:
        score = 30
    else:
        score = 10
    
    if score < 30:
        status = "✅"
    elif score < 60:
        status = "⚠️"
    else:
        status = "🔴"
    
    return DimensionResult(
        name="Verified Purchase Ratio",
        name_zh="真实购买VP认证率",
        score=round(score, 1),
        status=status,
        detail=f"{vp_ratio*100:.0f}% verified purchase ({vp_count}/{len(vp_reviews)})",
        detail_zh=f"已认证购买率 {vp_ratio*100:.0f}% ({vp_count}/{len(vp_reviews)})",
        weight=0.15
    )


def detect_review_length(reviews: List[Review]) -> DimensionResult:
    """Detection Review Length and Templatization"""
    lengths = [len(r.content) for r in reviews]
    
    if not lengths:
        return DimensionResult(
            name="Review Length",
            name_zh="评论长度与模板化检测",
            score=0,
            status="✅",
            detail="No reviews",
            detail_zh="暂无评论数据",
            weight=0.05
        )
    
    avg_length = sum(lengths) / len(lengths)
    short_count = sum(1 for l in lengths if l < 50)
    short_ratio = short_count / len(lengths)
    
    if len(lengths) > 5:
        length_std = (sum((l - avg_length) ** 2 for l in lengths) / len(lengths)) ** 0.5
        cv = length_std / avg_length if avg_length > 0 else 0
    else:
        cv = 1
    
    score = 0
    if short_ratio > 0.7:
        score += 40
    if cv < 0.3 and len(lengths) > 10:
        score += 40
    
    score = min(100, score)
    
    if score < 30:
        status = "✅"
    elif score < 60:
        status = "⚠️"
    else:
        status = "🔴"
    
    return DimensionResult(
        name="Review Length",
        name_zh="评论长度与模板化检测",
        score=round(score, 1),
        status=status,
        detail=f"Avg length: {avg_length:.0f} chars, {short_ratio*100:.0f}% short (<50)",
        detail_zh=f"平均长度: {avg_length:.0f} 字符，{short_ratio*100:.0f}% 为超短评 (<50字)",
        weight=0.05
    )


def detect_keywords(reviews: List[Review]) -> DimensionResult:
    """Detection Incentivized & Fake Order Keywords"""
    suspicious_keywords = [
        'received free', 'free product', 'in exchange', 'honest review',
        'discount code', 'promotional', 'gifted', 'complimentary',
        'five stars', '5 stars', 'best ever', 'amazing product',
        'highly recommend', 'must buy', 'perfect product',
        # Chinese authentic e-commerce manipulation keywords
        '好评返现', '五星好评', '返红包', '刷单', '加微信', '免费送',
        '带图好评', '拍a发b', '免费领取', '返现', '微信返', '客服返',
        '五星好评返', '好评截图', '联系返', '免费试用'
    ]
    
    keyword_hits = 0
    for review in reviews:
        content_lower = review.content.lower()
        for keyword in suspicious_keywords:
            if keyword.lower() in content_lower:
                keyword_hits += 1
                break
    
    hit_ratio = keyword_hits / len(reviews) if reviews else 0
    score = min(100, hit_ratio * 200)
    
    if score < 30:
        status = "✅"
    elif score < 60:
        status = "⚠️"
    else:
        status = "🔴"
    
    return DimensionResult(
        name="Suspicious Keywords",
        name_zh="可疑刷单/返现关键词",
        score=round(score, 1),
        status=status,
        detail=f"{keyword_hits} reviews contain suspicious keywords",
        detail_zh=f"发现 {keyword_hits} 条评价包含利益诱导/返现/刷单等特征词",
        weight=0.05
    )


def identify_suspicious_reviews(reviews: List[Review], dimensions: List[DimensionResult]) -> List[SuspiciousReview]:
    """Identify High Risk Reviews"""
    suspicious = []
    
    generic_phrases_en = ['great', 'amazing', 'perfect', 'love it', 'best', 'excellent']
    generic_phrases_zh = ['很好', '非常好', '太棒了', '质量好', '很喜欢', '完美', '五星好评', '强烈推荐', '满意', '正品', '物流快']
    incentive_keywords = [
        'received free', 'in exchange', 'honest review', 'discount', 'free product',
        '好评返现', '五星好评', '返红包', '刷单', '加微信', '免费送', '带图好评', '返现'
    ]
    
    for review in reviews:
        risk_score = 0
        reasons = []
        reasons_zh = []
        c_lower = review.content.lower()
        
        # Short Review
        if len(review.content) < 30:
            risk_score += 20
            reasons.append("Very short review")
            reasons_zh.append("评论字数过短")
        
        # Non-VP
        if review.has_vp and not review.verified_purchase:
            risk_score += 25
            reasons.append("Not verified purchase")
            reasons_zh.append("非真实买家VP认证购买")
        
        # Extreme Rating + Template Content
        if review.has_rating and review.rating == 5:
            has_generic_en = any(p in c_lower for p in generic_phrases_en) and len(review.content) < 100
            has_generic_zh = any(p in c_lower for p in generic_phrases_zh) and len(review.content) < 60
            if has_generic_en or has_generic_zh:
                risk_score += 30
                reasons.append("Generic 5-star template")
                reasons_zh.append("通用模板化五星水评")
        
        # Suspicious Keywords
        if any(k in c_lower for k in incentive_keywords):
            risk_score += 35
            reasons.append("Contains incentivized review keywords")
            reasons_zh.append("包含好评返现/利益诱导特征词")
        
        if risk_score >= 40:
            suspicious.append(SuspiciousReview(
                content=review.content[:100] + "..." if len(review.content) > 100 else review.content,
                risk_score=min(100, risk_score),
                reasons=reasons,
                reasons_zh=reasons_zh
            ))
    
    suspicious.sort(key=lambda x: x.risk_score, reverse=True)
    return suspicious[:10]  # Top 10


def determine_analysis_level(reviews: List[Review]) -> Tuple[AnalysisLevel, List[str], List[str]]:
    """ConfirmAnalyzelayerLevelAndMissing field"""
    available = ["content"]
    missing = []
    
    has_rating = any(r.has_rating for r in reviews)
    has_date = any(r.has_date for r in reviews)
    has_vp = any(r.has_vp for r in reviews)
    has_reviewer = any(r.reviewer_name for r in reviews)
    
    if has_rating:
        available.append("rating")
    else:
        missing.append("rating")
    
    if has_date:
        available.append("date")
    else:
        missing.append("date")
    
    if has_vp:
        available.append("verified_purchase")
    else:
        missing.append("verified_purchase")
    
    if has_reviewer:
        available.append("reviewer_info")
    else:
        missing.append("reviewer_info")
    
    # Determine levelLevel
    if has_rating and has_date and has_vp:
        level = AnalysisLevel.L4_FULL
    elif has_rating and has_date:
        level = AnalysisLevel.L3_SCORED
    elif has_date:
        level = AnalysisLevel.L2_TIMED
    else:
        level = AnalysisLevel.L1_BASIC
    
    return level, available, missing


def generate_deepening_hints(missing: List[str]) -> Tuple[List[str], List[str]]:
    """GenerateDeepenHint"""
    hints_en = []
    hints_zh = []
    
    hint_map = {
        "rating": (
            "Add star ratings → Unlock 'Rating Distribution Analysis'",
            "补充星级评分数据 → 解锁「评分分布离散度检测」"
        ),
        "date": (
            "Add review dates → Unlock 'Time Clustering Detection'",
            "补充评价发布日期 → 解锁「时间爆发聚集度检测」"
        ),
        "verified_purchase": (
            "Add VP status → Unlock 'Verified Purchase Analysis'",
            "补充买家VP认证状态 → 解锁「真实购买转化率排查」"
        ),
        "reviewer_info": (
            "Add reviewer info → Unlock 'Account Profile Analysis'",
            "补充买家账号信息 → 解锁「职业刷单账号画像检测」"
        ),
    }
    
    for field in missing:
        if field in hint_map:
            hints_en.append(hint_map[field][0])
            hints_zh.append(hint_map[field][1])
    
    return hints_en, hints_zh


def analyze_reviews(reviews: List[Review], asin: str = "UNKNOWN") -> AnalysisResult:
    """MainAnalyzeFunction"""
    if not reviews:
        return AnalysisResult(
            asin=asin,
            total_reviews=0,
            analysis_level=AnalysisLevel.L1_BASIC,
            authenticity_score=50,
            risk_level=RiskLevel.MEDIUM,
            dimensions=[],
            suspicious_reviews=[],
            available_fields=[],
            missing_fields=["content"],
            deepening_hints=["Please provide review data"],
            deepening_hints_zh=["Please provideReview Countdata"],
            summary="No reviews to analyze",
            summary_zh="noReview Countdata"
        )
    
    # ConfirmAnalyzelayerLevel
    level, available, missing = determine_analysis_level(reviews)
    hints_en, hints_zh = generate_deepening_hints(missing)
    
    # ExecuteDetection
    dimensions = []
    
    # L1: BasicDetection (AlwaysExecute)
    dimensions.append(detect_content_similarity(reviews))
    dimensions.append(detect_review_length(reviews))
    dimensions.append(detect_keywords(reviews))
    
    # L2+: TimeDetection
    time_result = detect_time_clustering(reviews)
    if time_result:
        dimensions.append(time_result)
    
    # L3+: RatingDetection
    rating_result = detect_rating_distribution(reviews)
    if rating_result:
        dimensions.append(rating_result)
    
    # L4: VPDetection
    vp_result = detect_vp_ratio(reviews)
    if vp_result:
        dimensions.append(vp_result)
    
    # CalculateComprehensiveScore (WeightedAverageSuspiciousDegree，ThenConvert toAuthenticityScore)
    total_weight = sum(d.weight for d in dimensions)
    if total_weight > 0:
        suspicion_score = sum(d.score * d.weight for d in dimensions) / total_weight
    else:
        suspicion_score = 50
    
    authenticity_score = max(0, min(100, 100 - suspicion_score))
    
    # ConfirmRiskGrade
    if authenticity_score >= 70:
        risk_level = RiskLevel.LOW
    elif authenticity_score >= 50:
        risk_level = RiskLevel.MEDIUM
    elif authenticity_score >= 30:
        risk_level = RiskLevel.HIGH
    else:
        risk_level = RiskLevel.CRITICAL
    
    # IdentifySuspiciousReview
    suspicious = identify_suspicious_reviews(reviews, dimensions)
    
    # Generate Summary
    risk_text = {
        RiskLevel.LOW: ("Low risk - Reviews appear authentic", "低风险 - 评价真实度高，未见异常刷单迹象"),
        RiskLevel.MEDIUM: ("Medium risk - Some concerns detected", "中度风险 - 存在部分轻度聚集或模板化可疑点"),
        RiskLevel.HIGH: ("High risk - Multiple red flags", "高风险 - 触发多项高危特征 (集中刷单/水军嫌疑大)"),
        RiskLevel.CRITICAL: ("Critical risk - Likely fake reviews", "极高风险 - 极大概率存在虚假操纵/好评返现刷单"),
    }
    
    summary_en = f"{risk_text[risk_level][0]}. Analyzed {len(reviews)} reviews at {level.value} level."
    summary_zh = f"{risk_text[risk_level][1]}。共分析 {len(reviews)} 条评价，分析深度层级为 {level.value}。"
    
    return AnalysisResult(
        asin=asin,
        total_reviews=len(reviews),
        analysis_level=level,
        authenticity_score=round(authenticity_score),
        risk_level=risk_level,
        dimensions=dimensions,
        suspicious_reviews=suspicious,
        available_fields=available,
        missing_fields=missing,
        deepening_hints=hints_en,
        deepening_hints_zh=hints_zh,
        summary=summary_en,
        summary_zh=summary_zh
    )


# ============================================================
# OutputFormat
# ============================================================

def format_report(result: AnalysisResult, lang: str = "en") -> str:
    """FormatReport"""
    risk_icons = {
        RiskLevel.LOW: "✅",
        RiskLevel.MEDIUM: "⚠️",
        RiskLevel.HIGH: "🔴",
        RiskLevel.CRITICAL: "💀",
    }
    
    if lang == "zh":
        lines = [
            f"📊 **商品评价真实性与防刷单诊断报告**",
            f"",
            f"**ASIN**: {result.asin}",
            f"**评价分析样本**: {result.total_reviews} 条",
            f"**分析深度层级**: {result.analysis_level.value}",
            f"",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"",
            f"## 评价真实度得分: {result.authenticity_score}/100 {risk_icons[result.risk_level]}",
            f"",
            f"{result.summary_zh}",
            f"",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"",
            f"## 多维度特征排查",
            f"",
        ]
        
        for d in result.dimensions:
            lines.append(f"{d.status} **{d.name_zh}**: {d.score:.0f}/100")
            lines.append(f"   {d.detail_zh}")
            lines.append("")
        
        if result.suspicious_reviews:
            lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            lines.append("")
            lines.append(f"## 疑似刷单/高风险评价 (Top {len(result.suspicious_reviews)})")
            lines.append("")
            for i, sr in enumerate(result.suspicious_reviews[:5], 1):
                lines.append(f"**{i}. 风险指数 {sr.risk_score:.0f}%**")
                lines.append(f'   "{sr.content}"')
                lines.append(f"   判定原因: {', '.join(sr.reasons_zh)}")
                lines.append("")
        
        if result.deepening_hints_zh:
            lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            lines.append("")
            lines.append("🔍 **若需更高精度诊断，建议补充以下字段：**")
            lines.append("")
            for hint in result.deepening_hints_zh:
                lines.append(f"• {hint}")
    else:
        lines = [
            f"📊 **Review Authenticity Report**",
            f"",
            f"**ASIN**: {result.asin}",
            f"**Reviews**: {result.total_reviews}",
            f"**Analysis Level**: {result.analysis_level.value}",
            f"",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"",
            f"## Authenticity Score: {result.authenticity_score}/100 {risk_icons[result.risk_level]}",
            f"",
            f"{result.summary}",
            f"",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"",
            f"## Detection Dimensions",
            f"",
        ]
        
        for d in result.dimensions:
            lines.append(f"{d.status} **{d.name}**: {d.score:.0f}/100")
            lines.append(f"   {d.detail}")
            lines.append("")
        
        if result.suspicious_reviews:
            lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            lines.append("")
            lines.append(f"## Suspicious Reviews (Top {len(result.suspicious_reviews)})")
            lines.append("")
            for i, sr in enumerate(result.suspicious_reviews[:5], 1):
                lines.append(f"**{i}. Risk {sr.risk_score:.0f}%**")
                lines.append(f'   "{sr.content}"')
                lines.append(f"   Reasons: {', '.join(sr.reasons)}")
                lines.append("")
        
        if result.deepening_hints:
            lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            lines.append("")
            lines.append("🔍 **Want more accurate analysis? Add the following:**")
            lines.append("")
            for hint in result.deepening_hints:
                lines.append(f"• {hint}")
    
    return "\n".join(lines)


# ============================================================
# Parse
# ============================================================

def parse_simple_reviews(text: str) -> List[Review]:
    """Parse simple text reviews separated by paragraphs"""
    reviews = []
    paragraphs = re.split(r'\n\n+', text.strip())
    
    for para in paragraphs:
        para = para.strip()
        if len(para) >= 2:
            review = Review(content=para)
            star_match = re.search(r'(\d)\s*(?:star|★|⭐|星)', para, re.I)
            if star_match:
                review.rating = int(star_match.group(1))
            date_match = re.search(r'(\d{4}-\d{2}-\d{2}|\w+\s+\d{1,2},?\s+\d{4})', para)
            if date_match:
                review.date = date_match.group(1)
            if 'verified purchase' in para.lower() or 'vp' in para.lower() or '已购买' in para:
                review.verified_purchase = True
            elif 'not verified' in para.lower() or '未认证' in para:
                review.verified_purchase = False
            reviews.append(review)
    return reviews


# ============================================================
# CLI Entry Point
# ============================================================

def main():
    """CLI Entry Point"""
    test_reviews = [
        Review(content="Great product! Works perfectly. Highly recommend to everyone.", rating=5, verified_purchase=True, date="2024-01-15"),
        Review(content="Amazing! Best purchase ever. Love it!", rating=5, verified_purchase=False, date="2024-01-15"),
        Review(content="Great product! Works perfectly. Must buy!", rating=5, verified_purchase=False, date="2024-01-16"),
        Review(content="Received free product in exchange for honest review. It's good.", rating=5, verified_purchase=False, date="2024-01-16"),
        Review(content="Excellent quality, fast shipping. Very satisfied with purchase.", rating=5, verified_purchase=True, date="2024-01-20"),
        Review(content="Not as described. Cheap quality.", rating=1, verified_purchase=True, date="2024-02-01"),
        Review(content="Perfect!", rating=5, verified_purchase=False, date="2024-01-16"),
        Review(content="Good value for money. Does what it says.", rating=4, verified_purchase=True, date="2024-02-15"),
        Review(content="Five stars! Amazing product!", rating=5, verified_purchase=False, date="2024-01-17"),
        Review(content="Decent product for the price.", rating=3, verified_purchase=True, date="2024-03-01"),
    ]
    
    args = sys.argv[1:]
    lang = "zh" if "--zh" in args else "en"
    args = [a for a in args if a != "--zh"]
    
    if "--help" in args or "-h" in args:
        print("""Usage: python3 analyzer.py [OPTIONS] [REVIEWS_DATA]
Options:
  --demo            Run with built-in test review dataset
  --zh              Output report in Chinese
  --json <string>   Pass JSON array of reviews
  --help, -h        Show this help message
""")
        return
        
    if len(args) > 0 and args[0] != "--demo":
        arg = args[0]
        if arg.startswith('['):
            try:
                data = json.loads(arg)
                test_reviews = [Review(**r) for r in data]
            except Exception as e:
                print(f"Error parsing JSON: {e}")
                sys.exit(1)
        else:
            test_reviews = parse_simple_reviews(arg)
    
    result = analyze_reviews(test_reviews, asin="B08XXXXX")
    print(format_report(result, lang=lang))


if __name__ == "__main__":
    main()
