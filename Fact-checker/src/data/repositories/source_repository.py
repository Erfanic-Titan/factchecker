"""
ریپازیتوری مخصوص عملیات مربوط به منابع فکت‌چک.
این ماژول مسئول مدیریت و نگهداری منابع مورد استفاده در فرآیند فکت‌چکینگ است.
"""

from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy import select, and_, or_, desc, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from urllib.parse import urlparse

from ..models import Source, FactCheck
from .base_repository import BaseRepository
from ...utils.helpers import get_logger

logger = get_logger(__name__)

class SourceRepository(BaseRepository[Source]):
    """
    ریپازیتوری برای مدیریت منابع فکت‌چک.
    این کلاس عملیات مربوط به منابع مورد استفاده در فکت‌چک‌ها را پیاده‌سازی می‌کند
    و امکان جستجو، ارزیابی اعتبار و مدیریت منابع را فراهم می‌کند.
    """

    def __init__(self, session: AsyncSession):
        """
        مقداردهی اولیه ریپازیتوری منابع
        
        Args:
            session: نشست فعال دیتابیس
        """
        super().__init__(Source, session)

    async def get_by_url(self, url: str) -> Optional[Source]:
        """
        دریافت منبع با URL مشخص
        
        Args:
            url: آدرس منبع
            
        Returns:
            منبع یافت شده یا None
        """
        try:
            # نرمال‌سازی URL برای جستجوی دقیق‌تر
            parsed_url = urlparse(url)
            normalized_url = f"{parsed_url.netloc}{parsed_url.path}"
            
            query = (
                select(Source)
                .where(Source.url.ilike(f"%{normalized_url}%"))
            )
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting source by URL: {str(e)}")
            return None

    async def get_by_factcheck(self, factcheck_id: int) -> List[Source]:
        """
        دریافت تمام منابع مرتبط با یک فکت‌چک
        
        Args:
            factcheck_id: شناسه فکت‌چک
            
        Returns:
            لیست منابع مرتبط با فکت‌چک
        """
        try:
            query = (
                select(Source)
                .where(Source.factcheck_id == factcheck_id)
                .order_by(desc(Source.reliability_score))
            )
            result = await self.session.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting sources for fact check: {str(e)}")
            return []

    async def add_sources_to_factcheck(
        self,
        factcheck_id: int,
        sources: List[Dict]
    ) -> List[Source]:
        """
        افزودن چندین منبع به یک فکت‌چک
        
        Args:
            factcheck_id: شناسه فکت‌چک
            sources: لیست دیکشنری‌های حاوی اطلاعات منابع
            
        Returns:
            لیست منابع اضافه شده
        """
        try:
            added_sources = []
            for source_data in sources:
                source_data["factcheck_id"] = factcheck_id
                source = await self.create(**source_data)
                if source:
                    added_sources.append(source)
            
            return added_sources
        except SQLAlchemyError as e:
            logger.error(f"Error adding sources to fact check: {str(e)}")
            return []

    async def get_most_reliable_sources(self, limit: int = 10) -> List[Source]:
        """
        دریافت معتبرترین منابع بر اساس امتیاز اعتبار
        
        Args:
            limit: تعداد نتایج
            
        Returns:
            لیست منابع معتبر
        """
        try:
            query = (
                select(Source)
                .where(Source.reliability_score.isnot(None))
                .order_by(desc(Source.reliability_score))
                .limit(limit)
            )
            result = await self.session.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting most reliable sources: {str(e)}")
            return []

    async def update_reliability_score(
        self,
        source_id: int,
        new_score: float
    ) -> Optional[Source]:
        """
        به‌روزرسانی امتیاز اعتبار یک منبع
        
        Args:
            source_id: شناسه منبع
            new_score: امتیاز جدید
            
        Returns:
            منبع به‌روز شده یا None در صورت خطا
        """
        try:
            # اطمینان از اینکه امتیاز در محدوده 0 تا 1 است
            new_score = max(0.0, min(1.0, new_score))
            return await self.update(source_id, reliability_score=new_score)
        except SQLAlchemyError as e:
            logger.error(f"Error updating source reliability score: {str(e)}")
            return None

    async def get_domain_statistics(self) -> Dict[str, Dict]:
        """
        دریافت آمار منابع بر اساس دامنه
        
        Returns:
            دیکشنری حاوی آمار هر دامنه
        """
        try:
            all_sources = await self.get_all()
            domain_stats = {}
            
            for source in all_sources:
                try:
                    domain = urlparse(source.url).netloc
                    if domain not in domain_stats:
                        domain_stats[domain] = {
                            "count": 0,
                            "avg_reliability": 0.0,
                            "sources": []
                        }
                    
                    stats = domain_stats[domain]
                    stats["count"] += 1
                    if source.reliability_score:
                        current_avg = stats["avg_reliability"]
                        stats["avg_reliability"] = (
                            (current_avg * (stats["count"] - 1) + source.reliability_score)
                            / stats["count"]
                        )
                    stats["sources"].append(source)
                except Exception as e:
                    logger.warning(f"Error processing URL {source.url}: {str(e)}")
                    continue
            
            return domain_stats
        except SQLAlchemyError as e:
            logger.error(f"Error getting domain statistics: {str(e)}")
            return {}

    async def find_similar_sources(
        self,
        url: str,
        threshold: float = 0.8
    ) -> List[Source]:
        """
        یافتن منابع مشابه بر اساس URL
        
        Args:
            url: آدرس منبع
            threshold: آستانه شباهت (بین 0 و 1)
            
        Returns:
            لیست منابع مشابه
        """
        try:
            # استخراج دامنه و مسیر از URL
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            path = parsed_url.path
            
            # جستجوی منابع با دامنه مشابه
            query = (
                select(Source)
                .where(Source.url.ilike(f"%{domain}%"))
            )
            result = await self.session.execute(query)
            similar_sources = result.scalars().all()
            
            # فیلتر کردن بر اساس شباهت مسیر
            from difflib import SequenceMatcher
            
            def calculate_similarity(s1: str, s2: str) -> float:
                return SequenceMatcher(None, s1, s2).ratio()
            
            filtered_sources = [
                source for source in similar_sources
                if calculate_similarity(
                    urlparse(source.url).path,
                    path
                ) >= threshold
            ]
            
            return filtered_sources
        except SQLAlchemyError as e:
            logger.error(f"Error finding similar sources: {str(e)}")
            return []

    async def cleanup_duplicate_sources(self) -> int:
        """
        حذف منابع تکراری با حفظ منبع با بیشترین امتیاز اعتبار
        
        Returns:
            تعداد منابع حذف شده
        """
        try:
            # گروه‌بندی منابع بر اساس URL
            domain_stats = await self.get_domain_statistics()
            deleted_count = 0
            
            for domain, stats in domain_stats.items():
                if stats["count"] > 1:
                    # مرتب‌سازی منابع بر اساس امتیاز اعتبار
                    sorted_sources = sorted(
                        stats["sources"],
                        key=lambda x: x.reliability_score or 0,
                        reverse=True
                    )
                    
                    # حذف نسخه‌های تکراری با حفظ بهترین نسخه
                    for source in sorted_sources[1:]:
                        await self.delete(source.id)
                        deleted_count += 1
            
            await self.session.commit()
            return deleted_count
        except SQLAlchemyError as e:
            logger.error(f"Error cleaning up duplicate sources: {str(e)}")
            await self.session.rollback()
            return 0

    async def validate_source_url(self, url: str) -> bool:
        """
        اعتبارسنجی URL منبع
        
        Args:
            url: آدرس منبع
            
        Returns:
            True اگر URL معتبر باشد، False در غیر این صورت
        """
        try:
            parsed_url = urlparse(url)
            return all([
                parsed_url.scheme in ['http', 'https'],
                parsed_url.netloc,
                len(url) <= 2048  # محدودیت طول URL
            ])
        except Exception as e:
            logger.error(f"Error validating source URL: {str(e)}")
            return False

    async def get_source_history(
        self,
        url: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """
        دریافت تاریخچه استفاده از یک منبع
        
        Args:
            url: آدرس منبع
            start_date: تاریخ شروع
            end_date: تاریخ پایان
            
        Returns:
            لیست دیکشنری‌های حاوی اطلاعات تاریخچه
        """
        try:
            conditions = [Source.url.ilike(f"%{url}%")]
            
            if start_date:
                conditions.append(Source.created_at >= start_date)
            if end_date:
                conditions.append(Source.created_at <= end_date)
                
            query = (
                select(Source)
                .options(joinedload(Source.factcheck))
                .where(and_(*conditions))
                .order_by(desc(Source.created_at))
            )
            
            result = await self.session.execute(query)
            sources = result.unique().scalars().all()
            
            history = []
            for source in sources:
                history.append({
                    "source_id": source.id,
                    "url": source.url,
                    "title": source.title,
                    "reliability_score": source.reliability_score,
                    "created_at": source.created_at,
                    "factcheck_id": source.factcheck_id,
                    "factcheck_result": source.factcheck.result if source.factcheck else None
                })
            
            return history
        except SQLAlchemyError as e:
            logger.error(f"Error getting source history: {str(e)}")
            return []
