"""
ریپازیتوری مخصوص عملیات مربوط به فکت‌چک‌ها
"""

from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import FactCheck, User, Category, Tag, FactCheckStatus, FactCheckResult
from .base_repository import BaseRepository
from ...utils.helpers import get_logger

logger = get_logger(__name__)

class FactCheckRepository(BaseRepository[FactCheck]):
    """
    ریپازیتوری برای مدیریت عملیات مربوط به فکت‌چک‌ها.
    این کلاس علاوه بر عملیات پایه، متدهای تخصصی برای جستجو و فیلتر فکت‌چک‌ها را نیز ارائه می‌دهد.
    """

    def __init__(self, session: AsyncSession):
        """
        مقداردهی اولیه ریپازیتوری فکت‌چک
        
        Args:
            session: نشست فعال دیتابیس
        """
        super().__init__(FactCheck, session)

    async def get_by_id_with_relations(self, id: int) -> Optional[FactCheck]:
        """
        دریافت فکت‌چک به همراه تمام روابط آن
        
        Args:
            id: شناسه فکت‌چک
            
        Returns:
            نمونه فکت‌چک با تمام روابط یا None
        """
        try:
            query = (
                select(FactCheck)
                .options(
                    joinedload(FactCheck.user),
                    joinedload(FactCheck.category),
                    joinedload(FactCheck.sources),
                    joinedload(FactCheck.media),
                    joinedload(FactCheck.report),
                    joinedload(FactCheck.tags),
                    joinedload(FactCheck.feedbacks)
                )
                .where(FactCheck.id == id)
            )
            result = await self.session.execute(query)
            return result.unique().scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting fact check with relations: {str(e)}")
            return None

    async def get_by_user(
        self, 
        user_id: int, 
        status: Optional[FactCheckStatus] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[FactCheck]:
        """
        دریافت فکت‌چک‌های یک کاربر با امکان فیلتر بر اساس وضعیت
        
        Args:
            user_id: شناسه کاربر
            status: وضعیت فکت‌چک (اختیاری)
            limit: تعداد نتایج
            offset: تعداد رد شده از ابتدا
            
        Returns:
            لیست فکت‌چک‌های کاربر
        """
        try:
            query = (
                select(FactCheck)
                .where(FactCheck.user_id == user_id)
                .options(joinedload(FactCheck.category))
                .order_by(desc(FactCheck.created_at))
            )
            
            if status:
                query = query.where(FactCheck.status == status)
            
            query = query.limit(limit).offset(offset)
            result = await self.session.execute(query)
            return result.scalars().unique().all()
        except Exception as e:
            logger.error(f"Error getting user fact checks: {str(e)}")
            return []

    async def search(
        self,
        keyword: Optional[str] = None,
        category_id: Optional[int] = None,
        status: Optional[FactCheckStatus] = None,
        result_type: Optional[FactCheckResult] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[FactCheck]:
        """
        جستجوی پیشرفته در فکت‌چک‌ها
        
        Args:
            keyword: کلمه کلیدی برای جستجو در محتوا
            category_id: شناسه دسته‌بندی
            status: وضعیت فکت‌چک
            result_type: نوع نتیجه
            start_date: تاریخ شروع
            end_date: تاریخ پایان
            tags: لیست تگ‌ها
            limit: تعداد نتایج
            offset: تعداد رد شده از ابتدا
            
        Returns:
            لیست فکت‌چک‌های یافت شده
        """
        try:
            conditions = []
            
            if keyword:
                conditions.append(
                    or_(
                        FactCheck.content.ilike(f"%{keyword}%"),
                        FactCheck.summary.ilike(f"%{keyword}%")
                    )
                )
                
            if category_id:
                conditions.append(FactCheck.category_id == category_id)
                
            if status:
                conditions.append(FactCheck.status == status)
                
            if result_type:
                conditions.append(FactCheck.result == result_type)
                
            if start_date:
                conditions.append(FactCheck.created_at >= start_date)
                
            if end_date:
                conditions.append(FactCheck.created_at <= end_date)
            
            query = (
                select(FactCheck)
                .options(
                    joinedload(FactCheck.category),
                    joinedload(FactCheck.tags)
                )
            )
            
            if tags:
                query = (
                    query.join(FactCheck.tags)
                    .where(Tag.name.in_(tags))
                )
            
            if conditions:
                query = query.where(and_(*conditions))
            
            query = (
                query
                .order_by(desc(FactCheck.created_at))
                .limit(limit)
                .offset(offset)
            )
            
            result = await self.session.execute(query)
            return result.scalars().unique().all()
        except Exception as e:
            logger.error(f"Error searching fact checks: {str(e)}")
            return []

    async def get_similar(
        self,
        content: str,
        limit: int = 5
    ) -> List[FactCheck]:
        """
        یافتن فکت‌چک‌های مشابه بر اساس محتوا
        
        Args:
            content: محتوای مورد نظر
            limit: تعداد نتایج
            
        Returns:
            لیست فکت‌چک‌های مشابه
        """
        try:
            # TODO: پیاده‌سازی الگوریتم جستجوی متن مشابه
            # می‌توان از روش‌هایی مانند TF-IDF یا embedding استفاده کرد
            return []
        except Exception as e:
            logger.error(f"Error finding similar fact checks: {str(e)}")
            return []

    async def get_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, any]:
        """
        دریافت آمار فکت‌چک‌ها
        
        Args:
            start_date: تاریخ شروع
            end_date: تاریخ پایان
            
        Returns:
            دیکشنری حاوی آمار مختلف
        """
        try:
            conditions = []
            if start_date:
                conditions.append(FactCheck.created_at >= start_date)
            if end_date:
                conditions.append(FactCheck.created_at <= end_date)

            # آمار کلی
            base_query = select(FactCheck)
            if conditions:
                base_query = base_query.where(and_(*conditions))

            # تعداد کل
            total_count = await self.session.execute(
                select(func.count()).select_from(base_query.subquery())
            )
            total = total_count.scalar_one()

            # آمار بر اساس نتیجه
            result_stats = await self.session.execute(
                select(
                    FactCheck.result,
                    func.count(FactCheck.id).label('count')
                )
                .where(and_(*conditions) if conditions else True)
                .group_by(FactCheck.result)
            )
            results_by_type = {
                str(row.result): row.count 
                for row in result_stats
            }

            # آمار بر اساس دسته‌بندی
            category_stats = await self.session.execute(
                select(
                    Category.name,
                    func.count(FactCheck.id).label('count')
                )
                .join(FactCheck.category)
                .where(and_(*conditions) if conditions else True)
                .group_by(Category.name)
            )
            results_by_category = {
                row.name: row.count 
                for row in category_stats
            }

            # میانگین امتیاز اطمینان
            avg_confidence = await self.session.execute(
                select(func.avg(FactCheck.confidence_score))
                .where(and_(*conditions) if conditions else True)
            )
            average_confidence = avg_confidence.scalar_one() or 0.0

            return {
                "total": total,
                "by_result": results_by_type,
                "by_category": results_by_category,
                "average_confidence": average_confidence
            }
        except Exception as e:
            logger.error(f"Error getting fact check statistics: {str(e)}")
            return {
                "total": 0,
                "by_result": {},
                "by_category": {},
                "average_confidence": 0.0
            }

    async def update_status(
        self,
        id: int,
        status: FactCheckStatus,
        result: Optional[FactCheckResult] = None,
        confidence_score: Optional[float] = None
    ) -> Optional[FactCheck]:
        """
        به‌روزرسانی وضعیت و نتیجه یک فکت‌چک
        
        Args:
            id: شناسه فکت‌چک
            status: وضعیت جدید
            result: نتیجه جدید (اختیاری)
            confidence_score: امتیاز اطمینان جدید (اختیاری)
            
        Returns:
            فکت‌چک به‌روز شده یا None در صورت خطا
        """
        try:
            update_data = {"status": status}
            if result is not None:
                update_data["result"] = result
            if confidence_score is not None:
                update_data["confidence_score"] = confidence_score
                
            return await self.update(id, **update_data)
        except Exception as e:
            logger.error(f"Error updating fact check status: {str(e)}")
            return None

    async def get_pending_count(self) -> int:
        """
        دریافت تعداد فکت‌چک‌های در انتظار بررسی
        
        Returns:
            تعداد فکت‌چک‌های در وضعیت انتظار
        """
        try:
            result = await self.session.execute(
                select(func.count())
                .select_from(FactCheck)
                .where(FactCheck.status == FactCheckStatus.PENDING)
            )
            return result.scalar_one() or 0
        except Exception as e:
            logger.error(f"Error getting pending fact check count: {str(e)}")
            return 0

    async def delete_old_unfinished(self, days: int = 30) -> int:
        """
        حذف فکت‌چک‌های قدیمی که تکمیل نشده‌اند
        
        Args:
            days: تعداد روزهای قبل برای حذف
            
        Returns:
            تعداد رکوردهای حذف شده
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            result = await self.session.execute(
                select(FactCheck)
                .where(and_(
                    FactCheck.created_at < cutoff_date,
                    FactCheck.status.in_([
                        FactCheckStatus.PENDING,
                        FactCheckStatus.PROCESSING
                    ])
                ))
            )
            old_checks = result.scalars().all()
            
            for check in old_checks:
                await self.session.delete(check)
            
            await self.session.commit()
            return len(old_checks)
        except Exception as e:
            logger.error(f"Error deleting old unfinished fact checks: {str(e)}")
            await self.session.rollback()
            return 0
