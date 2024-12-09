"""
سرویس راستی‌آزمایی با استفاده از Google Fact Check Tools API.
این ماژول برای جستجو و دریافت نتایج راستی‌آزمایی از API گوگل استفاده می‌شود
و نتایج را با سایر سرویس‌های تشخیص اخبار جعلی ترکیب می‌کند.
"""

import aiohttp
import logging
from typing import Dict, List, Optional
from datetime import datetime
import json
from urllib.parse import quote

from ...utils.helpers import get_logger
from ...config.config import GOOGLE_FACTCHECK_API_KEY

logger = get_logger(__name__)

class GoogleFactCheckService:
    """کلاس اصلی برای تعامل با Google Fact Check Tools API."""
    
    def __init__(self):
        """مقداردهی اولیه سرویس Google Fact Check."""
        self.api_key = GOOGLE_FACTCHECK_API_KEY
        self.base_url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
        
        # پیکربندی درخواست‌ها
        self.request_config = {
            'timeout': 10,  # زمان انتظار به ثانیه
            'max_retries': 3,  # حداکثر تعداد تلاش مجدد
            'language': 'fa'  # زبان پیش‌فرض برای جستجو
        }

    async def check_claim(
        self,
        claim_text: str,
        language: Optional[str] = None
    ) -> Dict:
        """
        جستجوی یک ادعا در Google Fact Check Tools.
        
        این متد ادعای مورد نظر را در پایگاه داده جهانی راستی‌آزمایی گوگل جستجو می‌کند
        و نتایج راستی‌آزمایی‌های موجود را برمی‌گرداند.
        
        Args:
            claim_text: متن ادعا
            language: کد زبان (پیش‌فرض: فارسی)
            
        Returns:
            دیکشنری نتایج راستی‌آزمایی
        """
        try:
            # ساخت پارامترهای درخواست
            params = {
                'key': self.api_key,
                'query': claim_text,
                'languageCode': language or self.request_config['language']
            }
            
            # ارسال درخواست به API
            async with aiohttp.ClientSession() as session:
                for attempt in range(self.request_config['max_retries']):
                    try:
                        async with session.get(
                            self.base_url,
                            params=params,
                            timeout=self.request_config['timeout']
                        ) as response:
                            if response.status == 200:
                                data = await response.json()
                                return self._process_factcheck_response(data)
                            else:
                                logger.warning(
                                    f"خطای {response.status} از Google Fact Check API"
                                )
                                
                    except asyncio.TimeoutError:
                        if attempt == self.request_config['max_retries'] - 1:
                            raise
                        await asyncio.sleep(1)  # انتظار قبل از تلاش مجدد
                        
            return {
                'status': 'error',
                'message': 'خطا در دریافت پاسخ از API'
            }
            
        except Exception as e:
            logger.error(f"خطا در راستی‌آزمایی با Google: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def _process_factcheck_response(self, response_data: Dict) -> Dict:
        """
        پردازش پاسخ دریافتی از Google Fact Check API.
        
        این متد پاسخ خام API را پردازش کرده و اطلاعات مفید را استخراج می‌کند.
        همچنین نتایج را برای ترکیب با سایر سرویس‌ها آماده می‌کند.
        
        Args:
            response_data: پاسخ خام API
            
        Returns:
            دیکشنری پردازش شده نتایج
        """
        try:
            if not response_data.get('claims'):
                return {
                    'status': 'no_results',
                    'message': 'نتیجه‌ای برای این ادعا یافت نشد'
                }
            
            # پردازش نتایج
            processed_claims = []
            for claim in response_data['claims']:
                fact_checks = []
                
                # پردازش راستی‌آزمایی‌ها
                for review in claim.get('claimReview', []):
                    fact_checks.append({
                        'publisher': {
                            'name': review.get('publisher', {}).get('name'),
                            'site': review.get('publisher', {}).get('site')
                        },
                        'rating': self._normalize_rating(
                            review.get('textualRating'),
                            review.get('rating')
                        ),
                        'title': review.get('title'),
                        'url': review.get('url'),
                        'language': review.get('languageCode'),
                        'review_date': review.get('reviewDate')
                    })
                
                processed_claims.append({
                    'text': claim.get('text'),
                    'claimant': claim.get('claimant'),
                    'claim_date': claim.get('claimDate'),
                    'fact_checks': fact_checks
                })
            
            # محاسبه آمار کلی
            verification_stats = self._calculate_verification_stats(processed_claims)
            
            return {
                'status': 'success',
                'claims_found': len(processed_claims),
                'claims': processed_claims,
                'verification_stats': verification_stats,
                'checked_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"خطا در پردازش پاسخ Google Fact Check: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def _normalize_rating(
        self,
        textual_rating: Optional[str],
        numeric_rating: Optional[float]
    ) -> Dict:
        """
        نرمال‌سازی امتیاز راستی‌آزمایی.
        
        این متد امتیازهای مختلف (متنی و عددی) را به یک فرمت استاندارد
        تبدیل می‌کند تا با سایر سرویس‌ها سازگار باشند.
        
        Args:
            textual_rating: امتیاز متنی
            numeric_rating: امتیاز عددی
            
        Returns:
            دیکشنری امتیاز نرمال شده
        """
        # تبدیل امتیاز متنی به وضعیت استاندارد
        status_mapping = {
            'true': 'VERIFIED',
            'mostly true': 'PARTIALLY_TRUE',
            'half true': 'PARTIALLY_TRUE',
            'mostly false': 'FALSE',
            'false': 'FALSE',
            'pants on fire': 'FALSE'
        }
        
        normalized_status = 'UNVERIFIED'
        confidence = 0.5
        
        if textual_rating:
            # تبدیل به حروف کوچک برای مقایسه
            lower_rating = textual_rating.lower()
            for pattern, status in status_mapping.items():
                if pattern in lower_rating:
                    normalized_status = status
                    # تنظیم اطمینان بر اساس وضعیت
                    if status == 'VERIFIED':
                        confidence = 0.9
                    elif status == 'PARTIALLY_TRUE':
                        confidence = 0.6
                    elif status == 'FALSE':
                        confidence = 0.1
                    break
        
        # استفاده از امتیاز عددی اگر موجود باشد
        if numeric_rating is not None:
            confidence = max(0.0, min(1.0, numeric_rating))
            # تنظیم وضعیت بر اساس اطمینان
            if confidence >= 0.8:
                normalized_status = 'VERIFIED'
            elif confidence >= 0.4:
                normalized_status = 'PARTIALLY_TRUE'
            else:
                normalized_status = 'FALSE'
        
        return {
            'status': normalized_status,
            'confidence': confidence,
            'original_rating': textual_rating or str(numeric_rating)
        }

    def _calculate_verification_stats(self, claims: List[Dict]) -> Dict:
        """
        محاسبه آمار کلی راستی‌آزمایی‌ها.
        
        این متد آمار و شاخص‌های مختلف را از نتایج راستی‌آزمایی
        محاسبه می‌کند.
        
        Args:
            claims: لیست ادعاهای راستی‌آزمایی شده
            
        Returns:
            دیکشنری آمار راستی‌آزمایی
        """
        total_reviews = 0
        status_counts = {
            'VERIFIED': 0,
            'PARTIALLY_TRUE': 0,
            'FALSE': 0,
            'UNVERIFIED': 0
        }
        
        confidence_sum = 0
        
        for claim in claims:
            for fact_check in claim['fact_checks']:
                total_reviews += 1
                rating = fact_check['rating']
                status_counts[rating['status']] += 1
                confidence_sum += rating['confidence']
        
        # محاسبه میانگین اطمینان
        avg_confidence = confidence_sum / total_reviews if total_reviews > 0 else 0
        
        # محاسبه درصدها
        percentages = {
            status: (count / total_reviews * 100 if total_reviews > 0 else 0)
            for status, count in status_counts.items()
        }
        
        return {
            'total_reviews': total_reviews,
            'status_counts': status_counts,
            'status_percentages': percentages,
            'average_confidence': avg_confidence,
            'credibility_score': self._calculate_credibility_score(
                status_counts,
                total_reviews
            )
        }

    def _calculate_credibility_score(
        self,
        status_counts: Dict[str, int],
        total_reviews: int
    ) -> float:
        """
        محاسبه امتیاز اعتبار کلی.
        
        این متد بر اساس توزیع وضعیت‌های مختلف راستی‌آزمایی،
        یک امتیاز کلی برای اعتبار ادعا محاسبه می‌کند.
        
        Args:
            status_counts: تعداد هر وضعیت
            total_reviews: کل راستی‌آزمایی‌ها
            
        Returns:
            امتیاز اعتبار بین 0 تا 1
        """
        if total_reviews == 0:
            return 0.5
        
        # وزن هر وضعیت در محاسبه امتیاز نهایی
        weights = {
            'VERIFIED': 1.0,
            'PARTIALLY_TRUE': 0.5,
            'FALSE': 0.0,
            'UNVERIFIED': 0.5
        }
        
        weighted_sum = sum(
            status_counts[status] * weight
            for status, weight in weights.items()
        )
        
        return weighted_sum / total_reviews