[... کد قبلی حفظ می‌شود ...]

    def _calculate_glcm_features(self, image: np.ndarray) -> Dict[str, float]:
        """
        محاسبه ویژگی‌های GLCM برای تحلیل بافت
        """
        distances = [1]
        angles = [0, np.pi/4, np.pi/2, 3*np.pi/4]
        levels = 256
        symmetric = True
        normed = True
        
        glcm = greycomatrix(
            image,
            distances,
            angles,
            levels,
            symmetric=symmetric,
            normed=normed
        )
        
        return {
            'contrast': greycoprops(glcm, 'contrast')[0, 0],
            'homogeneity': greycoprops(glcm, 'homogeneity')[0, 0],
            'energy': greycoprops(glcm, 'energy')[0, 0],
            'correlation': greycoprops(glcm, 'correlation')[0, 0]
        }

    def _analyze_color_transitions(self, hsv_image: np.ndarray) -> float:
        """
        تحلیل گذارهای رنگی برای یافتن گذارهای غیرطبیعی
        """
        # محاسبه گرادیان رنگ در فضای HSV
        h_grad = cv2.Sobel(hsv_image[:,:,0], cv2.CV_32F, 1, 1)
        s_grad = cv2.Sobel(hsv_image[:,:,1], cv2.CV_32F, 1, 1)
        v_grad = cv2.Sobel(hsv_image[:,:,2], cv2.CV_32F, 1, 1)
        
        # محاسبه بزرگی گرادیان
        gradient_magnitude = np.sqrt(h_grad**2 + s_grad**2 + v_grad**2)
        
        # محاسبه هیستوگرام گرادیان
        hist = np.histogram(gradient_magnitude, bins=50)[0]
        hist = hist / np.sum(hist)
        
        # محاسبه انتروپی گرادیان
        entropy = -np.sum(hist * np.log2(hist + 1e-10))
        normalized_entropy = entropy / np.log2(len(hist))
        
        return normalized_entropy

    async def _analyze_shadows(self, image: np.ndarray) -> float:
        """
        تحلیل سایه‌ها برای یافتن ناسازگاری‌های فیزیکی
        """
        try:
            # تبدیل به سطح خاکستری
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # تشخیص نواحی تیره
            _, shadow_mask = cv2.threshold(
                gray,
                0,
                255,
                cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )
            
            # تحلیل جهت سایه‌ها
            edges = cv2.Canny(shadow_mask, 100, 200)
            lines = cv2.HoughLines(edges, 1, np.pi/180, 50)
            
            if lines is None:
                return 0.0
                
            # بررسی همسویی خطوط
            angles = []
            for rho, theta in lines[:, 0]:
                angle = theta * 180 / np.pi
                angles.append(angle)
                
            angles = np.array(angles)
            angle_diff = np.max(angles) - np.min(angles)
            
            # نرمال‌سازی اختلاف زاویه
            normalized_diff = angle_diff / 180.0
            
            return normalized_diff
            
        except Exception as e:
            logger.error(f"Error analyzing shadows: {str(e)}")
            return 0.0

    async def _analyze_reflections(self, image: np.ndarray) -> float:
        """
        تحلیل انعکاس‌ها برای یافتن ناسازگاری‌های فیزیکی
        """
        try:
            # تبدیل به سطح خاکستری
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # تشخیص نواحی روشن
            _, highlight_mask = cv2.threshold(
                gray,
                200,
                255,
                cv2.THRESH_BINARY
            )
            
            # یافتن نواحی متصل
            num_labels, labels = cv2.connectedComponents(highlight_mask)
            
            if num_labels < 2:
                return 0.0
                
            # تحلیل شکل و اندازه نواحی انعکاسی
            region_properties = []
            for label in range(1, num_labels):
                region = (labels == label).astype(np.uint8)
                contours, _ = cv2.findContours(
                    region,
                    cv2.RETR_EXTERNAL,
                    cv2.CHAIN_APPROX_SIMPLE
                )
                if contours:
                    area = cv2.contourArea(contours[0])
                    perimeter = cv2.arcLength(contours[0], True)
                    if perimeter > 0:
                        circularity = 4 * np.pi * area / (perimeter * perimeter)
                        region_properties.append(circularity)
                        
            if not region_properties:
                return 0.0
                
            # بررسی تنوع در شکل انعکاس‌ها
            std_circularity = np.std(region_properties)
            normalized_std = min(1.0, std_circularity / 0.5)
            
            return normalized_std
            
        except Exception as e:
            logger.error(f"Error analyzing reflections: {str(e)}")
            return 0.0

    async def _analyze_perspective(self, image: np.ndarray) -> float:
        """
        تحلیل پرسپکتیو برای یافتن ناسازگاری‌های فیزیکی
        """
        try:
            # تشخیص خطوط با استفاده از تبدیل هاف
            edges = cv2.Canny(image, 50, 150)
            lines = cv2.HoughLinesP(
                edges,
                1,
                np.pi/180,
                50,
                minLineLength=100,
                maxLineGap=10
            )
            
            if lines is None:
                return 0.0
                
            # محاسبه زوایای خطوط
            angles = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
                angles.append(angle)
                
            # بررسی نقاط گریز
            vanishing_points = self._find_vanishing_points(lines)
            
            if not vanishing_points:
                return 0.0
            
            # محاسبه فاصله بین نقاط گریز
            distances = []
            for i in range(len(vanishing_points)):
                for j in range(i + 1, len(vanishing_points)):
                    dist = np.linalg.norm(
                        np.array(vanishing_points[i]) - np.array(vanishing_points[j])
                    )
                    distances.append(dist)
                    
            if not distances:
                return 0.0
                
            # نرمال‌سازی فواصل
            max_distance = np.sqrt(image.shape[0]**2 + image.shape[1]**2)
            normalized_distances = [d / max_distance for d in distances]
            
            # محاسبه انحراف معیار فواصل نرمال شده
            std_distance = np.std(normalized_distances)
            
            return min(1.0, std_distance)
            
        except Exception as e:
            logger.error(f"Error analyzing perspective: {str(e)}")
            return 0.0

    def _find_vanishing_points(self, lines: np.ndarray) -> List[Tuple[float, float]]:
        """
        یافتن نقاط گریز از خطوط تصویر
        """
        vanishing_points = []
        for i in range(len(lines)):
            for j in range(i + 1, len(lines)):
                x1, y1, x2, y2 = lines[i][0]
                x3, y3, x4, y4 = lines[j][0]
                
                # محاسبه نقطه تقاطع
                denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
                
                if abs(denom) < 1e-10:
                    continue
                    
                px = (
                    (x1 * y2 - y1 * x2) * (x3 - x4) -
                    (x1 - x2) * (x3 * y4 - y3 * x4)
                ) / denom
                
                py = (
                    (x1 * y2 - y1 * x2) * (y3 - y4) -
                    (y1 - y2) * (x3 * y4 - y3 * x4)
                ) / denom
                
                vanishing_points.append((px, py))
                
        return vanishing_points

    def _detect_block_artifacts(self, image: np.ndarray) -> float:
        """
        تشخیص آرتیفکت‌های بلوکی در تصویر
        """
        # تبدیل به سطح خاکستری
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # محاسبه گرادیان
        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        
        # محاسبه بزرگی گرادیان
        gradient_magnitude = np.sqrt(gx * gx + gy * gy)
        
        # تشخیص لبه‌های عمودی و افقی
        _, binary = cv2.threshold(
            gradient_magnitude,
            np.mean(gradient_magnitude) * 2,
            255,
            cv2.THRESH_BINARY
        )
        
        # بررسی الگوهای منظم
        block_size = 8
        h, w = binary.shape
        block_counts = []
        
        for y in range(0, h - block_size, block_size):
            for x in range(0, w - block_size, block_size):
                block = binary[y:y+block_size, x:x+block_size]
                edge_count = np.sum(block > 0)
                block_counts.append(edge_count)
        
        if not block_counts:
            return 0.0
            
        # محاسبه انحراف معیار تعداد لبه‌ها
        std_edges = np.std(block_counts)
        mean_edges = np.mean(block_counts)
        
        if mean_edges == 0:
            return 0.0
            
        # نرمال‌سازی
        normalized_std = std_edges / mean_edges
        
        return min(1.0, normalized_std)

    def _detect_artificial_edges(self, image: np.ndarray) -> float:
        """
        تشخیص لبه‌های مصنوعی در تصویر
        """
        # تبدیل به سطح خاکستری
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # اعمال فیلتر Canny با آستانه‌های مختلف
        edges1 = cv2.Canny(gray, 50, 150)
        edges2 = cv2.Canny(gray, 100, 200)
        
        # محاسبه تفاوت بین دو تصویر لبه
        edge_diff = cv2.absdiff(edges1, edges2)
        
        # محاسبه نسبت پیکسل‌های متفاوت
        total_pixels = edge_diff.shape[0] * edge_diff.shape[1]
        diff_ratio = np.sum(edge_diff > 0) / total_pixels
        
        return min(1.0, diff_ratio * 5)  # ضریب 5 برای تقویت تفاوت‌های کوچک

    def __del__(self):
        """
        آزادسازی منابع هنگام حذف شیء
        """
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
