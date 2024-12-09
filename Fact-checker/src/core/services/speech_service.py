"""
سرویس تشخیص گفتار و تبدیل صوت به متن.
این ماژول مسئول پردازش فایل‌های صوتی و استخراج متن از آنهاست.
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple
import speech_recognition as sr
import numpy as np
from pydub import AudioSegment
import logging
import wave
import contextlib
import json

from config.config import TEMP_DIR
from ...utils.helpers import get_logger

logger = get_logger(__name__)

class SpeechService:
    """کلاس اصلی برای تشخیص گفتار و پردازش صوت."""

    def __init__(self):
        """مقداردهی اولیه سرویس تشخیص گفتار."""
        self.recognizer = sr.Recognizer()
        
        # تنظیمات پیش‌فرض
        self.settings = {
            'language': 'fa-IR',
            'energy_threshold': 300,
            'dynamic_energy_threshold': True,
            'pause_threshold': 0.8,
            'phrase_threshold': 0.3,
            'non_speaking_duration': 0.5
        }
        
        # پشتیبانی از فرمت‌های مختلف
        self.supported_formats = {'.wav', '.mp3', '.ogg', '.flac', '.m4a'}

    async def transcribe_audio(
        self,
        audio_data: bytes,
        original_filename: str,
        language: Optional[str] = None
    ) -> Dict:
        """
        تبدیل فایل صوتی به متن.
        
        Args:
            audio_data: داده‌های باینری فایل صوتی
            original_filename: نام اصلی فایل
            language: کد زبان
            
        Returns:
            دیکشنری حاوی نتایج تشخیص
        """
        try:
            # بررسی فرمت فایل
            file_ext = Path(original_filename).suffix.lower()
            if file_ext not in self.supported_formats:
                raise ValueError(f"فرمت {file_ext} پشتیبانی نمی‌شود")

            # تبدیل به WAV برای پردازش
            audio_path = await self._convert_to_wav(audio_data, file_ext)
            
            # تشخیص گفتار
            text, confidence = await self._perform_recognition(
                audio_path,
                language or self.settings['language']
            )
            
            # تحلیل صوت
            audio_info = await self._analyze_audio(audio_path)
            
            # پاکسازی فایل موقت
            os.unlink(audio_path)
            
            return {
                'text': text,
                'confidence': confidence,
                'language': language or self.settings['language'],
                'word_count': len(text.split()),
                'duration': audio_info['duration'],
                'channels': audio_info['channels'],
                'sample_rate': audio_info['sample_rate'],
                'speakers': audio_info['speakers'],
                'noise_level': audio_info['noise_level']
            }

        except Exception as e:
            logger.error(f"خطا در تشخیص گفتار: {str(e)}")
            raise

    async def _convert_to_wav(
        self,
        audio_data: bytes,
        source_format: str
    ) -> str:
        """
        تبدیل فایل صوتی به فرمت WAV.
        
        Args:
            audio_data: داده‌های باینری فایل
            source_format: فرمت اصلی
            
        Returns:
            مسیر فایل WAV
        """
        # ذخیره فایل ورودی
        temp_input = tempfile.NamedTemporaryFile(
            suffix=source_format,
            delete=False
        ).name
        with open(temp_input, 'wb') as f:
            f.write(audio_data)

        # تبدیل به WAV
        temp_output = tempfile.NamedTemporaryFile(
            suffix='.wav',
            delete=False
        ).name

        audio = AudioSegment.from_file(temp_input)
        audio.export(
            temp_output,
            format='wav',
            parameters=['-ac', '1', '-ar', '16000']  # مونو، 16KHz
        )

        # پاکسازی فایل ورودی
        os.unlink(temp_input)

        return temp_output

    async def _perform_recognition(
        self,
        audio_path: str,
        language: str
    ) -> Tuple[str, float]:
        """
        انجام عملیات تشخیص گفتار.
        
        Args:
            audio_path: مسیر فایل صوتی
            language: کد زبان
            
        Returns:
            تاپل شامل (متن تشخیص داده شده, میزان اطمینان)
        """
        with sr.AudioFile(audio_path) as source:
            # تنظیم پارامترها
            self.recognizer.energy_threshold = self.settings['energy_threshold']
            self.recognizer.dynamic_energy_threshold = self.settings['dynamic_energy_threshold']
            self.recognizer.pause_threshold = self.settings['pause_threshold']
            self.recognizer.phrase_threshold = self.settings['phrase_threshold']
            self.recognizer.non_speaking_duration = self.settings['non_speaking_duration']
            
            # ضبط صدا
            audio = self.recognizer.record(source)
            
            # تشخیص با موتورهای مختلف
            results = []
            confidence_scores = []
            
            # Google Speech Recognition
            try:
                text = self.recognizer.recognize_google(
                    audio,
                    language=language,
                    show_all=True
                )
                if text and 'alternative' in text:
                    results.append(text['alternative'][0]['transcript'])
                    confidence_scores.append(
                        text['alternative'][0].get('confidence', 0.8)
                    )
            except Exception as e:
                logger.warning(f"خطا در Google Speech: {str(e)}")
            
            # Vosk (آفلاین)
            try:
                from vosk import Model, KaldiRecognizer
                
                model_path = os.path.join('models', language)
                if os.path.exists(model_path):
                    model = Model(model_path)
                    rec = KaldiRecognizer(model, 16000)
                    
                    with wave.open(audio_path) as wf:
                        while True:
                            data = wf.readframes(4000)
                            if len(data) == 0:
                                break
                            if rec.AcceptWaveform(data):
                                result = json.loads(rec.Result())
                                if result.get('text'):
                                    results.append(result['text'])
                                    confidence_scores.append(0.7)  # امتیاز پیش‌فرض
            except Exception as e:
                logger.warning(f"خطا در Vosk: {str(e)}")
            
            # انتخاب بهترین نتیجه
            if not results:
                raise ValueError("هیچ متنی تشخیص داده نشد")
                
            best_index = np.argmax(confidence_scores)
            return results[best_index], confidence_scores[best_index]

    async def _analyze_audio(self, audio_path: str) -> Dict:
        """
        تحلیل ویژگی‌های فایل صوتی.
        
        Args:
            audio_path: مسیر فایل صوتی
            
        Returns:
            دیکشنری حاوی ویژگی‌های صوتی
        """
        audio = AudioSegment.from_wav(audio_path)
        
        # اطلاعات پایه
        info = {
            'duration': len(audio) / 1000,  # تبدیل به ثانیه
            'channels': audio.channels,
            'sample_rate': audio.frame_rate,
            'sample_width': audio.sample_width
        }
        
        # تحلیل سطح نویز
        samples = np.array(audio.get_array_of_samples())
        noise_level = np.percentile(np.abs(samples), 10)
        info['noise_level'] = float(noise_level)
        
        # تشخیص تعداد گوینده‌ها
        info['speakers'] = await self._detect_speakers(audio_path)
        
        return info

    async def _detect_speakers(self, audio_path: str) -> int:
        """
        تشخیص تعداد گوینده‌ها در فایل صوتی.
        
        Args:
            audio_path: مسیر فایل صوتی
            
        Returns:
            تعداد گوینده‌ها
        """
        try:
            # استفاده از کتابخانه speechbrain
            from speechbrain.pretrained import SpeakerRecognition
            
            # بارگذاری مدل
            speaker_model = SpeakerRecognition.from_hparams(
                source="speechbrain/spkrec-ecapa-voxceleb",
                savedir="models/speaker_recognition"
            )
            
            # تشخیص گوینده‌ها
            embeddings = speaker_model.encode_batch(audio_path)
            
            # خوشه‌بندی برای تشخیص تعداد گوینده‌ها
            from sklearn.cluster import DBSCAN
            clustering = DBSCAN(eps=0.5, min_samples=2).fit(embeddings)
            
            n_speakers = len(set(clustering.labels_)) - (1 if -1 in clustering.labels_ else 0)
            return max(1, n_speakers)  # حداقل یک گوینده
            
        except Exception as e:
            logger.warning(f"خطا در تشخیص گوینده‌ها: {str(e)}")
            return 1  # مقدار پیش‌فرض