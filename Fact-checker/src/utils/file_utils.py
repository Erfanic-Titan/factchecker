"""
توابع کار با فایل‌ها و رسانه‌ها.
این ماژول شامل توابع مربوط به مدیریت، پردازش و تبدیل انواع فایل‌هاست.
"""

[... حفظ کد قبلی ...]

        'mime_type': get_file_type(file_path),
        'hash': hash_file(path.read_bytes()) if path.is_file() else None,
        'is_hidden': path.name.startswith('.'),
        'is_dir': path.is_dir(),
        'is_file': path.is_file(),
        'is_symlink': path.is_symlink()
    }

def safe_delete_file(file_path: str) -> bool:
    """
    حذف ایمن فایل.
    
    Args:
        file_path: مسیر فایل
        
    Returns:
        موفقیت/عدم موفقیت حذف
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return False
            
        # بررسی دسترسی‌ها
        if not os.access(path, os.W_OK):
            raise PermissionError(f"عدم دسترسی به {file_path}")
            
        # حذف فایل یا پوشه
        if path.is_file():
            path.unlink()
        else:
            shutil.rmtree(path)
            
        return True
        
    except Exception as e:
        raise OSError(f"خطا در حذف {file_path}: {str(e)}")

def create_zip_archive(
    files: List[str],
    output_path: str,
    password: Optional[str] = None
) -> str:
    """
    ایجاد آرشیو فشرده از فایل‌ها.
    
    Args:
        files: لیست مسیر فایل‌ها
        output_path: مسیر خروجی
        password: رمز آرشیو (اختیاری)
        
    Returns:
        مسیر آرشیو ایجاد شده
    """
    import zipfile
    import pyminizip
    
    if password:
        # استفاده از pyminizip برای رمزگذاری
        compression_level = 5
        pyminizip.compress_multiple(
            files,
            [os.path.basename(f) for f in files],
            output_path,
            password,
            compression_level
        )
    else:
        # استفاده از zipfile استاندارد
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in files:
                zipf.write(file, os.path.basename(file))
                
    return output_path

def extract_zip_archive(
    archive_path: str,
    extract_path: str,
    password: Optional[str] = None
) -> List[str]:
    """
    استخراج محتویات آرشیو فشرده.
    
    Args:
        archive_path: مسیر آرشیو
        extract_path: مسیر استخراج
        password: رمز آرشیو (اختیاری)
        
    Returns:
        لیست فایل‌های استخراج شده
    """
    import zipfile
    
    # ایجاد مسیر استخراج
    Path(extract_path).mkdir(parents=True, exist_ok=True)
    
    extracted_files = []
    with zipfile.ZipFile(archive_path) as zipf:
        # بررسی نیاز به رمز
        if zipf.encrypted and not password:
            raise ValueError("این آرشیو نیاز به رمز عبور دارد")
            
        # استخراج فایل‌ها
        for member in zipf.namelist():
            # بررسی مسیر امن
            if member.startswith('..') or member.startswith('/'):
                continue
                
            try:
                zipf.extract(member, extract_path, pwd=password.encode() if password else None)
                extracted_files.append(os.path.join(extract_path, member))
            except Exception as e:
                raise OSError(f"خطا در استخراج {member}: {str(e)}")
                
    return extracted_files

def convert_image_format(
    image_path: str,
    output_format: str,
    quality: int = 95
) -> str:
    """
    تبدیل فرمت تصویر.
    
    Args:
        image_path: مسیر تصویر ورودی
        output_format: فرمت خروجی
        quality: کیفیت خروجی
        
    Returns:
        مسیر تصویر خروجی
    """
    output_format = output_format.upper()
    supported_formats = {'JPEG', 'PNG', 'WEBP', 'BMP', 'TIFF'}
    
    if output_format not in supported_formats:
        raise ValueError(f"فرمت {output_format} پشتیبانی نمی‌شود")
    
    # ساخت مسیر خروجی
    input_path = Path(image_path)
    output_path = input_path.with_suffix(f".{output_format.lower()}")
    
    with Image.open(image_path) as img:
        # تبدیل به RGB اگر لازم باشد
        if img.mode in ('RGBA', 'P') and output_format == 'JPEG':
            img = img.convert('RGB')
            
        # ذخیره با فرمت جدید
        img.save(output_path, output_format, quality=quality, optimize=True)
        
    return str(output_path)

def create_image_variants(
    image_path: str,
    sizes: List[Tuple[int, int]],
    formats: List[str] = ['JPEG', 'WEBP']
) -> Dict[str, str]:
    """
    ایجاد نسخه‌های مختلف از تصویر.
    
    Args:
        image_path: مسیر تصویر اصلی
        sizes: لیست اندازه‌های مورد نیاز
        formats: لیست فرمت‌های مورد نیاز
        
    Returns:
        دیکشنری مسیر نسخه‌های ایجاد شده
    """
    variants = {}
    input_path = Path(image_path)
    
    with Image.open(image_path) as img:
        # تولید نسخه‌های مختلف
        for size in sizes:
            # تغییر اندازه
            resized = img.copy()
            resized.thumbnail(size)
            
            for fmt in formats:
                # تبدیل به RGB اگر لازم باشد
                if resized.mode in ('RGBA', 'P') and fmt == 'JPEG':
                    resized = resized.convert('RGB')
                
                # ساخت نام فایل
                variant_name = f"{size[0]}x{size[1]}_{fmt.lower()}"
                output_path = input_path.with_name(
                    f"{input_path.stem}_{variant_name}{input_path.suffix}"
                )
                
                # ذخیره نسخه
                resized.save(output_path, fmt, quality=85, optimize=True)
                variants[variant_name] = str(output_path)
                
    return variants

def clean_temp_files(max_age: int = 24 * 3600) -> int:
    """
    پاکسازی فایل‌های موقت قدیمی.
    
    Args:
        max_age: حداکثر عمر فایل به ثانیه
        
    Returns:
        تعداد فایل‌های پاک شده
    """
    temp_dir = Path(TEMP_DIR)
    if not temp_dir.exists():
        return 0
        
    removed_count = 0
    current_time = datetime.now().timestamp()
    
    for path in temp_dir.glob('**/*'):
        if not path.is_file():
            continue
            
        # بررسی عمر فایل
        file_age = current_time - path.stat().st_mtime
        if file_age > max_age:
            try:
                path.unlink()
                removed_count += 1
            except Exception:
                continue
                
    return removed_count

def get_media_duration(file_path: str) -> Optional[float]:
    """
    دریافت مدت زمان فایل‌های صوتی و تصویری.
    
    Args:
        file_path: مسیر فایل
        
    Returns:
        مدت زمان به ثانیه یا None
    """
    try:
        import av
        container = av.open(file_path)
        duration = container.duration / av.time_base
        container.close()
        return duration
    except Exception:
        return None

def is_valid_media(
    file_path: str,
    allowed_types: List[str],
    max_size: Optional[int] = None
) -> bool:
    """
    بررسی معتبر بودن فایل رسانه.
    
    Args:
        file_path: مسیر فایل
        allowed_types: انواع MIME مجاز
        max_size: حداکثر حجم مجاز
        
    Returns:
        معتبر بودن فایل
    """
    # بررسی وجود فایل
    if not os.path.exists(file_path):
        return False
        
    # بررسی نوع فایل
    mime_type = get_file_type(file_path)
    if mime_type not in allowed_types:
        return False
        
    # بررسی حجم فایل
    if max_size and os.path.getsize(file_path) > max_size:
        return False
        
    # بررسی سالم بودن فایل
    try:
        if mime_type.startswith('image/'):
            Image.open(file_path).verify()
        elif mime_type.startswith(('video/', 'audio/')):
            import av
            container = av.open(file_path)
            container.close()
    except Exception:
        return False
        
    return True