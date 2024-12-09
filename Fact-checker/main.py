"""
نقطه ورود اصلی برنامه ربات راستی‌آزمایی.

این ماژول مسئول راه‌اندازی و مدیریت تمام اجزای برنامه است، شامل:
- راه‌اندازی و پیکربندی ربات تلگرام
- اتصال به پایگاه داده و ایجاد جداول مورد نیاز
- راه‌اندازی سرویس‌های مختلف تشخیص و تحلیل
- مدیریت چرخه حیات برنامه و منابع
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

import telegram
from telegram.ext import ApplicationBuilder, ContextTypes
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from redis import Redis

# واردسازی سرویس‌ها و هندلرها
from src.core.services.nlp_service import NLPService
from src.core.services.speech_service import SpeechService
from src.core.services.translation_service import TranslationService
from src.core.services.video_analysis_service import VideoAnalysisService
from src.core.services.image_analysis_service import ImageAnalysisService
from src.core.services.credibility_service import CredibilityService
from src.core.services.fake_news_detector import FakeNewsDetector
from src.core.services.google_factcheck_service import GoogleFactCheckService

from src.bot.handlers.message_handlers import MessageHandlers, register_message_handlers
from src.bot.handlers.command_handlers import register_command_handlers
from src.bot.handlers.callback_handlers import register_callback_handlers

from src.data.models.models import Base
from src.data.repositories.fact_repository import FactRepository

from config.config import (
    TELEGRAM_TOKEN, DATABASE_URL, REDIS_URL,
    LOGGING_CONFIG, ADMIN_USER_IDS
)

# تنظیم لاگر
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

class FactCheckerBot:
    """کلاس اصلی برای مدیریت ربات راستی‌آزمایی."""
    
    def __init__(self):
        """مقداردهی اولیه کلاس ربات."""
        self.services = {}
        self.repositories = {}
        self.db_engine = None
        self.db_session = None
        self.redis_client = None
        self.telegram_app = None

    async def initialize(self):
        """
        راه‌اندازی و پیکربندی اولیه تمام اجزای برنامه.
        این متد همه سرویس‌ها را به ترتیب صحیح راه‌اندازی می‌کند.
        """
        try:
            logger.info("شروع راه‌اندازی ربات راستی‌آزمایی...")
            
            # راه‌اندازی پایگاه داده
            await self._setup_database()
            
            # راه‌اندازی Redis
            await self._setup_redis()
            
            # راه‌اندازی سرویس‌ها
            await self._setup_services()
            
            # راه‌اندازی ربات تلگرام
            await self._setup_telegram()
            
            logger.info("راه‌اندازی ربات با موفقیت انجام شد.")
            
        except Exception as e:
            logger.error(f"خطا در راه‌اندازی ربات: {str(e)}")
            raise

    async def _setup_database(self):
        """راه‌اندازی و پیکربندی پایگاه داده."""
        try:
            logger.info("راه‌اندازی اتصال به پایگاه داده...")
            
            # ایجاد موتور پایگاه داده
            self.db_engine = create_engine(
                DATABASE_URL,
                pool_size=20,
                max_overflow=10
            )
            
            # ایجاد جداول
            Base.metadata.create_all(self.db_engine)
            
            # ایجاد کلاس Session
            Session = sessionmaker(bind=self.db_engine)
            self.db_session = Session()
            
            # راه‌اندازی ریپوزیتوری‌ها
            self.repositories['fact'] = FactRepository(self.db_session)
            
            logger.info("اتصال به پایگاه داده با موفقیت برقرار شد.")
            
        except Exception as e:
            logger.error(f"خطا در راه‌اندازی پایگاه داده: {str(e)}")
            raise

    async def _setup_redis(self):
        """راه‌اندازی و پیکربندی Redis."""
        try:
            logger.info("راه‌اندازی اتصال به Redis...")
            
            self.redis_client = Redis.from_url(
                REDIS_URL,
                decode_responses=True
            )
            
            # تست اتصال
            self.redis_client.ping()
            
            logger.info("اتصال به Redis با موفقیت برقرار شد.")
            
        except Exception as e:
            logger.error(f"خطا در راه‌اندازی Redis: {str(e)}")
            raise

    async def _setup_services(self):
        """راه‌اندازی و پیکربندی سرویس‌های مختلف."""
        try:
            logger.info("راه‌اندازی سرویس‌ها...")
            
            # راه‌اندازی سرویس NLP
            self.services['nlp'] = NLPService()
            
            # راه‌اندازی سرویس‌های تحلیل محتوا
            self.services['speech'] = SpeechService()
            self.services['translation'] = TranslationService()
            self.services['video'] = VideoAnalysisService()
            self.services['image'] = ImageAnalysisService()
            
            # راه‌اندازی سرویس‌های راستی‌آزمایی
            self.services['credibility'] = CredibilityService(
                self.repositories['fact']
            )
            self.services['fake_news'] = FakeNewsDetector(
                self.services['nlp']
            )
            self.services['factcheck'] = GoogleFactCheckService()
            
            logger.info("تمام سرویس‌ها با موفقیت راه‌اندازی شدند.")
            
        except Exception as e:
            logger.error(f"خطا در راه‌اندازی سرویس‌ها: {str(e)}")
            raise

    async def _setup_telegram(self):
        """راه‌اندازی و پیکربندی ربات تلگرام."""
        try:
            logger.info("راه‌اندازی ربات تلگرام...")
            
            # ایجاد نمونه ربات
            self.telegram_app = ApplicationBuilder().token(
                TELEGRAM_TOKEN
            ).build()
            
            # ثبت هندلرها
            register_message_handlers(
                self.telegram_app,
                self.services,
                self.repositories
            )
            register_command_handlers(self.telegram_app)
            register_callback_handlers(
                self.telegram_app,
                self.services,
                self.repositories
            )
            
            # اطلاع‌رسانی به ادمین‌ها
            await self._notify_admins("ربات راستی‌آزمایی با موفقیت راه‌اندازی شد.")
            
            logger.info("ربات تلگرام با موفقیت راه‌اندازی شد.")
            
        except Exception as e:
            logger.error(f"خطا در راه‌اندازی ربات تلگرام: {str(e)}")
            raise

    async def _notify_admins(self, message: str):
        """ارسال پیام به ادمین‌های ربات."""
        for admin_id in ADMIN_USER_IDS:
            try:
                await self.telegram_app.bot.send_message(
                    chat_id=admin_id,
                    text=message
                )
            except Exception as e:
                logger.error(f"خطا در ارسال پیام به ادمین {admin_id}: {str(e)}")

    async def run(self):
        """اجرای ربات و شروع پردازش پیام‌ها."""
        try:
            logger.info("شروع اجرای ربات...")
            await self.telegram_app.run_polling()
            
        except Exception as e:
            logger.error(f"خطا در اجرای ربات: {str(e)}")
            raise

    async def cleanup(self):
        """پاکسازی منابع و بستن اتصال‌ها."""
        try:
            logger.info("شروع پاکسازی منابع...")
            
            # بستن اتصال پایگاه داده
            if self.db_session:
                self.db_session.close()
            if self.db_engine:
                self.db_engine.dispose()
                
            # بستن اتصال Redis
            if self.redis_client:
                self.redis_client.close()
                
            # پاکسازی سرویس‌ها
            for service in self.services.values():
                if hasattr(service, 'cleanup'):
                    await service.cleanup()
                    
            logger.info("پاکسازی منابع با موفقیت انجام شد.")
            
        except Exception as e:
            logger.error(f"خطا در پاکسازی منابع: {str(e)}")
            raise

async def main():
    """تابع اصلی برنامه."""
    bot = FactCheckerBot()
    
    try:
        # راه‌اندازی اولیه
        await bot.initialize()
        
        # اجرای ربات
        await bot.run()
        
    except Exception as e:
        logger.error(f"خطای اصلی برنامه: {str(e)}")
        sys.exit(1)
        
    finally:
        # پاکسازی منابع در هر صورت
        await bot.cleanup()

if __name__ == "__main__":
    # اجرای برنامه در حلقه رویداد
    asyncio.run(main())