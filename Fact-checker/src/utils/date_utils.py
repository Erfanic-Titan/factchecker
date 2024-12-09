"""
توابع کار با تاریخ و زمان.
این ماژول شامل توابع مربوط به تبدیل، فرمت‌بندی و محاسبات تاریخ و زمان است.
"""

[... حفظ کد قبلی ...]

        return date.replace(year=year, month=month)
    elif unit == 'days':
        return date + timedelta(days=value)
    elif unit == 'hours':
        return date + timedelta(hours=value)
    elif unit == 'minutes':
        return date + timedelta(minutes=value)
    elif unit == 'seconds':
        return date + timedelta(seconds=value)
    else:
        raise ValueError(f"واحد زمانی {unit} پشتیبانی نمی‌شود")

def get_month_name(month: int, lang: str = 'fa') -> str:
    """
    دریافت نام ماه.
    
    Args:
        month: شماره ماه (1-12)
        lang: زبان خروجی (fa/en)
        
    Returns:
        نام ماه
    """
    if not 1 <= month <= 12:
        raise ValueError("شماره ماه باید بین 1 تا 12 باشد")
        
    persian_months = {
        1: 'فروردین',
        2: 'اردیبهشت',
        3: 'خرداد',
        4: 'تیر',
        5: 'مرداد',
        6: 'شهریور',
        7: 'مهر',
        8: 'آبان',
        9: 'آذر',
        10: 'دی',
        11: 'بهمن',
        12: 'اسفند'
    }
    
    english_months = {
        1: 'January',
        2: 'February',
        3: 'March',
        4: 'April',
        5: 'May',
        6: 'June',
        7: 'July',
        8: 'August',
        9: 'September',
        10: 'October',
        11: 'November',
        12: 'December'
    }
    
    return persian_months[month] if lang == 'fa' else english_months[month]

def get_weekday_name(weekday: int, lang: str = 'fa') -> str:
    """
    دریافت نام روز هفته.
    
    Args:
        weekday: شماره روز هفته (0-6)
        lang: زبان خروجی (fa/en)
        
    Returns:
        نام روز هفته
    """
    if not 0 <= weekday <= 6:
        raise ValueError("شماره روز هفته باید بین 0 تا 6 باشد")
        
    persian_days = {
        0: 'شنبه',
        1: 'یکشنبه',
        2: 'دوشنبه',
        3: 'سه‌شنبه',
        4: 'چهارشنبه',
        5: 'پنج‌شنبه',
        6: 'جمعه'
    }
    
    english_days = {
        0: 'Saturday',
        1: 'Sunday',
        2: 'Monday',
        3: 'Tuesday',
        4: 'Wednesday',
        5: 'Thursday',
        6: 'Friday'
    }
    
    return persian_days[weekday] if lang == 'fa' else english_days[weekday]

def is_valid_date(
    year: int,
    month: int,
    day: int,
    calendar: str = 'jalali'
) -> bool:
    """
    اعتبارسنجی تاریخ.
    
    Args:
        year: سال
        month: ماه
        day: روز
        calendar: نوع تقویم (jalali/gregorian)
        
    Returns:
        معتبر بودن تاریخ
    """
    try:
        if calendar == 'jalali':
            jdatetime.date(year, month, day)
        else:
            datetime(year, month, day)
        return True
    except ValueError:
        return False

def get_date_diff(
    date1: datetime,
    date2: datetime,
    unit: str = 'days'
) -> int:
    """
    محاسبه اختلاف دو تاریخ.
    
    Args:
        date1: تاریخ اول
        date2: تاریخ دوم
        unit: واحد خروجی
        
    Returns:
        اختلاف دو تاریخ در واحد مشخص شده
    """
    diff = date2 - date1
    
    if unit == 'days':
        return diff.days
    elif unit == 'hours':
        return int(diff.total_seconds() / 3600)
    elif unit == 'minutes':
        return int(diff.total_seconds() / 60)
    elif unit == 'seconds':
        return int(diff.total_seconds())
    else:
        raise ValueError(f"واحد {unit} پشتیبانی نمی‌شود")

