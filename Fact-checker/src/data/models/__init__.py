"""
در این ماژول مدل‌های پایگاه داده تعریف می‌شوند.
همه مدل‌ها از فایل models.py در اینجا import می‌شوند تا دسترسی به آنها آسان‌تر باشد.
"""

from .models import (
    Base,
    User,
    FactCheck,
    Source,
    Category,
    Tag,
    Media,
    Report,
    Feedback
)

__all__ = [
    'Base',
    'User',
    'FactCheck',
    'Source',
    'Category',
    'Tag',
    'Media',
    'Report',
    'Feedback'
]
