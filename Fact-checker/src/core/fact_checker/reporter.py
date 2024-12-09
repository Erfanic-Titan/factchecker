"""
Reporter module for formatting and presenting fact-checking results.
"""
from typing import Dict, List, Optional
import json
import logging
from datetime import datetime

from ...data.models.models import FactCheckResult
from ...utils.helpers import format_date, calculate_percentage

logger = logging.getLogger(__name__)

class FactReporter:
    """Handles formatting and presentation of fact-checking results."""
    
    def __init__(self):
        self.verification_emojis = {
            "VERIFIED": "✅",
            "FALSE": "❌",
            "PARTIALLY_TRUE": "⚠️",
            "UNVERIFIED": "❓"
        }
        
    async def generate_report(
        self,
        result: FactCheckResult,
        format_type: str = "telegram"
    ) -> str:
        """
        Generate a formatted report of fact-checking results.
        
        Args:
            result: FactCheckResult object containing analysis results
            format_type: Output format type ("telegram", "json", "text")
            
        Returns:
            Formatted report string
        """
        try:
            if format_type == "telegram":
                return await self._format_telegram_report(result)
            elif format_type == "json":
                return await self._format_json_report(result)
            elif format_type == "text":
                return await self._format_text_report(result)
            else:
                raise ValueError(f"Unsupported format type: {format_type}")
                
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            raise

    async def _format_telegram_report(self, result: FactCheckResult) -> str:
        """Format results for Telegram message."""
        emoji = self.verification_emojis.get(result.verification_status, "❓")
        credibility_percentage = calculate_percentage(result.credibility_score)
        
        report = [
            f"🔍 فکت‌چک ادعا:",
            f'"{result.claim_text}"',
            "",
            f"{emoji} نتیجه بررسی: {self._get_status_text(result.verification_status)}",
            f"📊 درجه صحت: {credibility_percentage}%",
            "",
            "⚡️ خلاصه سریع:",
            self._format_summary(result),
            "",
            "🔎 دلایل:",
            self._format_evidence(result.evidence),
            "",
            "📚 منابع معتبر:",
            self._format_sources(result.sources),
            "",
            "✅ اطلاعات درست:",
            self._format_correct_info(result),
            "",
            f"🔄 آخرین به‌روزرسانی: {format_date(result.analyzed_at)}"
        ]
        
        return "\n".join(report)

    async def _format_json_report(self, result: FactCheckResult) -> str:
        """Format results as JSON string."""
        report_dict = {
            "claim": result.claim_text,
            "verification_status": result.verification_status,
            "credibility_score": result.credibility_score,
            "evidence": result.evidence,
            "sources": result.sources,
            "analyzed_at": result.analyzed_at.isoformat()
        }
        return json.dumps(report_dict, ensure_ascii=False, indent=2)

    async def _format_text_report(self, result: FactCheckResult) -> str:
        """Format results as plain text."""
        report = [
            "Fact Check Report",
            "================",
            f"Claim: {result.claim_text}",
            f"Status: {result.verification_status}",
            f"Credibility: {calculate_percentage(result.credibility_score)}%",
            "",
            "Evidence:",
            self._format_evidence(result.evidence),
            "",
            "Sources:",
            self._format_sources(result.sources),
            "",
            f"Analysis Date: {format_date(result.analyzed_at)}"
        ]
        return "\n".join(report)

    def _get_status_text(self, status: str) -> str:
        """Convert verification status to Persian text."""
        status_map = {
            "VERIFIED": "تأیید شده",
            "FALSE": "نادرست",
            "PARTIALLY_TRUE": "نسبتاً درست",
            "UNVERIFIED": "غیرقابل تأیید"
        }
        return status_map.get(status, status)

    def _format_summary(self, result: FactCheckResult) -> str:
        """Format the quick summary section."""
        summary_points = []
        
        # Add main verification point
        if result.verification_status == "VERIFIED":
            summary_points.append("این ادعا با منابع معتبر تأیید شده است")
        elif result.verification_status == "FALSE":
            summary_points.append("این ادعا با شواهد موجود رد می‌شود")
        elif result.verification_status == "PARTIALLY_TRUE":
            summary_points.append("این ادعا تا حدی صحیح است اما نیاز به توضیحات تکمیلی دارد")
            
        # Add context from evidence
        if result.evidence:
            main_evidence = result.evidence[0]
            summary_points.append(main_evidence.get('content', ''))
            
        return "\n".join(summary_points)

    def _format_evidence(self, evidence: List[Dict]) -> str:
        """Format the evidence section."""
        if not evidence:
            return "شواهد کافی برای بررسی این ادعا یافت نشد"
            
        formatted_points = []
        for i, item in enumerate(evidence, 1):
            if item['type'] == 'SOURCE':
                formatted_points.append(
                    f"{i}. {item['content']} "
                    f"(اعتبار منبع: {calculate_percentage(item['credibility_score'])}%)"
                )
            elif item['type'] == 'SIMILAR_CLAIM':
                formatted_points.append(
                    f"{i}. ادعای مشابه: {item['content']} "
                    f"({self._get_status_text(item['verification_status'])})"
                )
                
        return "\n".join(formatted_points)

    def _format_sources(self, sources: List[Dict]) -> str:
        """Format the sources section."""
        if not sources:
            return "منابع معتبر مرتبط یافت نشد"
            
        formatted_sources = []
        for source in sources:
            if source.get('url'):
                formatted_sources.append(f"• {source['title']}\n  {source['url']}")
            else:
                formatted_sources.append(f"• {source['title']}")
                
        return "\n".join(formatted_sources)

    def _format_correct_info(self, result: FactCheckResult) -> str:
        """Format the correct information section."""
        # This would be generated based on the verified facts
        correct_info = []
        
        if hasattr(result, 'verified_facts'):
            for fact in result.verified_facts:
                correct_info.append(f"• {fact}")
        else:
            correct_info.append("اطلاعات تکمیلی در حال بررسی است")
            
        return "\n".join(correct_info)

    def _format_trend_info(self, result: FactCheckResult) -> str:
        """Format trend information about the claim."""
        if not hasattr(result, 'trend_data'):
            return ""
            
        trend_info = [
            "📈 روند انتشار:",
            f"اولین انتشار: {result.trend_data.get('first_seen', 'نامشخص')}",
            f"اوج انتشار: {result.trend_data.get('peak_time', 'نامشخص')}",
            f"میزان بازنشر: {result.trend_data.get('share_level', 'نامشخص')}"
        ]
        
        return "\n".join(trend_info)

    def _format_recommendations(self, result: FactCheckResult) -> str:
        """Format recommendations based on the fact check results."""
        recommendations = ["📌 توصیه‌های تکمیلی:"]
        
        # Add general recommendations
        recommendations.extend([
            "• از منابع معتبر استفاده کنید",
            "• اخبار را از چند منبع مستقل بررسی کنید",
            "• به تاریخ انتشار مطالب توجه کنید"
        ])
        
        # Add specific recommendations based on claim type
        if hasattr(result, 'claim_type'):
            if result.claim_type == 'SCIENTIFIC':
                recommendations.append("• به مقالات علمی معتبر مراجعه کنید")
            elif result.claim_type == 'STATISTICAL':
                recommendations.append("• آمار را با منابع رسمی مقایسه کنید")
                
        return "\n".join(recommendations)