"""
پیکربندی محیط Alembic برای مدیریت مهاجرت‌های پایگاه داده.
"""

from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys
from dotenv import load_dotenv

# اضافه کردن مسیر پروژه به PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# بارگذاری تنظیمات محیطی
load_dotenv()

# این خط مدل‌های SQLAlchemy را وارد می‌کند
from src.data.models.models import Base

# پیکربندی alembic.ini
config = context.config

# پیکربندی لاگر از فایل alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# اضافه کردن MetaData برای تولید مهاجرت‌ها
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """
    اجرای مهاجرت‌ها در حالت آفلاین.
    
    این حالت زمانی استفاده می‌شود که نمی‌خواهیم به پایگاه داده متصل شویم.
    مهاجرت‌ها به صورت SQL خام تولید می‌شوند.
    """
    url = os.getenv("DATABASE_URL")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """
    اجرای مهاجرت‌ها در حالت آنلاین.
    
    در این حالت، مستقیماً به پایگاه داده متصل می‌شویم و تغییرات را اعمال می‌کنیم.
    این حالت معمول برای توسعه و تولید است.
    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = os.getenv("DATABASE_URL")
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()