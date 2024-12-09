"""
ریپازیتوری مخصوص عملیات مربوط به دسته‌بندی‌های فکت‌چک.
این ماژول امکان مدیریت ساختار درختی دسته‌بندی‌ها و روابط بین آنها را فراهم می‌کند.
"""

from typing import List, Optional, Dict
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload, selectinload

from ..models import Category, FactCheck
from .base_repository import BaseRepository
from ...utils.helpers import get_logger

logger = get_logger(__name__)

class CategoryRepository(BaseRepository[Category]):
    """
    ریپازیتوری برای مدیریت دسته‌بندی‌های فکت‌چک.
    این کلاس امکان ایجاد، ویرایش و مدیریت ساختار درختی دسته‌بندی‌ها را فراهم می‌کند
    و قابلیت‌های مهمی مانند یافتن زیردسته‌ها، والدین و آمارگیری را ارائه می‌دهد.
    """

    def __init__(self, session: AsyncSession):
        """
        مقداردهی اولیه ریپازیتوری دسته‌بندی
        
        Args:
            session: نشست فعال دیتابیس
        """
        super().__init__(Category, session)

    async def get_by_name(self, name: str) -> Optional[Category]:
        """
        دریافت دسته‌بندی با نام مشخص
        
        Args:
            name: نام دسته‌بندی
            
        Returns:
            دسته‌بندی یافت شده یا None
        """
        try:
            query = select(Category).where(Category.name == name)
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting category by name: {str(e)}")
            return None

    async def get_root_categories(self) -> List[Category]:
        """
        دریافت دسته‌بندی‌های ریشه (بدون والد)
        
        Returns:
            لیست دسته‌بندی‌های ریشه
        """
        try:
            query = (
                select(Category)
                .where(Category.parent_id.is_(None))
                .options(selectinload(Category.children))
            )
            result = await self.session.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting root categories: {str(e)}")
            return []

    async def get_children(self, category_id: int) -> List[Category]:
        """
        دریافت زیردسته‌های مستقیم یک دسته‌بندی
        
        Args:
            category_id: شناسه دسته‌بندی والد
            
        Returns:
            لیست زیردسته‌ها
        """
        try:
            query = (
                select(Category)
                .where(Category.parent_id == category_id)
                .options(selectinload(Category.children))
            )
            result = await self.session.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting category children: {str(e)}")
            return []

    async def get_all_descendants(self, category_id: int) -> List[Category]:
        """
        دریافت تمام زیردسته‌های یک دسته‌بندی (به صورت بازگشتی)
        
        Args:
            category_id: شناسه دسته‌بندی والد
            
        Returns:
            لیست تمام زیردسته‌ها
        """
        try:
            descendants = []
            direct_children = await self.get_children(category_id)
            
            for child in direct_children:
                descendants.append(child)
                child_descendants = await self.get_all_descendants(child.id)
                descendants.extend(child_descendants)
            
            return descendants
        except SQLAlchemyError as e:
            logger.error(f"Error getting all descendants: {str(e)}")
            return []

    async def get_ancestry_path(self, category_id: int) -> List[Category]:
        """
        دریافت مسیر کامل از ریشه تا دسته‌بندی مورد نظر
        
        Args:
            category_id: شناسه دسته‌بندی
            
        Returns:
            لیست دسته‌بندی‌ها از ریشه تا هدف
        """
        try:
            path = []
            current = await self.get_by_id(category_id)
            
            while current:
                path.insert(0, current)
                if current.parent_id:
                    current = await self.get_by_id(current.parent_id)
                else:
                    break
            
            return path
        except SQLAlchemyError as e:
            logger.error(f"Error getting ancestry path: {str(e)}")
            return []

    async def move_category(
        self,
        category_id: int,
        new_parent_id: Optional[int]
    ) -> bool:
        """
        جابجایی یک دسته‌بندی به والد جدید
        
        Args:
            category_id: شناسه دسته‌بندی
            new_parent_id: شناسه والد جدید (None برای تبدیل به ریشه)
            
        Returns:
            True در صورت موفقیت، False در صورت خطا
        """
        try:
            # بررسی اعتبار عملیات جابجایی
            if category_id == new_parent_id:
                logger.error("Cannot move category to itself")
                return False
            
            if new_parent_id:
                new_parent = await self.get_by_id(new_parent_id)
                if not new_parent:
                    logger.error("New parent category not found")
                    return False
                    
                # بررسی حلقه در ساختار درختی
                ancestors = await self.get_ancestry_path(new_parent_id)
                if any(a.id == category_id for a in ancestors):
                    logger.error("Moving would create a cycle in the hierarchy")
                    return False
            
            # انجام جابجایی
            category = await self.get_by_id(category_id)
            if category:
                return bool(await self.update(category_id, parent_id=new_parent_id))
            return False
        except SQLAlchemyError as e:
            logger.error(f"Error moving category: {str(e)}")
            return False

    async def get_category_statistics(self, category_id: int) -> Dict:
        """
        دریافت آمار یک دسته‌بندی
        
        Args:
            category_id: شناسه دسته‌بندی
            
        Returns:
            دیکشنری حاوی آمار
        """
        try:
            category = await self.get_by_id(category_id)
            if not category:
                return {}

            # دریافت تمام زیردسته‌ها
            descendants = await self.get_all_descendants(category_id)
            descendant_ids = [d.id for d in descendants] + [category_id]

            # آمار فکت‌چک‌ها
            factcheck_count = await self.session.execute(
                select(func.count(FactCheck.id))
                .where(FactCheck.category_id.in_(descendant_ids))
            )
            
            # توزیع نتایج فکت‌چک‌ها
            result_distribution = await self.session.execute(
                select(
                    FactCheck.result,
                    func.count(FactCheck.id).label('count')
                )
                .where(FactCheck.category_id.in_(descendant_ids))
                .group_by(FactCheck.result)
            )

            # میانگین امتیاز اطمینان
            avg_confidence = await self.session.execute(
                select(func.avg(FactCheck.confidence_score))
                .where(FactCheck.category_id.in_(descendant_ids))
            )

            return {
                "category_name": category.name,
                "total_factchecks": factcheck_count.scalar_one() or 0,
                "subcategories_count": len(descendants),
                "result_distribution": {
                    str(row.result): row.count 
                    for row in result_distribution
                },
                "average_confidence": float(avg_confidence.scalar_one() or 0),
                "direct_children": len(await self.get_children(category_id))
            }
        except SQLAlchemyError as e:
            logger.error(f"Error getting category statistics: {str(e)}")
            return {}

    async def merge_categories(
        self,
        source_id: int,
        target_id: int
    ) -> bool:
        """
        ادغام دو دسته‌بندی
        
        Args:
            source_id: شناسه دسته‌بندی مبدا
            target_id: شناسه دسته‌بندی مقصد
            
        Returns:
            True در صورت موفقیت، False در صورت خطا
        """
        try:
            source = await self.get_by_id(source_id)
            target = await self.get_by_id(target_id)
            
            if not source or not target:
                return False

            # انتقال فکت‌چک‌ها
            await self.session.execute(
                update(FactCheck)
                .where(FactCheck.category_id == source_id)
                .values(category_id=target_id)
            )

            # انتقال زیردسته‌ها
            await self.session.execute(
                update(Category)
                .where(Category.parent_id == source_id)
                .values(parent_id=target_id)
            )

            # حذف دسته‌بندی مبدا
            await self.delete(source_id)
            await self.session.commit()
            
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error merging categories: {str(e)}")
            await self.session.rollback()
            return False

    async def reorder_categories(
        self,
        parent_id: Optional[int],
        order: List[int]
    ) -> bool:
        """
        تغییر ترتیب دسته‌بندی‌ها
        
        Args:
            parent_id: شناسه والد (None برای دسته‌بندی‌های ریشه)
            order: لیست شناسه‌ها به ترتیب جدید
            
        Returns:
            True در صورت موفقیت، False در صورت خطا
        """
        try:
            # TODO: پیاده‌سازی سیستم ترتیب‌بندی
            # می‌توان از یک فیلد position استفاده کرد
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error reordering categories: {str(e)}")
            return False

    async def search_categories(
        self,
        keyword: str,
        include_children: bool = True
    ) -> List[Category]:
        """
        جستجو در دسته‌بندی‌ها
        
        Args:
            keyword: کلمه کلیدی
            include_children: شامل کردن زیردسته‌ها
            
        Returns:
            لیست دسته‌بندی‌های یافت شده
        """
        try:
            query = (
                select(Category)
                .where(
                    or_(
                        Category.name.ilike(f"%{keyword}%"),
                        Category.description.ilike(f"%{keyword}%")
                    )
                )
            )
            
            if include_children:
                query = query.options(selectinload(Category.children))
                
            result = await self.session.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Error searching categories: {str(e)}")
            return []

    async def validate_hierarchy(self) -> List[str]:
        """
        اعتبارسنجی ساختار سلسله مراتبی دسته‌بندی‌ها
        
        Returns:
            لیست خطاهای یافت شده
        """
        try:
            errors = []
            categories = await self.get_all()
            
            for category in categories:
                if category.parent_id:
                    # بررسی وجود والد
                    parent = await self.get_by_id(category.parent_id)
                    if not parent:
                        errors.append(
                            f"Category {category.name} references non-existent parent {category.parent_id}"
                        )
                    
                    # بررسی حلقه
                    ancestors = await self.get_ancestry_path(category.id)
                    seen = set()
                    for ancestor in ancestors:
                        if ancestor.id in seen:
                            errors.append(
                                f"Cycle detected in hierarchy involving category {category.name}"
                            )
                            break
                        seen.add(ancestor.id)
            
            return errors
        except SQLAlchemyError as e:
            logger.error(f"Error validating category hierarchy: {str(e)}")
            return [str(e)]
