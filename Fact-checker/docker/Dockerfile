FROM python:3.10-slim

# نصب وابستگی‌های سیستمی
RUN apt-get update && apt-get install -y \
    ffmpeg \
    tesseract-ocr \
    tesseract-ocr-fas \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# تنظیم محیط کاری
WORKDIR /app

# کپی فایل‌های پروژه
COPY requirements.txt .
COPY . .

# نصب وابستگی‌های پایتون
RUN pip install --no-cache-dir -r requirements.txt

# دانلود مدل‌های مورد نیاز
RUN python -c "import nltk; nltk.download('punkt')"
RUN python -c "import spacy; spacy.cli.download('xx_ent_wiki_sm')"

# ایجاد پوشه‌های مورد نیاز
RUN mkdir -p models media temp

# تنظیم متغیرهای محیطی
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# اجرای برنامه
CMD ["python", "main.py"]