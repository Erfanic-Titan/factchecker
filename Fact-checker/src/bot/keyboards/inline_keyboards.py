"""
ماژول کیبوردهای اینلاین برای ربات تلگرام.
این ماژول شامل توابع ایجاد انواع مختلف کیبوردهای اینلاین است.
"""

import json
from typing import Dict, List, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    ایجاد کیبورد منوی اصلی.
    
    Returns:
        کیبورد اینلاین حاوی دکمه‌های منوی اصلی
    """
    keyboard = [
        [
            InlineKeyboardButton(
                "📝 ارسال متن",
                callback_data='{"action":"send_text"}'
            ),
            InlineKeyboardButton(
                "🖼 ارسال تصویر",
                callback_data='{"action":"send_image"}'
            )
        ],
        [
            InlineKeyboardButton(
                "🎥 ارسال ویدیو",
                callback_data='{"action":"send_video"}'
            ),
            InlineKeyboardButton(
                "🎤 ارسال صدا",
                callback_data='{"action":"send_voice"}'
            )
        ],
        [
            InlineKeyboardButton(
                "📄 ارسال سند",
                callback_data='{"action":"send_document"}'
            ),
            InlineKeyboardButton(
                "🔗 ارسال لینک",
                callback_data='{"action":"send_link"}'
            )
        ],
        [
            InlineKeyboardButton(
                "⚙️ تنظیمات",
                callback_data='{"action":"settings"}'
            ),
            InlineKeyboardButton(
                "❓ راهنما",
                callback_data='{"action":"help"}'
            )
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_verification_result_keyboard(result: Dict) -> InlineKeyboardMarkup:
    """
    ایجاد کیبورد نتیجه راستی‌آزمایی.
    
    Args:
        result: دیکشنری حاوی نتایج راستی‌آزمایی
        
    Returns:
        کیبورد اینلاین حاوی دکمه‌های عملیات روی نتیجه
    """
    fact_check_id = result.get('id')
    
    keyboard = [
        [
            InlineKeyboardButton(
                "📊 جزئیات بیشتر",
                callback_data=f'{{"action":"show_details","id":{fact_check_id}}}'
            ),
            InlineKeyboardButton(
                "📤 اشتراک‌گذاری",
                callback_data=f'{{"action":"share_result","id":{fact_check_id}}}'
            )
        ],
        [
            InlineKeyboardButton(
                "👍 موافقم",
                callback_data=f'{{"action":"feedback","id":{fact_check_id},"value":"agree"}}'
            ),
            InlineKeyboardButton(
                "👎 مخالفم",
                callback_data=f'{{"action":"feedback","id":{fact_check_id},"value":"disagree"}}'
            )
        ],
        [
            InlineKeyboardButton(
                "✍️ ثبت نظر",
                callback_data=f'{{"action":"add_comment","id":{fact_check_id}}}'
            ),
            InlineKeyboardButton(
                "⚠️ گزارش مشکل",
                callback_data=f'{{"action":"report_issue","id":{fact_check_id}}}'
            )
        ],
        [
            InlineKeyboardButton(
                "🔄 بررسی مجدد",
                callback_data=f'{{"action":"recheck","id":{fact_check_id}}}'
            ),
            InlineKeyboardButton(
                "🏠 منوی اصلی",
                callback_data='{"action":"main_menu"}'
            )
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_settings_keyboard(current_settings: Dict) -> InlineKeyboardMarkup:
    """
    ایجاد کیبورد تنظیمات.
    
    Args:
        current_settings: دیکشنری حاوی تنظیمات فعلی
        
    Returns:
        کیبورد اینلاین حاوی دکمه‌های تنظیمات
    """
    # دریافت مقادیر فعلی
    language = current_settings.get('language', 'fa')
    report_format = current_settings.get('report_format', 'text')
    notifications = current_settings.get('notifications', True)
    
    # تنظیم متن دکمه‌ها بر اساس مقادیر فعلی
    lang_text = "🌐 زبان: فارسی" if language == 'fa' else "🌐 Language: English"
    format_text = "📄 قالب گزارش: " + {
        'text': 'متنی',
        'html': 'HTML',
        'pdf': 'PDF'
    }.get(report_format, 'متنی')
    notif_text = "🔔 اعلان‌ها: " + ("فعال" if notifications else "غیرفعال")
    
    keyboard = [
        [
            InlineKeyboardButton(
                lang_text,
                callback_data='{"setting":"language"}'
            )
        ],
        [
            InlineKeyboardButton(
                format_text,
                callback_data='{"setting":"report_format"}'
            )
        ],
        [
            InlineKeyboardButton(
                notif_text,
                callback_data='{"setting":"notifications"}'
            )
        ],
        [
            InlineKeyboardButton(
                "💾 ذخیره تنظیمات",
                callback_data='{"setting":"save"}'
            )
        ],
        [
            InlineKeyboardButton(
                "🏠 منوی اصلی",
                callback_data='{"action":"main_menu"}'
            )
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_language_keyboard() -> InlineKeyboardMarkup:
    """
    ایجاد کیبورد انتخاب زبان.
    
    Returns:
        کیبورد اینلاین حاوی دکمه‌های انتخاب زبان
    """
    keyboard = [
        [
            InlineKeyboardButton(
                "🇮🇷 فارسی",
                callback_data='{"setting":"language","value":"fa"}'
            )
        ],
        [
            InlineKeyboardButton(
                "🇬🇧 English",
                callback_data='{"setting":"language","value":"en"}'
            )
        ],
        [
            InlineKeyboardButton(
                "🇸🇦 العربية",
                callback_data='{"setting":"language","value":"ar"}'
            )
        ],
        [
            InlineKeyboardButton(
                "↩️ بازگشت",
                callback_data='{"action":"settings"}'
            )
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_report_format_keyboard() -> InlineKeyboardMarkup:
    """
    ایجاد کیبورد انتخاب قالب گزارش.
    
    Returns:
        کیبورد اینلاین حاوی دکمه‌های انتخاب قالب
    """
    keyboard = [
        [
            InlineKeyboardButton(
                "📝 متنی",
                callback_data='{"setting":"report_format","value":"text"}'
            )
        ],
        [
            InlineKeyboardButton(
                "🌐 HTML",
                callback_data='{"setting":"report_format","value":"html"}'
            )
        ],
        [
            InlineKeyboardButton(
                "📑 PDF",
                callback_data='{"setting":"report_format","value":"pdf"}'
            )
        ],
        [
            InlineKeyboardButton(
                "↩️ بازگشت",
                callback_data='{"action":"settings"}'
            )
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_notification_settings_keyboard() -> InlineKeyboardMarkup:
    """
    ایجاد کیبورد تنظیمات اعلان‌ها.
    
    Returns:
        کیبورد اینلاین حاوی دکمه‌های تنظیمات اعلان
    """
    keyboard = [
        [
            InlineKeyboardButton(
                "✅ فعال",
                callback_data='{"setting":"notifications","value":true}'
            )
        ],
        [
            InlineKeyboardButton(
                "❌ غیرفعال",
                callback_data='{"setting":"notifications","value":false}'
            )
        ],
        [
            InlineKeyboardButton(
                "↩️ بازگشت",
                callback_data='{"action":"settings"}'
            )
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_confirmation_keyboard(
    action: str,
    item_id: Optional[int] = None
) -> InlineKeyboardMarkup:
    """
    ایجاد کیبورد تأیید عملیات.
    
    Args:
        action: نوع عملیات
        item_id: شناسه آیتم (اختیاری)
        
    Returns:
        کیبورد اینلاین حاوی دکمه‌های تأیید/لغو
    """
    callback_data = {
        'action': action,
        'confirmed': True
    }
    
    if item_id is not None:
        callback_data['id'] = item_id
    
    keyboard = [
        [
            InlineKeyboardButton(
                "✅ تأیید",
                callback_data=json.dumps(callback_data)
            ),
            InlineKeyboardButton(
                "❌ انصراف",
                callback_data=json.dumps({'action': 'cancel'})
            )
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_pagination_keyboard(
    current_page: int,
    total_pages: int,
    base_callback: str
) -> InlineKeyboardMarkup:
    """
    ایجاد کیبورد صفحه‌بندی.
    
    Args:
        current_page: شماره صفحه فعلی
        total_pages: تعداد کل صفحات
        base_callback: داده کال‌بک پایه
        
    Returns:
        کیبورد اینلاین حاوی دکمه‌های پیمایش
    """
    keyboard = []
    
    # دکمه‌های پیمایش
    nav_buttons = []
    if current_page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                "◀️ قبلی",
                callback_data=f'{base_callback}_page_{current_page-1}'
            )
        )
        
    nav_buttons.append(
        InlineKeyboardButton(
            f"📄 {current_page} از {total_pages}",
            callback_data="noop"
        )
    )
    
    if current_page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(
                "بعدی ▶️",
                callback_data=f'{base_callback}_page_{current_page+1}'
            )
        )
        
    keyboard.append(nav_buttons)
    
    # دکمه بازگشت
    keyboard.append([
        InlineKeyboardButton(
            "🏠 منوی اصلی",
            callback_data='{"action":"main_menu"}'
        )
    ])
    
    return InlineKeyboardMarkup(keyboard)