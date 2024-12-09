"""
تنظیمات اصلی برنامه.
"""

[... حفظ کد قبلی ...]

# تنظیمات سرویس Google Fact Check
GOOGLE_FACTCHECK_API_KEY = os.getenv('GOOGLE_FACTCHECK_API_KEY')
GOOGLE_FACTCHECK_CONFIG = {
    'request_timeout': 10,
    'max_retries': 3,
    'default_language': 'fa'
}

# سایر تنظیمات...