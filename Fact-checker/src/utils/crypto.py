"""
توابع رمزنگاری و امنیتی.
این ماژول شامل توابع مربوط به رمزنگاری، رمزگشایی و تولید توکن‌های امن است.
"""

import base64
import hashlib
import hmac
import secrets
from typing import Tuple, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

def generate_salt(length: int = 32) -> bytes:
    """
    تولید نمک تصادفی برای هش کردن.
    
    Args:
        length: طول نمک
        
    Returns:
        نمک تولید شده
    """
    return secrets.token_bytes(length)

def hash_password(
    password: str,
    salt: Optional[bytes] = None
) -> Tuple[bytes, bytes]:
    """
    هش کردن رمز عبور با استفاده از نمک.
    
    Args:
        password: رمز عبور
        salt: نمک (اختیاری)
        
    Returns:
        تاپل شامل (هش رمز عبور, نمک)
    """
    if salt is None:
        salt = generate_salt()
        
    # استفاده از PBKDF2 برای تولید هش
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000
    )
    
    password_hash = kdf.derive(password.encode())
    return password_hash, salt

def verify_password(
    password: str,
    stored_hash: bytes,
    salt: bytes
) -> bool:
    """
    بررسی صحت رمز عبور.
    
    Args:
        password: رمز عبور
        stored_hash: هش ذخیره شده
        salt: نمک
        
    Returns:
        صحیح/غلط بودن رمز عبور
    """
    # تولید هش جدید با همان نمک
    new_hash, _ = hash_password(password, salt)
    return hmac.compare_digest(new_hash, stored_hash)

def generate_token(length: int = 32) -> str:
    """
    تولید توکن تصادفی امن.
    
    Args:
        length: طول توکن
        
    Returns:
        توکن تولید شده
    """
    return secrets.token_urlsafe(length)

def encrypt_data(data: bytes, key: bytes) -> bytes:
    """
    رمزنگاری داده با استفاده از Fernet.
    
    Args:
        data: داده‌های خام
        key: کلید رمزنگاری
        
    Returns:
        داده‌های رمزنگاری شده
    """
    if not isinstance(key, bytes):
        raise TypeError("کلید باید از نوع bytes باشد")
        
    # تولید کلید Fernet از کلید ورودی
    fernet_key = base64.urlsafe_b64encode(key[:32].ljust(32, b'\0'))
    cipher = Fernet(fernet_key)
    
    return cipher.encrypt(data)

def decrypt_data(encrypted_data: bytes, key: bytes) -> bytes:
    """
    رمزگشایی داده‌های رمزنگاری شده.
    
    Args:
        encrypted_data: داده‌های رمزنگاری شده
        key: کلید رمزنگاری
        
    Returns:
        داده‌های اصلی
    """
    if not isinstance(key, bytes):
        raise TypeError("کلید باید از نوع bytes باشد")
        
    # تولید کلید Fernet از کلید ورودی
    fernet_key = base64.urlsafe_b64encode(key[:32].ljust(32, b'\0'))
    cipher = Fernet(fernet_key)
    
    return cipher.decrypt(encrypted_data)

def generate_api_key() -> str:
    """
    تولید کلید API امن.
    
    Returns:
        کلید API تولید شده
    """
    # ترکیب زمان فعلی و داده‌های تصادفی
    random_bytes = secrets.token_bytes(32)
    api_key = base64.urlsafe_b64encode(random_bytes).decode('utf-8')
    
    return f"fck_{api_key}"  # پیشوند برای شناسایی نوع کلید

def hash_file(file_data: bytes, algorithm: str = 'sha256') -> str:
    """
    تولید هش از محتوای فایل.
    
    Args:
        file_data: محتوای فایل
        algorithm: الگوریتم هش
        
    Returns:
        هش فایل
    """
    if algorithm == 'md5':
        hash_obj = hashlib.md5()
    elif algorithm == 'sha1':
        hash_obj = hashlib.sha1()
    elif algorithm == 'sha256':
        hash_obj = hashlib.sha256()
    elif algorithm == 'sha512':
        hash_obj = hashlib.sha512()
    else:
        raise ValueError(f"الگوریتم {algorithm} پشتیبانی نمی‌شود")
        
    hash_obj.update(file_data)
    return hash_obj.hexdigest()

def generate_session_id() -> str:
    """
    تولید شناسه نشست امن.
    
    Returns:
        شناسه نشست
    """
    # ترکیب زمان و داده‌های تصادفی
    session_bytes = secrets.token_bytes(16)
    return base64.urlsafe_b64encode(session_bytes).decode('utf-8')

def sign_data(data: bytes, key: bytes) -> bytes:
    """
    امضای دیجیتال داده‌ها.
    
    Args:
        data: داده‌های ورودی
        key: کلید امضا
        
    Returns:
        امضای دیجیتال
    """
    return hmac.new(key, data, hashlib.sha256).digest()

def verify_signature(
    data: bytes,
    signature: bytes,
    key: bytes
) -> bool:
    """
    بررسی صحت امضای دیجیتال.
    
    Args:
        data: داده‌های اصلی
        signature: امضای دیجیتال
        key: کلید امضا
        
    Returns:
        صحیح/غلط بودن امضا
    """
    expected_signature = sign_data(data, key)
    return hmac.compare_digest(signature, expected_signature)

def derive_key(
    master_key: bytes,
    purpose: str,
    length: int = 32
) -> bytes:
    """
    مشتق کردن کلید جدید از کلید اصلی.
    
    Args:
        master_key: کلید اصلی
        purpose: هدف استفاده از کلید
        length: طول کلید مشتق شده
        
    Returns:
        کلید مشتق شده
    """
    if not isinstance(master_key, bytes):
        raise TypeError("کلید اصلی باید از نوع bytes باشد")
        
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=length,
        salt=purpose.encode(),
        iterations=1000
    )
    
    return kdf.derive(master_key)