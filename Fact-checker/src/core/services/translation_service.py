"""
سرویس ترجمه متن و محتوا.
این ماژول مسئول ترجمه متون بین زبان‌های مختلف و مدیریت ترجمه‌هاست.
"""

[... حفظ کد قبلی ...]

            if target_lang not in self.supported_langs:
                raise ValueError(f"زبان مقصد {target_lang} پشتیبانی نمی‌شود")

            # تعیین روش ترجمه
            translation_pair = f"{source_lang}-{target_lang}"
            if use_local and translation_pair in self.models:
                # استفاده از مدل محلی
                translated_text, confidence = await self._translate_with_local_model(
                    text,
                    translation_pair
                )
            else:
                # استفاده از API ترجمه
                translated_text = await self._translate_with_api(
                    text,
                    source_lang,
                    target_lang
                )
                confidence = 0.8  # مقدار پیش‌فرض برای API

            return {
                'original_text': text,
                'translated_text': translated_text,
                'source_language': source_lang,
                'target_language': target_lang,
                'confidence': confidence,
                'word_count': len(text.split()),
                'translation_method': 'local' if use_local else 'api'
            }

        except Exception as e:
            logger.error(f"خطا در ترجمه متن: {str(e)}")
            raise

    async def _translate_with_local_model(
        self,
        text: str,
        translation_pair: str
    ) -> tuple[str, float]:
        """
        ترجمه با استفاده از مدل محلی.
        
        Args:
            text: متن ورودی
            translation_pair: جفت زبان‌ها
            
        Returns:
            تاپل شامل (متن ترجمه شده، میزان اطمینان)
        """
        try:
            # تبدیل متن به توکن
            tokenizer = self.tokenizers[translation_pair]
            model = self.models[translation_pair]
            
            encoded = tokenizer(text, return_tensors='pt', padding=True)
            
            # ترجمه متن
            with torch.no_grad():
                output = model.generate(
                    **encoded,
                    max_length=1024,
                    num_beams=5,
                    length_penalty=0.6,
                    early_stopping=True
                )
                
            # تبدیل خروجی به متن
            translated = tokenizer.decode(output[0], skip_special_tokens=True)
            
            # محاسبه میزان اطمینان
            confidence = self._calculate_translation_confidence(
                encoded,
                output,
                model
            )
            
            return translated, confidence
            
        except Exception as e:
            logger.error(f"خطا در ترجمه با مدل محلی: {str(e)}")
            raise

    async def _translate_with_api(
        self,
        text: str,
        source_lang: str,
        target_lang: str
    ) -> str:
        """
        ترجمه با استفاده از API.
        
        Args:
            text: متن ورودی
            source_lang: زبان مبدا
            target_lang: زبان مقصد
            
        Returns:
            متن ترجمه شده
        """
        try:
            translator = GoogleTranslator(
                source=source_lang,
                target=target_lang
            )
            return translator.translate(text)
            
        except Exception as e:
            logger.error(f"خطا در ترجمه با API: {str(e)}")
            raise

    def _calculate_translation_confidence(
        self,
        input_ids: torch.Tensor,
        output_ids: torch.Tensor,
        model: MarianMTModel
    ) -> float:
        """
        محاسبه میزان اطمینان از ترجمه.
        
        Args:
            input_ids: توکن‌های ورودی
            output_ids: توکن‌های خروجی
            model: مدل ترجمه
            
        Returns:
            امتیاز اطمینان بین 0 تا 1
        """
        try:
            # محاسبه احتمالات خروجی
            with torch.no_grad():
                outputs = model(
                    input_ids=input_ids['input_ids'],
                    decoder_input_ids=output_ids
                )
                
            logits = outputs.logits
            probs = torch.softmax(logits, dim=-1)
            
            # محاسبه میانگین احتمالات بیشینه
            max_probs = torch.max(probs, dim=-1).values
            confidence = float(torch.mean(max_probs))
            
            return confidence
            
        except Exception:
            return 0.7  # مقدار پیش‌فرض در صورت خطا

    async def detect_language(self, text: str) -> str:
        """
        تشخیص زبان متن.
        
        Args:
            text: متن ورودی
            
        Returns:
            کد زبان تشخیص داده شده
        """
        try:
            from langdetect import detect
            return detect(text)
            
        except Exception:
            return 'unknown'

    async def translate_batch(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str
    ) -> List[Dict]:
        """
        ترجمه گروهی متون.
        
        Args:
            texts: لیست متون
            source_lang: زبان مبدا
            target_lang: زبان مقصد
            
        Returns:
            لیست نتایج ترجمه
        """
        results = []
        for text in texts:
            try:
                result = await self.translate_text(
                    text,
                    source_lang,
                    target_lang
                )
                results.append(result)
            except Exception as e:
                results.append({
                    'original_text': text,
                    'error': str(e)
                })
                
        return results

    async def get_supported_languages(self) -> Dict[str, str]:
        """
        دریافت لیست زبان‌های پشتیبانی شده.
        
        Returns:
            دیکشنری کد و نام زبان‌ها
        """
        return self.supported_langs

    def _load_model(self, translation_pair: str):
        """
        بارگذاری مدل ترجمه برای یک جفت زبان.
        
        Args:
            translation_pair: جفت زبان‌ها
        """
        if translation_pair not in self.translation_pairs:
            raise ValueError(f"مدلی برای {translation_pair} وجود ندارد")
            
        model_name = self.translation_pairs[translation_pair]
        self.models[translation_pair] = MarianMTModel.from_pretrained(model_name)
        self.tokenizers[translation_pair] = MarianTokenizer.from_pretrained(model_name)

    def _unload_model(self, translation_pair: str):
        """
        آزادسازی حافظه مدل ترجمه.
        
        Args:
            translation_pair: جفت زبان‌ها
        """
        if translation_pair in self.models:
            del self.models[translation_pair]
            del self.tokenizers[translation_pair]
            torch.cuda.empty_cache()  # آزادسازی حافظه GPU