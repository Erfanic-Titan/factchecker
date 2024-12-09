"""
ریپازیتوری مخصوص عملیات مربوط به فایل‌های چندرسانه‌ای.
این ماژول مسئول مدیریت و پردازش انواع فایل‌های مرتبط با فکت‌چک‌ها است،
از جمله تصاویر، ویدیوها، فایل‌های صوتی و اسناد.
"""

import os
from typing import List, Optional, Dict, BinaryIO
from datetime import datetime
import hashlib
import magic
import aiofiles
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
import json

from ..models import Media, MediaType, FactCheck
from .base_repository import BaseRepository
from ...utils.helpers import get_logger
from ...config.config import MEDIA_DIR

logger = get_logger(__name__)

class MediaRepository(BaseRepository[Media]):
    """
    ریپازیتوری برای مدیریت فایل‌های چندرسانه‌ای.
    این کلاس عملیات پیشرفته برای ذخیره‌سازی، پردازش و مدیریت فایل‌های مختلف را
    پیاده‌سازی می‌کند و با سیستم فایل و تلگرام در تعامل است.
    """

    def __init__(self, session: AsyncSession):
        """
        مقداردهی اولیه ریپازیتوری رسانه
        
        Args:
            session: نشست فعال دیتابیس
        """
        super().__init__(Media, session)
        self.ALLOWED_EXTENSIONS = {
            'image': {'jpg', 'jpeg', 'png', 'gif', 'webp'},
            'video': {'mp4', 'avi', 'mov', 'mkv'},
            'audio': {'mp3', 'wav', 'ogg', 'm4a'},
            'document': {'pdf', 'doc', 'docx', 'txt'}
        }
        self.MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 مگابایت

    async def save_file(
        self,
        file: BinaryIO,
        filename: str,
        media_type: MediaType,
        factcheck_id: int,
        telegram_file_id: Optional[str] = None,
        caption: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Optional[Media]:
        """
        ذخیره فایل جدید
        
        Args:
            file: شیء فایل
            filename: نام فایل
            media_type: نوع رسانه
            factcheck_id: شناسه فکت‌چک مرتبط
            telegram_file_id: شناسه فایل در تلگرام (اختیاری)
            caption: توضیحات فایل (اختیاری)
            metadata: اطلاعات اضافی (اختیاری)
            
        Returns:
            رسانه ذخیره شده یا None در صورت خطا
        """
        try:
            # بررسی پسوند فایل
            ext = filename.rsplit('.', 1)[-1].lower()
            if not self._is_allowed_file(ext, media_type):
                logger.error(f"File extension {ext} not allowed for {media_type}")
                return None

            # بررسی سایز فایل
            file.seek(0, 2)  # رفتن به انتهای فایل
            size = file.tell()
            file.seek(0)  # برگشت به ابتدای فایل
            
            if size > self.MAX_FILE_SIZE:
                logger.error(f"File size {size} exceeds maximum allowed size")
                return None

            # ایجاد نام یکتا برای فایل
            file_hash = hashlib.md5(file.read()).hexdigest()
            file.seek(0)
            unique_filename = f"{file_hash}_{datetime.utcnow().timestamp()}.{ext}"
            
            # ایجاد مسیر ذخیره‌سازی
            save_path = os.path.join(MEDIA_DIR, media_type.value, unique_filename)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            # ذخیره فایل
            async with aiofiles.open(save_path, 'wb') as f:
                contents = file.read()
                await f.write(contents)

            # تشخیص نوع MIME
            mime_type = magic.from_buffer(contents, mime=True)

            # ذخیره متادیتا
            full_metadata = {
                'original_filename': filename,
                'size': size,
                'mime_type': mime_type,
                'hash': file_hash
            }
            if metadata:
                full_metadata.update(metadata)

            # ایجاد رکورد در دیتابیس
            media = await self.create(
                factcheck_id=factcheck_id,
                type=media_type,
                file_id=telegram_file_id,
                file_path=save_path,
                caption=caption,
                metadata=json.dumps(full_metadata)
            )

            return media

        except Exception as e:
            logger.error(f"Error saving media file: {str(e)}")
            return None

    def _is_allowed_file(self, extension: str, media_type: MediaType) -> bool:
        """
        بررسی مجاز بودن پسوند فایل
        
        Args:
            extension: پسوند فایل
            media_type: نوع رسانه
            
        Returns:
            True اگر مجاز باشد، False در غیر این صورت
        """
        return extension in self.ALLOWED_EXTENSIONS.get(media_type.value, set())

    async def get_by_telegram_id(self, file_id: str) -> Optional[Media]:
        """
        دریافت رسانه با شناسه تلگرام
        
        Args:
            file_id: شناسه فایل در تلگرام
            
        Returns:
            رسانه یافت شده یا None
        """
        try:
            query = select(Media).where(Media.file_id == file_id)
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting media by telegram ID: {str(e)}")
            return None

    async def get_by_hash(self, file_hash: str) -> Optional[Media]:
        """
        دریافت رسانه با هش فایل
        
        Args:
            file_hash: هش MD5 فایل
            
        Returns:
            رسانه یافت شده یا None
        """
        try:
            query = (
                select(Media)
                .where(Media.metadata.like(f'%"hash": "{file_hash}"%'))
            )
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting media by hash: {str(e)}")
            return None

    async def get_factcheck_media(
        self,
        factcheck_id: int,
        media_type: Optional[MediaType] = None
    ) -> List[Media]:
        """
        دریافت تمام رسانه‌های مرتبط با یک فکت‌چک
        
        Args:
            factcheck_id: شناسه فکت‌چک
            media_type: نوع رسانه برای فیلتر (اختیاری)
            
        Returns:
            لیست رسانه‌های مرتبط
        """
        try:
            query = select(Media).where(Media.factcheck_id == factcheck_id)
            if media_type:
                query = query.where(Media.type == media_type)
            
            result = await self.session.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting fact check media: {str(e)}")
            return []

    async def delete_file(self, media_id: int) -> bool:
        """
        حذف فایل رسانه و رکورد مربوطه
        
        Args:
            media_id: شناسه رسانه
            
        Returns:
            True در صورت موفقیت، False در صورت خطا
        """
        try:
            media = await self.get_by_id(media_id)
            if not media:
                return False

            # حذف فایل فیزیکی
            if media.file_path and os.path.exists(media.file_path):
                os.remove(media.file_path)

            # حذف رکورد از دیتابیس
            return await self.delete(media_id)
        except Exception as e:
            logger.error(f"Error deleting media file: {str(e)}")
            return False

    async def update_metadata(
        self,
        media_id: int,
        metadata_updates: Dict
    ) -> Optional[Media]:
        """
        به‌روزرسانی متادیتای رسانه
        
        Args:
            media_id: شناسه رسانه
            metadata_updates: دیکشنری تغییرات متادیتا
            
        Returns:
            رسانه به‌روز شده یا None در صورت خطا
        """
        try:
            media = await self.get_by_id(media_id)
            if not media:
                return None

            current_metadata = json.loads(media.metadata or '{}')
            current_metadata.update(metadata_updates)

            return await self.update(
                media_id,
                metadata=json.dumps(current_metadata)
            )
        except Exception as e:
            logger.error(f"Error updating media metadata: {str(e)}")
            return None

    async def bulk_delete_files(self, media_ids: List[int]) -> int:
        """
        حذف گروهی فایل‌های رسانه
        
        Args:
            media_ids: لیست شناسه‌های رسانه
            
        Returns:
            تعداد فایل‌های حذف شده
        """
        try:
            deleted_count = 0
            for media_id in media_ids:
                if await self.delete_file(media_id):
                    deleted_count += 1
            return deleted_count
        except Exception as e:
            logger.error(f"Error bulk deleting media files: {str(e)}")
            return 0

    async def get_media_statistics(self) -> Dict[str, int]:
        """
        دریافت آمار استفاده از رسانه‌ها
        
        Returns:
            دیکشنری حاوی آمار به تفکیک نوع رسانه
        """
        try:
            stats = {}
            for media_type in MediaType:
                count = await self.session.execute(
                    select(func.count())
                    .select_from(Media)
                    .where(Media.type == media_type)
                )
                stats[media_type.value] = count.scalar_one() or 0
                
            # محاسبه حجم کل
            total_size = 0
            all_media = await self.get_all()
            for media in all_media:
                metadata = json.loads(media.metadata or '{}')
                total_size += metadata.get('size', 0)
                
            stats['total_size_bytes'] = total_size
            stats['total_count'] = sum(
                count for type_, count in stats.items()
                if type_ != 'total_size_bytes'
            )
            
            return stats
        except SQLAlchemyError as e:
            logger.error(f"Error getting media statistics: {str(e)}")
            return {}

    async def get_duplicate_files(self) -> List[List[Media]]:
        """
        یافتن فایل‌های تکراری بر اساس هش
        
        Returns:
            لیست گروه‌های فایل‌های تکراری
        """
        try:
            all_media = await self.get_all()
            hash_groups = {}
            
            for media in all_media:
                metadata = json.loads(media.metadata or '{}')
                file_hash = metadata.get('hash')
                if file_hash:
                    if file_hash not in hash_groups:
                        hash_groups[file_hash] = []
                    hash_groups[file_hash].append(media)
            
            return [
                group for group in hash_groups.values()
                if len(group) > 1
            ]
        except SQLAlchemyError as e:
            logger.error(f"Error finding duplicate files: {str(e)}")
            return []

    async def cleanup_orphaned_files(self) -> int:
        """
        پاکسازی فایل‌های بدون ارجاع در دیتابیس
        
        Returns:
            تعداد فایل‌های پاکسازی شده
        """
        try:
            cleaned_count = 0
            all_media = await self.get_all()
            
            for media in all_media:
                # بررسی وجود فکت‌چک مرتبط
                factcheck = await self.session.get(FactCheck, media.factcheck_id)
                if not factcheck:
                    if await self.delete_file(media.id):
                        cleaned_count += 1
                    continue
                
                # بررسی وجود فایل فیزیکی
                if media.file_path and not os.path.exists(media.file_path):
                    await self.delete(media.id)
                    cleaned_count += 1
            
            return cleaned_count
        except SQLAlchemyError as e:
            logger.error(f"Error cleaning up orphaned files: {str(e)}")
            return 0
