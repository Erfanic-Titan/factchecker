"""
سرویس تحلیل تصویر برای تشخیص دستکاری‌ها و تحلیل محتوا.
"""

[... حفظ کد قبلی ...]

                        suspicious_blocks.append({
                            'x': int(j),
                            'y': int(i),
                            'size': int(block_size),
                            'ac_energy': float(ac_energy)
                        })
                        
            # تحلیل توزیع ضرایب
            coeff_std = np.std([c['ac_energy'] for c in coefficients])
            coeff_mean = np.mean([c['ac_energy'] for c in coefficients])
            
            # محاسبه امتیاز دستکاری
            manipulation_score = min(
                1.0,
                len(suspicious_blocks) / ((h * w) / (block_size * block_size)) * 2
            )
            
            return {
                'coefficient_stats': {
                    'mean': float(coeff_mean),
                    'std': float(coeff_std)
                },
                'suspicious_blocks': suspicious_blocks,
                'manipulation_score': manipulation_score,
                'block_analysis': {
                    'total_blocks': len(coefficients),
                    'suspicious_blocks': len(suspicious_blocks)
                }
            }
            
        except Exception as e:
            logger.error(f"خطا در تحلیل DCT: {str(e)}")
            return {
                'error': str(e)
            }

    async def _analyze_compression(self, image: np.ndarray) -> Dict:
        """
        تحلیل نشانه‌های فشرده‌سازی مجدد.
        
        Args:
            image: آرایه تصویر
            
        Returns:
            دیکشنری نتایج تحلیل فشرده‌سازی
        """
        try:
            # ذخیره با کیفیت مشخص
            quality = self.settings['compression_quality']
            temp_path = os.path.join(TEMP_DIR, 'temp_compression.jpg')
            
            cv2.imwrite(
                temp_path,
                image,
                [cv2.IMWRITE_JPEG_QUALITY, quality]
            )
            
            # محاسبه اندازه فایل
            file_size = os.path.getsize(temp_path)
            os.remove(temp_path)
            
            # محاسبه نسبت فشرده‌سازی
            original_size = image.shape[0] * image.shape[1] * image.shape[2]
            compression_ratio = file_size / original_size
            
            # تحلیل بلوک‌های JPEG
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            
            block_artifacts = []
            block_size = 8  # اندازه بلوک JPEG
            
            for i in range(0, gray.shape[0] - block_size, block_size):
                for j in range(0, gray.shape[1] - block_size, block_size):
                    block = edges[i:i+block_size, j:j+block_size]
                    
                    # بررسی مرزهای بلوک
                    if np.sum(block[0, :]) > 0 or np.sum(block[-1, :]) > 0 or \
                       np.sum(block[:, 0]) > 0 or np.sum(block[:, -1]) > 0:
                        block_artifacts.append({
                            'x': int(j),
                            'y': int(i),
                            'size': int(block_size)
                        })
            
            # محاسبه امتیاز دستکاری
            artifact_density = len(block_artifacts) / ((gray.shape[0] * gray.shape[1]) / (block_size * block_size))
            manipulation_score = min(1.0, artifact_density * 2)
            
            return {
                'compression_ratio': float(compression_ratio),
                'block_artifacts': block_artifacts,
                'artifact_density': float(artifact_density),
                'manipulation_score': manipulation_score
            }
            
        except Exception as e:
            logger.error(f"خطا در تحلیل فشرده‌سازی: {str(e)}")
            return {
                'error': str(e)
            }

    async def _detect_deepfake(self, image: np.ndarray) -> float:
        """
        تشخیص تصاویر دیپ‌فیک.
        
        Args:
            image: آرایه تصویر
            
        Returns:
            احتمال دیپ‌فیک بودن
        """
        try:
            # تبدیل و نرمال‌سازی تصویر
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            input_tensor = self.transform(pil_image).unsqueeze(0)
            
            # پیش‌بینی مدل
            with torch.no_grad():
                output = self.deepfake_detector(input_tensor)
                probability = torch.sigmoid(output).item()
                
            return float(probability)
            
        except Exception as e:
            logger.error(f"خطا در تشخیص دیپ‌فیک: {str(e)}")
            return 0.0

    async def _classify_manipulation(self, image: np.ndarray) -> Dict:
        """
        طبقه‌بندی نوع دستکاری تصویر.
        
        Args:
            image: آرایه تصویر
            
        Returns:
            دیکشنری نوع دستکاری و احتمال‌ها
        """
        try:
            # کلاس‌های دستکاری
            manipulation_types = [
                'splice',  # ترکیب تصاویر
                'copy-move',  # کپی و جابجایی
                'removal',  # حذف اجزا
                'enhancement'  # بهبود و فیلتر
            ]
            
            # تبدیل تصویر
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            input_tensor = self.transform(pil_image).unsqueeze(0)
            
            # پیش‌بینی مدل
            with torch.no_grad():
                output = self.manipulation_classifier(input_tensor)
                probabilities = torch.softmax(output, dim=1)[0]
                
            # تبدیل به دیکشنری
            predictions = {
                manipulation_types[i]: float(probabilities[i])
                for i in range(len(manipulation_types))
            }
            
            # نوع غالب دستکاری
            main_type = manipulation_types[torch.argmax(probabilities).item()]
            
            return {
                'main_type': main_type,
                'probabilities': predictions
            }
            
        except Exception as e:
            logger.error(f"خطا در طبقه‌بندی دستکاری: {str(e)}")
            return {
                'error': str(e)
            }

    async def _calculate_image_hash(self, image: Image) -> str:
        """
        محاسبه هش تصویر برای مقایسه.
        
        Args:
            image: آبجکت تصویر PIL
            
        Returns:
            هش تصویر
        """
        try:
            # محاسبه انواع هش
            hashes = {
                'average': str(imagehash.average_hash(image)),
                'perceptual': str(imagehash.phash(image)),
                'difference': str(imagehash.dhash(image)),
                'wavelet': str(imagehash.whash(image))
            }
            
            return json.dumps(hashes)
            
        except Exception as e:
            logger.error(f"خطا در محاسبه هش تصویر: {str(e)}")
            return ""

    def _combine_evidence(self, scores: Dict[str, float]) -> float:
        """
        ترکیب نتایج تحلیل‌های مختلف.
        
        Args:
            scores: دیکشنری امتیازات
            
        Returns:
            امتیاز نهایی دستکاری
        """
        # وزن‌های هر روش
        weights = {
            'noise': 0.2,
            'ela': 0.25,
            'dct': 0.2,
            'compression': 0.15,
            'deepfake': 0.2
        }
        
        # میانگین وزن‌دار
        total_score = sum(
            score * weights.get(method, 0)
            for method, score in scores.items()
        )
        
        return min(1.0, max(0.0, total_score))