"""
ریپازیتوری مخصوص عملیات مربوط به کاربران
"""

from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, update, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from ..models import User, FactCheck
from .base_repository import BaseRepository
from ...utils.helpers import get_logger

logger = get_logger(__name__)

class UserRepository(BaseRepository[User]):
    """
    ریپازیتوری برای مدیریت عملیات مربوط به کاربران.
    این کلاس عملیات تخصصی مربوط به کاربران تلگرام را پیاده‌سازی می‌کند.
    """

    def __init__(self, session: AsyncSession):
        """
        مقداردهی اولیه ریپازیتوری کاربر
        
        Args:
            session: نشست فعال دیتابیس
        """
        super().__init__(User, session)

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """
        دریافت کاربر با شناسه تلگرام
        
        Args:
            telegram_id: شناسه کاربر در تلگرام
            
        Returns:
            کاربر یافت شده یا None
        """
        try:
            query = select(User).where(User.telegram_id == telegram_id)
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting user by telegram ID: {str(e)}")
            return None

    async def create_or_update(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: Optional[str] = None
    ) -> Optional[User]:
        """
        ایجاد یا به‌روزرسانی کاربر بر اساس اطلاعات تلگرام
        
        Args:
            telegram_id: شناسه کاربر در تلگرام
            username: نام کاربری (اختیاری)
            first_name: نام (اختیاری)
            last_name: نام خانوادگی (اختیاری)
            language_code: کد زبان (اختیاری)
            
        Returns:
            کاربر ایجاد یا به‌روز شده یا None در صورت خطا
        """
        try:
            user = await self.get_by_telegram_id(telegram_id)
            
            if user:
                # به‌روزرسانی کاربر موجود
                update_data = {
                    "last_activity": datetime.utcnow(),
                    "username": username or user.username,
                    "first_name": first_name or user.first_name,
                    "last_name": last_name or user.last_name,
                    "language_code": language_code or user.language_code
                }
                return await self.update(user.id, **update_data)
            else:
                # ایجاد کاربر جدید
                return await self.create(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    language_code=language_code,
                    is_premium=False,
                    is_blocked=False
                )
        except SQLAlchemyError as e:
            logger.error(f"Error creating/updating user: {str(e)}")
            return None

    async def update_activity(self, telegram_id: int) -> bool:
        """
        به‌روزرسانی زمان آخرین فعالیت کاربر
        
        Args:
            telegram_id: شناسه کاربر در تلگرام
            
        Returns:
            True در صورت موفقیت، False در صورت خطا
        """
        try:
            query = (
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(last_activity=datetime.utcnow())
            )
            await self.session.execute(query)
            await self.session.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error updating user activity: {str(e)}")
            await self.session.rollback()
            return False

    async def block_user(self, telegram_id: int) -> bool:
        """
        مسدود کردن کاربر
        
        Args:
            telegram_id: شناسه کاربر در تلگرام
            
        Returns:
            True در صورت موفقیت، False در صورت خطا
        """
        try:
            query = (
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(is_blocked=True)
            )
            await self.session.execute(query)
            await self.session.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error blocking user: {str(e)}")
            await self.session.rollback()
            return False

    async def unblock_user(self, telegram_id: int) -> bool:
        """
        رفع مسدودیت کاربر
        
        Args:
            telegram_id: شناسه کاربر در تلگرام
            
        Returns:
            True در صورت موفقیت، False در صورت خطا
        """
        try:
            query = (
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(is_blocked=False)
            )
            await self.session.execute(query)
            await self.session.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error unblocking user: {str(e)}")
            await self.session.rollback()
            return False

    async def set_premium_status(self, telegram_id: int, is_premium: bool) -> bool:
        """
        تنظیم وضعیت پریمیم کاربر
        
        Args:
            telegram_id: شناسه کاربر در تلگرام
            is_premium: وضعیت پریمیم
            
        Returns:
            True در صورت موفقیت، False در صورت خطا
        """
        try:
            query = (
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(is_premium=is_premium)
            )
            await self.session.execute(query)
            await self.session.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error setting premium status: {str(e)}")
            await self.session.rollback()
            return False

    async def get_user_statistics(self, telegram_id: int) -> dict:
        """
        دریافت آمار فعالیت‌های کاربر
        
        Args:
            telegram_id: شناسه کاربر در تلگرام
            
        Returns:
            دیکشنری حاوی آمار کاربر
        """
        try:
            user = await self.get_by_telegram_id(telegram_id)
            if not user:
                return {}
                
            # تعداد کل فکت‌چک‌ها
            total_checks = await self.session.execute(
                select(func.count(FactCheck.id))
                .where(FactCheck.user_id == user.id)
            )
            
            # تعداد فکت‌چک‌ها بر اساس نتیجه
            result_stats = await self.session.execute(
                select(
                    FactCheck.result,
                    func.count(FactCheck.id).label('count')
                )
                .where(FactCheck.user_id == user.id)
                .group_by(FactCheck.result)
            )
            
            # میانگین امتیاز اطمینان
            avg_confidence = await self.session.execute(
                select(func.avg(FactCheck.confidence_score))
                .where(FactCheck.user_id == user.id)
            )
            
            return {
                "total_checks": total_checks.scalar_one() or 0,
                "results_breakdown": {
                    str(row.result): row.count 
                    for row in result_stats
                },
                "average_confidence": float(avg_confidence.scalar_one() or 0),
                "member_since": user.created_at,
                "last_activity": user.last_activity,
                "is_premium": user.is_premium
            }
        except SQLAlchemyError as e:
            logger.error(f"Error getting user statistics: {str(e)}")
            return {}

    async def get_inactive_users(self, days: int = 30) -> List[User]:
        """
        دریافت لیست کاربران غیرفعال
        
        Args:
            days: تعداد روزهای عدم فعالیت
            
        Returns:
            لیست کاربران غیرفعال
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            query = (
                select(User)
                .where(User.last_activity < cutoff_date)
            )
            result = await self.session.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting inactive users: {str(e)}")
            return []

    async def get_premium_users(self) -> List[User]:
        """
        دریافت لیست کاربران پریمیم
        
        Returns:
            لیست کاربران پریمیم
        """
        try:
            query = select(User).where(User.is_premium == True)
            result = await self.session.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting premium users: {str(e)}")
            return []

    async def cleanup_inactive_users(self, days: int = 90) -> int:
        """
        حذف کاربران غیرفعال
        
        Args:
            days: تعداد روزهای عدم فعالیت
            
        Returns:
            تعداد کاربران حذف شده
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            inactive_users = await self.get_inactive_users(days)
            
            for user in inactive_users:
                await self.session.delete(user)
            
            await self.session.commit()
            return len(inactive_users)
        except SQLAlchemyError as e:
            logger.error(f"Error cleaning up inactive users: {str(e)}")
            await self.session.rollback()
            return 0
