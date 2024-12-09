"""
توابع کمکی مورد استفاده در سراسر برنامه.
این ماژول شامل توابع عمومی و پرکاربرد است که در بخش‌های مختلف برنامه استفاده می‌شوند.
"""

import re
import logging
import unicodedata
from typing import Dict, List, Optional, Union
from datetime import datetime
from urllib.parse import urlparse
import hashlib
import json
import numpy as np
from pathlib import Path
from logging.handlers import RotatingFileHandler

from config.config import LOGS_DIR

def setup_logger(name: str, log_file: str, level=logging.INFO) -> logging.Logger:
    """
    راه‌اندازی لاگر با تنظیمات مناسب.
    
    Args:
        name: نام لاگر
        log_file: مسیر فایل لاگ
        level: سطح لاگ کردن
        
    Returns:
        آبجکت لاگر پیکربندی شده
    """
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )

    handler = RotatingFileHandler(
        Path(LOGS_DIR) / log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger

def clean_text(text: str) -> str:
    """
    پاکسازی و نرمال‌سازی متن.
    
    Args:
        text: متن ورودی
        
    Returns:
        متن پاکسازی شده
    """
    if not text:
        return ""

    # حذف کاراکترهای کنترلی
    text = ''.join(ch for ch in text if unicodedata.category(ch)[0] != 'C')
    
    # نرمال‌سازی فاصله‌ها
    text = ' '.join(text.split())
    
    # نرمال‌سازی کاراکترهای عربی/فارسی
    replacements = {
        'ي': 'ی',
        'ك': 'ک',
        '٠': '0',
        '١': '1',
        '٢': '2',
        '٣': '3',
        '٤': '4',
        '٥': '5',
        '٦': '6',
        '٧': '7',
        '٨': '8',
        '٩': '9'
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    return text.strip()

def is_valid_url(url: str) -> bool:
    """
    بررسی معتبر بودن URL.
    
    Args:
        url: آدرس URL
        
    Returns:
        صحیح/غلط بودن URL
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def extract_domain(url: str) -> str:
    """
    استخراج دامنه از URL.
    
    Args:
        url: آدرس URL
        
    Returns:
        دامنه استخراج شده
    """
    try:
        return urlparse(url).netloc.lower()
    except:
        return ""

async def calculate_similarity_score(
    text1: str,
    text2: str,
    method: str = 'cosine'
) -> float:
    """
    محاسبه میزان شباهت بین دو متن.
    
    Args:
        text1: متن اول
        text2: متن دوم
        method: روش محاسبه شباهت
        
    Returns:
        امتیاز شباهت بین 0 تا 1
    """
    if not text1 or not text2:
        return 0.0

    # نرمال‌سازی متن‌ها
    text1 = clean_text(text1.lower())
    text2 = clean_text(text2.lower())

    if method == 'cosine':
        # تبدیل متن‌ها به بردار
        words1 = set(text1.split())
        words2 = set(text2.split())
        words = words1.union(words2)

        v1 = np.array([1 if w in words1 else 0 for w in words])
        v2 = np.array([1 if w in words2 else 0 for w in words])

        # محاسبه شباهت کسینوسی
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    elif method == 'jaccard':
        # محاسبه شباهت ژاکارد
        set1 = set(text1.split())
        set2 = set(text2.split())
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))

        if union == 0:
            return 0.0

        return float(intersection / union)

    else:
        raise ValueError(f"روش {method} پشتیبانی نمی‌شود")

def format_date(date: datetime, format: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    فرمت‌بندی تاریخ و زمان.
    
    Args:
        date: آبجکت تاریخ و زمان
        format: قالب مورد نظر
        
    Returns:
        رشته فرمت‌بندی شده تاریخ
    """
    try:
        return date.strftime(format)
    except:
        return str(date)

def calculate_percentage(value: float, decimals: int = 1) -> float:
    """
    تبدیل عدد اعشاری به درصد.
    
    Args:
        value: عدد اعشاری
        decimals: تعداد ارقام اعشار
        
    Returns:
        عدد درصدی
    """
    try:
        return round(value * 100, decimals)
    except:
        return 0.0

def generate_file_hash(content: bytes) -> str:
    """
    تولید هش برای محتوای فایل.
    
    Args:
        content: محتوای باینری فایل
        
    Returns:
        رشته هش
    """
    return hashlib.sha256(content).hexdigest()

def detect_language(text: str) -> str:
    """
    تشخیص زبان متن.
    
    Args:
        text: متن ورودی
        
    Returns:
        کد زبان تشخیص داده شده
    """
    # شناسایی الگوهای رایج فارسی
    persian_chars = re.findall(r'[\u0600-\u06FF]', text)
    if len(persian_chars) > len(text) * 0.3:
        return 'fa'
    
    # شناسایی الگوهای رایج عربی
    arabic_chars = re.findall(r'[\u0627-\u064A]', text)
    if len(arabic_chars) > len(text) * 0.3:
        return 'ar'
    
    # شناسایی الگوهای رایج انگلیسی
    english_chars = re.findall(r'[a-zA-Z]', text)
    if len(english_chars) > len(text) * 0.3:
        return 'en'
    
    return 'unknown'

def sanitize_filename(filename: str) -> str:
    """
    پاکسازی نام فایل از کاراکترهای غیرمجاز.
    
    Args:
        filename: نام فایل
        
    Returns:
        نام فایل پاکسازی شده
    """
    # حذف کاراکترهای غیرمجاز
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # کوتاه کردن نام طولانی
    name, ext = os.path.splitext(filename)
    if len(name) > 200:
        name = name[:200]
    
    return name + ext

def truncate_text(
    text: str,
    max_length: int = 100,
    suffix: str = '...'
) -> str:
    """
    کوتاه کردن متن با حفظ انسجام.
    
    Args:
        text: متن ورودی
        max_length: حداکثر طول مجاز
        suffix: پسوند
        
    Returns:
        متن کوتاه شده
    """
    if not text or len(text) <= max_length:
        return text
        
    return text[:max_length - len(suffix)].rsplit(' ', 1)[0] + suffix

def format_file_size(size_in_bytes: int) -> str:
    """
    فرمت‌بندی اندازه فایل.
    
    Args:
        size_in_bytes: اندازه به بایت
        
    Returns:
        اندازه فرمت‌بندی شده
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.1f} {unit}"
        size_in_bytes /= 1024
    return f"{size_in_bytes:.1f} TB"

def is_valid_json(text: str) -> bool:
    """
    بررسی معتبر بودن JSON.
    
    Args:
        text: متن JSON
        
    Returns:
        صحیح/غلط بودن ساختار
    """
    try:
        json.loads(text)
        return True
    except:
        return False

def extract_numbers(text: str) -> List[float]:
    """
    استخراج اعداد از متن.
    
    Args:
        text: متن ورودی
        
    Returns:
        لیست اعداد استخراج شده
    """
    # الگوی اعداد فارسی و انگلیسی
    pattern = r'[-+]?\d*\.?\d+'
    
    # تبدیل اعداد فارسی به انگلیسی
    text = text.translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789'))
    
    # استخراج و تبدیل به float
    numbers = []
    for match in re.finditer(pattern, text):
        try:
            numbers.append(float(match.group()))
        except:
            continue
            
    return numbers

def normalize_phone_number(phone: str) -> str:
    """
    نرمال‌سازی شماره تلفن.
    
    Args:
        phone: شماره تلفن
        
    Returns:
        شماره تلفن نرمال‌سازی شده
    """
    # حذف کاراکترهای اضافی
    phone = re.sub(r'[^\d+]', '', phone)
    
    # اضافه کردن کد کشور
    if phone.startswith('0'):
        phone = '+98' + phone[1:]
    elif not phone.startswith('+'):
        phone = '+' + phone
        
    return phone

def get_file_extension(filename: str) -> str:
    """
    استخراج پسوند فایل.
    
    Args:
        filename: نام فایل
        
    Returns:
        پسوند فایل
    """
    return Path(filename).suffix.lower()

def is_valid_email(email: str) -> bool:
    """
    بررسی معتبر بودن ایمیل.
    
    Args:
        email: آدرس ایمیل
        
    Returns:
        صحیح/غلط بودن ایمیل
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))