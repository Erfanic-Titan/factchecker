"""
کلاس پایه برای تمام ریپازیتوری‌ها که عملیات مشترک را پیاده‌سازی می‌کند
"""

from typing import Generic, List, Optional, Type, TypeVar
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from ..models import Base
from ...utils.helpers import get_logger

logger = get_logger(__name__)

# تعریف نوع ژنریک برای مدل
ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    """
    کلاس پایه برای ریپازیتوری‌ها که عملیات CRUD اصلی را پیاده‌سازی می‌کند.
    این کلاس به صورت ژنریک طراحی شده و می‌تواند با هر مدلی کار کند.
    """

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        """
        مقداردهی اولیه ریپازیتوری
        
        Args:
            model: کلاس مدل SQLAlchemy
            session: نشست فعال دیتابیس
        """
        self.model = model
        self.session = session

    async def create(self, **kwargs) -> Optional[ModelType]:
        """
        ایجاد یک نمونه جدید از مدل
        
        Args:
            **kwargs: پارامترهای مدل
            
        Returns:
            نمونه ایجاد شده یا None در صورت خطا
        """
        try:
            instance = self.model(**kwargs)
            self.session.add(instance)
            await self.session.commit()
            await self.session.refresh(instance)
            return instance
        except SQLAlchemyError as e:
            logger.error(f"Error creating {self.model.__name__}: {str(e)}")
            await self.session.rollback()
            return None

    async def get_by_id(self, id: int) -> Optional[ModelType]:
        """
        دریافت نمونه با شناسه مشخص
        
        Args:
            id: شناسه مورد نظر
            
        Returns:
            نمونه یافت شده یا None
        """
        try:
            query = select(self.model).where(self.model.id == id)
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting {self.model.__name__} by id: {str(e)}")
            return None

    async def get_all(self) -> List[ModelType]:
        """
        دریافت تمام نمونه‌های موجود
        
        Returns:
            لیست نمونه‌ها
        """
        try:
            query = select(self.model)
            result = await self.session.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting all {self.model.__name__}s: {str(e)}")
            return []

    async def update(self, id: int, **kwargs) -> Optional[ModelType]:
        """
        به‌روزرسانی نمونه با شناسه مشخص
        
        Args:
            id: شناسه مورد نظر
            **kwargs: پارامترهای جدید
            
        Returns:
            نمونه به‌روز شده یا None در صورت خطا
        """
        try:
            instance = await self.get_by_id(id)
            if instance:
                for key, value in kwargs.items():
                    if hasattr(instance, key):
                        setattr(instance, key, value)
                await self.session.commit()
                await self.session.refresh(instance)
                return instance
            return None
        except SQLAlchemyError as e:
            logger.error(f"Error updating {self.model.__name__}: {str(e)}")
            await self.session.rollback()
            return None

    async def delete(self, id: int) -> bool:
        """
        حذف نمونه با شناسه مشخص
        
        Args:
            id: شناسه مورد نظر
            
        Returns:
            True در صورت موفقیت، False در صورت خطا
        """
        try:
            instance = await self.get_by_id(id)
            if instance:
                await self.session.delete(instance)
                await self.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            logger.error(f"Error deleting {self.model.__name__}: {str(e)}")
            await self.session.rollback()
            return False

    async def exists(self, id: int) -> bool:
        """
        بررسی وجود نمونه با شناسه مشخص
        
        Args:
            id: شناسه مورد نظر
            
        Returns:
            True اگر موجود باشد، False در غیر این صورت
        """
        try:
            result = await self.get_by_id(id)
            return result is not None
        except SQLAlchemyError as e:
            logger.error(f"Error checking existence of {self.model.__name__}: {str(e)}")
            return False

    async def count(self) -> int:
        """
        شمارش تعداد کل نمونه‌ها
        
        Returns:
            تعداد نمونه‌ها
        """
        try:
            query = select(self.model)
            result = await self.session.execute(query)
            return len(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error counting {self.model.__name__}s: {str(e)}")
            return 0
