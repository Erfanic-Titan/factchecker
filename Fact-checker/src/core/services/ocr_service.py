"""
سرویس OCR برای استخراج متن از تصاویر و پردازش آن‌ها.
"""
from typing import Dict, List, Optional, Tuple
import logging
import cv2
import numpy as np
from PIL import Image
import pytesseract
from pathlib import Path
import tempfile
import os

logger = logging.getLogger(__name__)

class OCRService:
    """کلاس اصلی برای پردازش تصاویر و استخراج متن."""
    
    def __init__(self):
        self.initialize_tesseract()
        
    def initialize_tesseract(self):
        """مقداردهی اولیه موتور Tesseract و تنظیمات آن."""
        try:
            # تنظیم مسیر اجرایی Tesseract
            if os.name == 'nt':  # Windows
                tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
                if os.path.exists(tesseract_path):
                    pytesseract.pytesseract.tesseract_cmd = tesseract_path
            
            # تنظیم زبان‌های پشتیبانی شده
            self.supported_languages = ['eng', 'fas']
            
            # بررسی نصب زبان فارسی
            self._check_persian_support()
            
        except Exception as e:
            logger.error(f"خطا در مقداردهی اولیه Tesseract: {str(e)}")
            raise

    def _check_persian_support(self):
        """بررسی نصب بودن پشتیبانی زبان فارسی."""
        try:
            supported = pytesseract.get_languages()
            if 'fas' not in supported:
                logger.warning("پشتیبانی زبان فارسی در Tesseract نصب نشده است")
                
        except Exception as e:
            logger.error(f"خطا در بررسی پشتیبانی زبان فارسی: {str(e)}")

    async def extract_text_from_image(
        self,
        image_data: bytes,
        language: str = 'fas'
    ) -> Dict[str, any]:
        """
        استخراج متن از تصویر.
        
        پارامترها:
            image_data: داده‌های باینری تصویر
            language: کد زبان برای تشخیص ('fas' برای فارسی، 'eng' برای انگلیسی)
            
        خروجی:
            دیکشنری حاوی متن استخراج شده و اطلاعات اضافی
        """
        try:
            # تبدیل داده‌های باینری به تصویر
            image = self._load_image(image_data)
            
            # پیش‌پردازش تصویر
            processed_image = self._preprocess_image(image)
            
            # استخراج متن
            extracted_text = pytesseract.image_to_string(
                processed_image,
                lang=language,
                config='--psm 3'  # حالت تشخیص خودکار صفحه
            )
            
            # استخراج اطلاعات ساختاری
            layout_info = self._extract_layout_info(processed_image, language)
            
            # شناسایی نواحی متنی
            text_regions = self._detect_text_regions(processed_image)
            
            return {
                'text': extracted_text.strip(),
                'layout': layout_info,
                'text_regions': text_regions,
                'language': language,
                'confidence': self._calculate_confidence(processed_image, language)
            }
            
        except Exception as e:
            logger.error(f"خطا در استخراج متن از تصویر: {str(e)}")
            raise

    def _load_image(self, image_data: bytes) -> np.ndarray:
        """تبدیل داده‌های باینری به تصویر."""
        try:
            # ذخیره موقت داده‌های تصویر
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(image_data)
                temp_path = temp_file.name
            
            # خواندن تصویر با OpenCV
            image = cv2.imread(temp_path)
            
            # پاک کردن فایل موقت
            os.unlink(temp_path)
            
            if image is None:
                raise ValueError("خطا در بارگذاری تصویر")
                
            return image
            
        except Exception as e:
            logger.error(f"خطا در بارگذاری تصویر: {str(e)}")
            raise

    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """پیش‌پردازش تصویر برای بهبود نتایج OCR."""
        try:
            # تبدیل به سطح خاکستری
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # حذف نویز
            denoised = cv2.fastNlMeansDenoising(gray)
            
            # افزایش کنتراست
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(denoised)
            
            # آستانه‌گذاری تطبیقی
            binary = cv2.adaptiveThreshold(
                enhanced,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11,
                2
            )
            
            return binary
            
        except Exception as e:
            logger.error(f"خطا در پیش‌پردازش تصویر: {str(e)}")
            raise

    def _extract_layout_info(
        self,
        image: np.ndarray,
        language: str
    ) -> Dict[str, any]:
        """استخراج اطلاعات ساختاری صفحه."""
        try:
            # استخراج داده‌های صفحه
            data = pytesseract.image_to_data(
                image,
                lang=language,
                output_type=pytesseract.Output.DICT
            )
            
            # استخراج پاراگراف‌ها
            paragraphs = self._group_text_blocks(data)
            
            # شناسایی جداول
            tables = self._detect_tables(image)
            
            return {
                'paragraphs': paragraphs,
                'tables': tables,
                'page_width': image.shape[1],
                'page_height': image.shape[0]
            }
            
        except Exception as e:
            logger.error(f"خطا در استخراج اطلاعات ساختاری: {str(e)}")
            return {}

    def _detect_text_regions(self, image: np.ndarray) -> List[Dict]:
        """شناسایی و استخراج نواحی متنی در تصویر."""
        try:
            # یافتن کانتورها
            contours, _ = cv2.findContours(
                image,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )
            
            regions = []
            for contour in contours:
                # محاسبه مستطیل محیطی
                x, y, w, h = cv2.boundingRect(contour)
                
                # فیلتر کردن نواحی خیلی کوچک
                if w * h < 100:  # آستانه حداقل اندازه
                    continue
                    
                regions.append({
                    'x': int(x),
                    'y': int(y),
                    'width': int(w),
                    'height': int(h),
                    'area': int(w * h)
                })
                
            return regions
            
        except Exception as e:
            logger.error(f"خطا در شناسایی نواحی متنی: {str(e)}")
            return []

    def _group_text_blocks(self, data: Dict) -> List[Dict]:
        """گروه‌بندی بلوک‌های متنی به پاراگراف‌ها."""
        paragraphs = []
        current_paragraph = {
            'text': [],
            'confidence': [],
            'bbox': None
        }
        
        last_block_num = -1
        for i in range(len(data['text'])):
            if data['text'][i].strip():
                block_num = data['block_num'][i]
                
                if block_num != last_block_num and last_block_num != -1:
                    # ذخیره پاراگراف قبلی
                    if current_paragraph['text']:
                        current_paragraph['text'] = ' '.join(current_paragraph['text'])
                        current_paragraph['confidence'] = sum(current_paragraph['confidence']) / len(current_paragraph['confidence'])
                        paragraphs.append(current_paragraph)
                        
                    # شروع پاراگراف جدید
                    current_paragraph = {
                        'text': [],
                        'confidence': [],
                        'bbox': None
                    }
                
                # افزودن متن به پاراگراف فعلی
                current_paragraph['text'].append(data['text'][i])
                current_paragraph['confidence'].append(float(data['conf'][i]))
                
                # به‌روزرسانی محدوده پاراگراف
                if current_paragraph['bbox'] is None:
                    current_paragraph['bbox'] = {
                        'x': data['left'][i],
                        'y': data['top'][i],
                        'width': data['width'][i],
                        'height': data['height'][i]
                    }
                else:
                    bbox = current_paragraph['bbox']
                    bbox['width'] = max(bbox['width'], data['left'][i] + data['width'][i] - bbox['x'])
                    bbox['height'] = max(bbox['height'], data['top'][i] + data['height'][i] - bbox['y'])
                
                last_block_num = block_num
        
        # افزودن آخرین پاراگراف
        if current_paragraph['text']:
            current_paragraph['text'] = ' '.join(current_paragraph['text'])
            current_paragraph['confidence'] = sum(current_paragraph['confidence']) / len(current_paragraph['confidence'])
            paragraphs.append(current_paragraph)
            
        return paragraphs

    def _detect_tables(self, image: np.ndarray) -> List[Dict]:
        """شناسایی جداول در تصویر."""
        try:
            # یافتن خطوط افقی و عمودی
            horizontal = self._detect_lines(image, True)
            vertical = self._detect_lines(image, False)
            
            # ترکیب خطوط برای یافتن تقاطع‌ها
            table_mask = cv2.bitwise_or(horizontal, vertical)
            
            # یافتن کانتورهای جداول
            contours, _ = cv2.findContours(
                table_mask,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )
            
            tables = []
            for contour in contours:
                # محاسبه مستطیل محیطی
                x, y, w, h = cv2.boundingRect(contour)
                
                # فیلتر کردن نواحی خیلی کوچک
                if w * h < 1000:  # آستانه حداقل اندازه برای جداول
                    continue
                    
                tables.append({
                    'x': int(x),
                    'y': int(y),
                    'width': int(w),
                    'height': int(h)
                })
                
            return tables
            
        except Exception as e:
            logger.error(f"خطا در شناسایی جداول: {str(e)}")
            return []

    def _detect_lines(self, image: np.ndarray, horizontal: bool) -> np.ndarray:
        """شناسایی خطوط افقی یا عمودی."""
        # ایجاد المان ساختاری
        if horizontal:
            kernel_length = image.shape[1] // 40
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_length, 1))
        else:
            kernel_length = image.shape[0] // 40
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel_length))
        
        # تشخیص خطوط
        eroded = cv2.erode(image, kernel)
        dilated = cv2.dilate(eroded, kernel)
        
        return dilated

    def _calculate_confidence(
        self,
        image: np.ndarray,
        language: str
    ) -> float:
        """محاسبه میزان اطمینان از نتایج OCR."""
        try:
            data = pytesseract.image_to_data(
                image,
                lang=language,
                output_type=pytesseract.Output.DICT
            )
            
            # محاسبه میانگین اطمینان برای کلمات معتبر
            confidences = [
                float(conf) for conf in data['conf']
                if conf != '-1'  # حذف کلمات نامعتبر
            ]
            
            if confidences:
                return sum(confidences) / len(confidences)
            return 0.0
            
        except Exception as e:
            logger.error(f"خطا در محاسبه میزان اطمینان: {str(e)}")
            return 0.0