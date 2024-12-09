"""
توابع کمکی برای کار با تلگرام.
این ماژول شامل توابع مختلف برای تسهیل کار با API تلگرام است.
"""

import os
import asyncio
import aiohttp
from typing import Union, Optional, BinaryIO, Dict, List
from datetime import datetime
import json
from telegram import InputFile, Message, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from ...utils.helpers import get_logger
from ...config.config import TELEGRAM_TOKEN, MEDIA_DIR

logger = get_logger(__name__)

async def download_telegram_file(file_obj: BinaryIO, destination: str) -> bool:
    """
    دانلود فایل از تلگرام
    
    Args:
        file_obj: شیء فایل تلگرام
        destination: مسیر مقصد
        
    Returns:
        True در صورت موفقیت
    """
    try:
        await file_obj.download_to_drive(destination)
        return True
    except Exception as e:
        logger.error(f"Error downloading telegram file: {str(e)}")
        return False

async def send_long_message(
    message: Message,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    max_length: int = 4096
) -> List[Message]:
    """
    ارسال پیام‌های طولانی به صورت چند بخشی
    
    Args:
        message: پیام اصلی
        text: متن طولانی
        reply_markup: دکمه‌ها (اختیاری)
        max_length: حداکثر طول هر بخش
        
    Returns:
        لیست پیام‌های ارسال شده
    """
    try:
        messages = []
        
        # تقسیم متن به بخش‌های کوچکتر
        parts = []
        current_part = ""
        
        # تقسیم بر اساس خط جدید برای حفظ خوانایی
        lines = text.split('\n')
        
        for line in lines:
            if len(current_part + line + '\n') > max_length:
                parts.append(current_part)
                current_part = line + '\n'
            else:
                current_part += line + '\n'
                
        if current_part:
            parts.append(current_part)
        
        # ارسال هر بخش
        for i, part in enumerate(parts):
            # فقط بخش آخر دکمه داشته باشد
            markup = reply_markup if i == len(parts) - 1 else None
            
            sent = await message.reply_text(
                text=part.strip(),
                reply_markup=markup
            )
            messages.append(sent)
            
            if i < len(parts) - 1:
                await asyncio.sleep(0.5)  # تاخیر کوتاه بین پیام‌ها
                
        return messages
        
    except Exception as e:
        logger.error(f"Error sending long message: {str(e)}")
        await message.reply_text(
            "متأسفانه در ارسال پیام مشکلی پیش آمد. لطفاً دوباره تلاش کنید."
        )
        return []

async def send_action_until_done(
    message: Message,
    action: str,
    delay: float = 3.0
) -> asyncio.Task:
    """
    نمایش مداوم وضعیت تایپ/آپلود تا پایان پردازش
    
    Args:
        message: پیام اصلی
        action: نوع عملیات
        delay: تاخیر بین هر اعلام وضعیت
        
    Returns:
        تسک ایجاد شده
    """
    async def _send_action():
        try:
            while True:
                await message.chat.send_action(action)
                await asyncio.sleep(delay)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error sending chat action: {str(e)}")
            
    return asyncio.create_task(_send_action())