def get_age(
    birth_date: Union[datetime, str],
    at_date: Optional[datetime] = None
) -> Dict[str, int]:
    """
    محاسبه سن.
    
    Args:
        birth_date: تاریخ تولد
        at_date: تاریخ محاسبه (پیش‌فرض: اکنون)
        
    Returns:
        دیکشنری حاوی سال، ماه و روز
    """
    if isinstance(birth_date, str):
        birth_date = datetime.fromisoformat(birth_date)
        
    if at_date is None:
        at_date = datetime.now()
        
    # محاسبه اختلاف
    years = at_date.year - birth_date.year
    months = at_date.month - birth_date.month
    days = at_date.day - birth_date.day
    
    # تصحیح مقادیر منفی
    if days < 0:
        months -= 1
        days += 30  # تقریبی
        
    if months < 0:
        years -= 1
        months += 12
        
    return {
        'years': years,
        'months': months,
        'days': days
    }

def get_ramadan_date(year: int) -> Dict[str, datetime]:
    """
    محاسبه تاریخ ماه رمضان.
    
    Args:
        year: سال شمسی
        
    Returns:
        دیکشنری حاوی تاریخ شروع و پایان
    """
    # تبدیل به تاریخ قمری
    import hijri_converter
    
    gregorian_year = to_gregorian(f"{year}/01/01", "%Y/%m/%d").year
    hijri = hijri_converter.Gregorian(gregorian_year).to_hijri()
    
    # محاسبه تاریخ رمضان
    ramadan_start = hijri_converter.Hijri(
        hijri.year,
        9,  # ماه رمضان
        1
    ).to_gregorian()
    
    ramadan_end = hijri_converter.Hijri(
        hijri.year,
        9,
        30
    ).to_gregorian()
    
    return {
        'start': ramadan_start,
        'end': ramadan_end
    }

def get_next_working_day(
    date: datetime,
    holidays: List[datetime] = None
) -> datetime:
    """
    محاسبه روز کاری بعدی.
    
    Args:
        date: تاریخ مبدا
        holidays: لیست تعطیلات
        
    Returns:
        تاریخ روز کاری بعدی
    """
    if holidays is None:
        holidays = []
        
    next_day = date + timedelta(days=1)
    
    # بررسی روزهای تعطیل
    while (
        next_day.weekday() in [4, 5] or  # پنج‌شنبه و جمعه
        next_day in holidays
    ):
        next_day += timedelta(days=1)
        
    return next_day

def format_time_ago(date: datetime, lang: str = 'fa') -> str:
    """
    نمایش فاصله زمانی به صورت متنی.
    
    Args:
        date: تاریخ
        lang: زبان خروجی
        
    Returns:
        متن فاصله زمانی (مثلاً "2 روز پیش")
    """
    now = datetime.now()
    diff = now - date
    
    # متن‌های فارسی و انگلیسی
    texts = {
        'fa': {
            'now': 'هم‌اکنون',
            'minutes': 'دقیقه پیش',
            'hours': 'ساعت پیش',
            'days': 'روز پیش',
            'months': 'ماه پیش',
            'years': 'سال پیش'
        },
        'en': {
            'now': 'just now',
            'minutes': 'minutes ago',
            'hours': 'hours ago',
            'days': 'days ago',
            'months': 'months ago',
            'years': 'years ago'
        }
    }[lang]
    
    # محاسبه فاصله
    if diff.days == 0:
        if diff.seconds < 60:
            return texts['now']
        elif diff.seconds < 3600:
            minutes = diff.seconds // 60
            return f"{minutes} {texts['minutes']}"
        else:
            hours = diff.seconds // 3600
            return f"{hours} {texts['hours']}"
    elif diff.days < 30:
        return f"{diff.days} {texts['days']}"
    elif diff.days < 365:
        months = diff.days // 30
        return f"{months} {texts['months']}"
    else:
        years = diff.days // 365
        return f"{years} {texts['years']}"