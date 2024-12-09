"""
سرویس تحلیل ویدیو.
این ماژول مسئول پردازش ویدیو، استخراج فریم‌های کلیدی و تحلیل محتواست.
"""

[... حفظ کد قبلی ...]

        Returns:
            لیست دیکشنری‌های حاوی اطلاعات فریم‌های کلیدی
        """
        cap = cv2.VideoCapture(video_path)
        frames = []
        
        try:
            # محاسبه فاصله فریم‌ها
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_interval = int(fps * self.settings['frame_interval'])
            
            frame_count = 0
            success = True
            prev_frame = None
            
            while success and len(frames) < self.settings['max_frames']:
                success, frame = cap.read()
                
                if not success:
                    break
                    
                if frame_count % frame_interval == 0:
                    # بررسی تفاوت با فریم قبلی
                    if prev_frame is not None:
                        diff = cv2.absdiff(
                            cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY),
                            cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
                        )
                        
                        if np.mean(diff) > self.settings['threshold'] * 255:
                            # ذخیره فریم به عنوان عکس
                            frame_path = os.path.join(
                                TEMP_DIR,
                                f'frame_{frame_count}.jpg'
                            )
                            cv2.imwrite(frame_path, frame)
                            
                            frames.append({
                                'path': frame_path,
                                'timestamp': frame_count / fps,
                                'frame_number': frame_count
                            })
                            
                    prev_frame = frame.copy()
                
                frame_count += 1
                
            return frames
            
        finally:
            cap.release()

    async def _analyze_frames(
        self,
        key_frames: List[Dict]
    ) -> List[Dict]:
        """
        تحلیل محتوای فریم‌های کلیدی.
        
        Args:
            key_frames: لیست فریم‌های کلیدی
            
        Returns:
            لیست نتایج تحلیل فریم‌ها
        """
        results = []
        
        for batch in self._batch_frames(key_frames, self.settings['batch_size']):
            # تبدیل تصاویر برای مدل
            images = [Image.open(frame['path']).convert('RGB') for frame in batch]
            inputs = [self.transform(img) for img in images]
            batch_tensor = torch.stack(inputs)
            
            with torch.no_grad():
                # تشخیص اشیا
                object_detections = self.object_detector(batch_tensor)
                
                # طبقه‌بندی تصاویر
                classifications = self.classifier(batch_tensor)
                
                for i, frame in enumerate(batch):
                    frame_result = {
                        'timestamp': frame['timestamp'],
                        'frame_number': frame['frame_number'],
                        'objects': self._process_detections(
                            object_detections.xyxy[i]
                        ),
                        'scene_type': self._process_classification(
                            classifications[i]
                        )
                    }
                    results.append(frame_result)
                    
        return results

    def _batch_frames(
        self,
        frames: List[Dict],
        batch_size: int
    ) -> List[List[Dict]]:
        """
        گروه‌بندی فریم‌ها برای پردازش دسته‌ای.
        
        Args:
            frames: لیست فریم‌ها
            batch_size: اندازه هر دسته
            
        Returns:
            لیست دسته‌های فریم
        """
        return [
            frames[i:i + batch_size]
            for i in range(0, len(frames), batch_size)
        ]

    def _process_detections(
        self,
        detections: torch.Tensor
    ) -> List[Dict]:
        """
        پردازش نتایج تشخیص اشیا.
        
        Args:
            detections: تنسور نتایج تشخیص
            
        Returns:
            لیست اشیا تشخیص داده شده
        """
        results = []
        
        for det in detections:
            x1, y1, x2, y2, conf, cls = det.tolist()
            
            if conf > 0.3:  # حداقل اطمینان
                results.append({
                    'label': self.object_detector.names[int(cls)],
                    'confidence': float(conf),
                    'bbox': [float(x) for x in [x1, y1, x2, y2]]
                })
                
        return results

    def _process_classification(
        self,
        logits: torch.Tensor
    ) -> Dict:
        """
        پردازش نتایج طبقه‌بندی تصویر.
        
        Args:
            logits: تنسور نتایج طبقه‌بندی
            
        Returns:
            دیکشنری نتیجه طبقه‌بندی
        """
        probs = torch.softmax(logits, dim=0)
        conf, cls = torch.max(probs, dim=0)
        
        return {
            'class_id': int(cls),
            'confidence': float(conf)
        }

    async def _detect_scenes(
        self,
        video_path: str
    ) -> List[Dict]:
        """
        تشخیص و جداسازی صحنه‌های ویدیو.
        
        Args:
            video_path: مسیر فایل ویدیو
            
        Returns:
            لیست صحنه‌های تشخیص داده شده
        """
        scenes = []
        cap = cv2.VideoCapture(video_path)
        
        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = 0
            scene_start = 0
            prev_frame = None
            
            while True:
                success, frame = cap.read()
                if not success:
                    break
                    
                if prev_frame is not None:
                    # محاسبه تفاوت بین فریم‌ها
                    diff = cv2.absdiff(
                        cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY),
                        cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
                    )
                    
                    mean_diff = np.mean(diff)
                    
                    # تشخیص تغییر صحنه
                    if mean_diff > self.settings['threshold'] * 255:
                        scene_duration = (frame_count - scene_start) / fps
                        
                        if scene_duration >= self.settings['min_scene_length']:
                            scenes.append({
                                'start_time': scene_start / fps,
                                'end_time': frame_count / fps,
                                'duration': scene_duration,
                                'start_frame': scene_start,
                                'end_frame': frame_count
                            })
                            
                        scene_start = frame_count
                        
                prev_frame = frame.copy()
                frame_count += 1
                
            # افزودن آخرین صحنه
            if frame_count - scene_start > 0:
                scenes.append({
                    'start_time': scene_start / fps,
                    'end_time': frame_count / fps,
                    'duration': (frame_count - scene_start) / fps,
                    'start_frame': scene_start,
                    'end_frame': frame_count
                })
                
            return scenes
            
        finally:
            cap.release()

    async def extract_thumbnail(
        self,
        video_path: str,
        time_offset: float = 0
    ) -> Optional[str]:
        """
        استخراج تصویر بندانگشتی از ویدیو.
        
        Args:
            video_path: مسیر فایل ویدیو
            time_offset: زمان موردنظر (ثانیه)
            
        Returns:
            مسیر فایل تصویر یا None
        """
        try:
            cap = cv2.VideoCapture(video_path)
            
            # تنظیم موقعیت زمانی
            cap.set(cv2.CAP_PROP_POS_MSEC, time_offset * 1000)
            
            success, frame = cap.read()
            if success:
                # ذخیره بندانگشتی
                thumb_path = os.path.join(
                    TEMP_DIR,
                    f'thumb_{Path(video_path).stem}.jpg'
                )
                
                # تغییر اندازه
                height = 480
                ratio = height / frame.shape[0]
                width = int(frame.shape[1] * ratio)
                frame = cv2.resize(frame, (width, height))
                
                cv2.imwrite(thumb_path, frame)
                return thumb_path
                
            return None
            
        except Exception as e:
            logger.error(f"خطا در استخراج بندانگشتی: {str(e)}")
            return None
            
        finally:
            cap.release()

    async def generate_preview(
        self,
        video_path: str,
        duration: float = 10.0
    ) -> Optional[str]:
        """
        ایجاد ویدیوی پیش‌نمایش.
        
        Args:
            video_path: مسیر فایل ویدیو
            duration: مدت پیش‌نمایش (ثانیه)
            
        Returns:
            مسیر فایل پیش‌نمایش یا None
        """
        try:
            # بررسی مدت ویدیو
            video_duration = get_media_duration(video_path)
            if not video_duration:
                return None
                
            # محاسبه زمان شروع
            start_time = min(
                video_duration / 4,  # از یک چهارم ویدیو
                max(0, video_duration - duration)
            )
            
            # ایجاد پیش‌نمایش
            preview_path = os.path.join(
                TEMP_DIR,
                f'preview_{Path(video_path).stem}.mp4'
            )
            
            import ffmpeg
            
            stream = ffmpeg.input(
                video_path,
                ss=start_time,
                t=duration
            )
            
            stream = ffmpeg.output(
                stream,
                preview_path,
                vcodec='libx264',
                acodec='aac',
                strict='experimental'
            )
            
            ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
            
            return preview_path
            
        except Exception as e:
            logger.error(f"خطا در ایجاد پیش‌نمایش: {str(e)}")
            return None