async def get_user_profile_photos(
    user_id: int,
    limit: int = 1
) -> List[str]:
    """
    دریافت تصاویر پروفایل کاربر
    
    Args:
        user_id: شناسه کاربر
        limit: حداکثر تعداد تصاویر
        
    Returns:
        لیست آدرس تصاویر
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/"
                f"getUserProfilePhotos?user_id={user_id}&limit={limit}"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data['ok']:
                        photos = data['result']['photos']
                        if not photos:
                            return []
                            
                        file_ids = [p[0]['file_id'] for p in photos]
                        photo_urls = []
                        
                        for file_id in file_ids:
                            # دریافت path فایل
                            async with session.get(
                                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/"
                                f"getFile?file_id={file_id}"
                            ) as file_response:
                                if file_response.status == 200:
                                    file_data = await file_response.json()
                                    if file_data['ok']:
                                        file_path = file_data['result']['file_path']
                                        photo_urls.append(
                                            f"https://api.telegram.org/file/bot"
                                            f"{TELEGRAM_TOKEN}/{file_path}"
                                        )
                                        
                        return photo_urls
                        
        return []
        
    except Exception as e:
        logger.error(f"Error getting user profile photos: {str(e)}")
        return []

async def handle_error(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    error: Exception
):
    """
    مدیریت خطاهای تلگرام
    
    Args:
        update: آپدیت تلگرام
        context: کانتکست
        error: خطای رخ داده
    """
    try:
        # لاگ خطا
        logger.error(f"Error handling update {update}: {str(error)}")
        
        # اطلاع‌رسانی به کاربر
        error_message = (
            "متأسفانه در پردازش درخواست شما مشکلی پیش آمد."
            " لطفاً دوباره تلاش کنید."
        )
        
        if isinstance(error, TelegramError):
            if 'Message is too long' in str(error):
                error_message = (
                    "متن پیام بیش از حد طولانی است."
                    " لطفاً متن کوتاه‌تری ارسال کنید."
                )
            elif 'Wrong file identifier' in str(error):
                error_message = (
                    "فایل مورد نظر در دسترس نیست."
                    " لطفاً دوباره آن را ارسال کنید."
                )
            elif 'Query is too old' in str(error):
                error_message = (
                    "درخواست شما منقضی شده است."
                    " لطفاً دوباره تلاش کنید."
                )
        
        # ارسال پیام خطا
        if update.callback_query:
            await update.callback_query.message.reply_text(error_message)
        elif update.message:
            await update.message.reply_text(error_message)
            
    except Exception as e:
        logger.error(f"Error in error handler: {str(e)}")

def cleanup_temp_files():
    """
    پاکسازی فایل‌های موقت
    """
    try:
        # حذف فایل‌های قدیمی‌تر از یک روز
        current_time = datetime.now().timestamp()
        one_day = 86400  # 24 * 60 * 60
        
        for filename in os.listdir(MEDIA_DIR):
            file_path = os.path.join(MEDIA_DIR, filename)
            # بررسی زمان ایجاد فایل
            if os.path.getctime(file_path) < current_time - one_day:
                os.remove(file_path)
                logger.info(f"Removed old temp file: {filename}")
                
    except Exception as e:
        logger.error(f"Error cleaning up temp files: {str(e)}")

async def save_user_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    ذخیره اطلاعات کاربر
    
    Args:
        update: آپدیت تلگرام
        context: کانتکست
    """
    try:
        user = update.effective_user
        if user:
            from ...core.services.fact_checker import FactCheckerService
            fact_checker = FactCheckerService()
            
            # بروزرسانی اطلاعات کاربر
            await fact_checker.update_user_info(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                language_code=user.language_code
            )
            
    except Exception as e:
        logger.error(f"Error saving user data: {str(e)}")

async def get_chat_member_count(chat_id: Union[str, int]) -> Optional[int]:
    """
    دریافت تعداد اعضای یک گروه
    
    Args:
        chat_id: شناسه گروه
        
    Returns:
        تعداد اعضا یا None
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/"
                f"getChatMemberCount?chat_id={chat_id}"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data['ok']:
                        return data['result']
        return None
        
    except Exception as e:
        logger.error(f"Error getting chat member count: {str(e)}")
        return None

def is_user_admin(user_id: int, admin_list: List[int]) -> bool:
    """
    بررسی ادمین بودن کاربر
    
    Args:
        user_id: شناسه کاربر
        admin_list: لیست ادمین‌ها
        
    Returns:
        True اگر کاربر ادمین باشد
    """
    return user_id in admin_list

async def restrict_spam(
    message: Message,
    context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """
    محدودسازی پیام‌های تکراری
    
    Args:
        message: پیام کاربر
        context: کانتکست
        
    Returns:
        True اگر پیام اسپم باشد
    """
    try:
        user_id = message.from_user.id
        now = datetime.now().timestamp()
        
        if 'spam_control' not in context.user_data:
            context.user_data['spam_control'] = {
                'count': 1,
                'first_message': now
            }
            return False
            
        # بررسی تعداد پیام‌ها در بازه زمانی
        control = context.user_data['spam_control']
        time_diff = now - control['first_message']
        
        if time_diff < 60:  # یک دقیقه
            control['count'] += 1
            if control['count'] > 10:  # حداکثر 10 پیام در دقیقه
                await message.reply_text(
                    "لطفاً از ارسال پیام‌های پی در پی خودداری کنید."
                )
                return True
        else:
            # ریست کردن شمارنده
            control['count'] = 1
            control['first_message'] = now
            
        return False
        
    except Exception as e:
        logger.error(f"Error checking spam: {str(e)}")
        return False

async def forward_to_channel(
    message: Message,
    channel_id: Union[str, int]
) -> bool:
    """
    فوروارد پیام به کانال
    
    Args:
        message: پیام اصلی
        channel_id: شناسه کانال
        
    Returns:
        True در صورت موفقیت
    """
    try:
        await message.forward(
            chat_id=channel_id,
            disable_notification=True
        )
        return True
        
    except Exception as e:
        logger.error(f"Error forwarding message to channel: {str(e)}")
        return False

def format_number(number: Union[int, float]) -> str:
    """
    فرمت‌بندی اعداد به فارسی
    
    Args:
        number: عدد ورودی
        
    Returns:
        عدد فرمت‌بندی شده
    """
    try:
        persian_numbers = '۰۱۲۳۴۵۶۷۸۹'
        english_numbers = '0123456789'
        
        number_str = format(number, ',')
        result = number_str.translate(
            str.maketrans(english_numbers, persian_numbers)
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error formatting number: {str(e)}")
        return str(number)
