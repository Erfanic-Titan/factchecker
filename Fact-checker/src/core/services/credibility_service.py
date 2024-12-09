"""
سرویس تشخیص و ارزیابی اعتبار منابع.
"""

[... حفظ کد قبلی ...]

                    if similarity > 0.6:
                        related.append({
                            'domain': source['domain'],
                            'relation_type': 'similar_content',
                            'relation_strength': similarity
                        })
            
            # بررسی الگوهای انتشار مشابه
            publish_patterns = await self._analyze_publishing_patterns(domain)
            
            for source_domain, pattern_similarity in publish_patterns.items():
                if pattern_similarity > 0.7:
                    related.append({
                        'domain': source_domain,
                        'relation_type': 'similar_patterns',
                        'relation_strength': pattern_similarity
                    })
            
            return related
            
        except Exception as e:
            logger.error(f"خطا در یافتن منابع مرتبط: {str(e)}")
            return []

    async def _analyze_publishing_patterns(
        self,
        domain: str
    ) -> Dict[str, float]:
        """
        تحلیل الگوهای انتشار محتوا.
        
        این تابع الگوهای زمانی و موضوعی انتشار محتوا را تحلیل می‌کند
        و با سایر منابع مقایسه می‌کند.

        Args:
            domain: دامنه مورد نظر

        Returns:
            دیکشنری شباهت الگو برای هر دامنه
        """
        try:
            # دریافت آمار انتشار
            stats = await self._get_publishing_stats(domain)
            
            if not stats:
                return {}
                
            similarities = {}
            
            # مقایسه با سایر منابع
            for source in self.trusted_sources.get('news', []):
                other_domain = source['domain']
                if other_domain != domain:
                    other_stats = await self._get_publishing_stats(other_domain)
                    
                    if other_stats:
                        # محاسبه شباهت زمانی
                        time_similarity = self._compare_time_patterns(
                            stats['time_distribution'],
                            other_stats['time_distribution']
                        )
                        
                        # محاسبه شباهت موضوعی
                        topic_similarity = self._compare_topic_patterns(
                            stats['topic_distribution'],
                            other_stats['topic_distribution']
                        )
                        
                        # ترکیب معیارها
                        similarities[other_domain] = (
                            time_similarity * 0.4 +
                            topic_similarity * 0.6
                        )
            
            return similarities
            
        except Exception as e:
            logger.error(f"خطا در تحلیل الگوهای انتشار: {str(e)}")
            return {}

    async def _get_publishing_stats(self, domain: str) -> Optional[Dict]:
        """
        دریافت آمار انتشار برای یک دامنه.
        
        Args:
            domain: دامنه مورد نظر
            
        Returns:
            دیکشنری آمار انتشار یا None
        """
        try:
            # دریافت مطالب اخیر
            articles = await self.fact_repository.get_recent_articles(
                domain,
                days=30
            )
            
            if not articles:
                return None
                
            # توزیع زمانی
            time_dist = {
                'hourly': [0] * 24,  # ساعات شبانه‌روز
                'daily': [0] * 7     # روزهای هفته
            }
            
            # توزیع موضوعی
            topic_dist = {}
            
            for article in articles:
                # آمار زمانی
                published_at = article['published_at']
                time_dist['hourly'][published_at.hour] += 1
                time_dist['daily'][published_at.weekday()] += 1
                
                # آمار موضوعی
                for topic in article['topics']:
                    topic_dist[topic] = topic_dist.get(topic, 0) + 1
            
            # نرمال‌سازی توزیع‌ها
            total_articles = len(articles)
            
            time_dist['hourly'] = [
                count / total_articles
                for count in time_dist['hourly']
            ]
            
            time_dist['daily'] = [
                count / total_articles
                for count in time_dist['daily']
            ]
            
            topic_dist = {
                topic: count / total_articles
                for topic, count in topic_dist.items()
            }
            
            return {
                'time_distribution': time_dist,
                'topic_distribution': topic_dist
            }
            
        except Exception as e:
            logger.error(f"خطا در دریافت آمار انتشار: {str(e)}")
            return None

    def _compare_time_patterns(
        self,
        pattern1: Dict,
        pattern2: Dict
    ) -> float:
        """
        مقایسه الگوهای زمانی انتشار.
        
        Args:
            pattern1: الگوی زمانی اول
            pattern2: الگوی زمانی دوم
            
        Returns:
            میزان شباهت بین 0 تا 1
        """
        try:
            # محاسبه فاصله کسینوسی برای هر توزیع
            hourly_sim = self._cosine_similarity(
                pattern1['hourly'],
                pattern2['hourly']
            )
            
            daily_sim = self._cosine_similarity(
                pattern1['daily'],
                pattern2['daily']
            )
            
            # میانگین وزن‌دار
            return hourly_sim * 0.7 + daily_sim * 0.3
            
        except Exception:
            return 0.0

    def _compare_topic_patterns(
        self,
        dist1: Dict[str, float],
        dist2: Dict[str, float]
    ) -> float:
        """
        مقایسه توزیع موضوعی.
        
        Args:
            dist1: توزیع موضوعی اول
            dist2: توزیع موضوعی دوم
            
        Returns:
            میزان شباهت بین 0 تا 1
        """
        try:
            # تبدیل به بردار برای موضوعات یکسان
            all_topics = sorted(set(dist1.keys()) | set(dist2.keys()))
            
            vec1 = [dist1.get(topic, 0.0) for topic in all_topics]
            vec2 = [dist2.get(topic, 0.0) for topic in all_topics]
            
            return self._cosine_similarity(vec1, vec2)
            
        except Exception:
            return 0.0

    def _cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float]
    ) -> float:
        """
        محاسبه شباهت کسینوسی دو بردار.
        
        Args:
            vec1: بردار اول
            vec2: بردار دوم
            
        Returns:
            شباهت کسینوسی
        """
        try:
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            norm1 = sum(x * x for x in vec1) ** 0.5
            norm2 = sum(x * x for x in vec2) ** 0.5
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
                
            return dot_product / (norm1 * norm2)
            
        except Exception:
            return 0.0

    def _analyze_network_structure(self, network: Dict) -> Dict:
        """
        تحلیل ساختار شبکه منابع.
        
        Args:
            network: دیکشنری شبکه منابع
            
        Returns:
            دیکشنری نتایج تحلیل
        """
        try:
            # محاسبه شاخص‌های مرکزیت
            centrality = self._calculate_centrality(network)
            
            # شناسایی خوشه‌ها
            communities = self._detect_communities(network)
            
            # تحلیل جریان اطلاعات
            information_flow = self._analyze_information_flow(network)
            
            return {
                'centrality_metrics': centrality,
                'communities': communities,
                'information_flow': information_flow
            }
            
        except Exception as e:
            logger.error(f"خطا در تحلیل ساختار شبکه: {str(e)}")
            return {}

    async def _establish_baseline_metrics(self, domain: str) -> Dict:
        """
        ایجاد معیارهای پایه برای پایش منبع.
        
        Args:
            domain: دامنه منبع
            
        Returns:
            دیکشنری معیارهای پایه
        """
        try:
            metrics = {}
            
            # بررسی محتوای معمول
            recent_articles = await self.fact_repository.get_recent_articles(
                domain,
                days=7
            )
            
            if recent_articles:
                # الگوهای نگارشی
                metrics['avg_length'] = np.mean([
                    len(article['content'])
                    for article in recent_articles
                ])
                
                metrics['common_phrases'] = self._extract_common_phrases(
                    [article['content'] for article in recent_articles]
                )
                
                # سبک نگارش
                metrics['writing_style'] = await self._analyze_writing_style(
                    [article['content'] for article in recent_articles]
                )
                
                # الگوی انتشار
                metrics['publishing_pattern'] = self._extract_publishing_pattern(
                    [article['published_at'] for article in recent_articles]
                )
            
            # آمار اعتبارسنجی
            fact_checks = await self.fact_repository.get_source_fact_checks(
                domain,
                days=30
            )
            
            if fact_checks:
                metrics['credibility_stats'] = {
                    'avg_score': np.mean([
                        fc['credibility_score']
                        for fc in fact_checks
                    ]),
                    'score_distribution': np.histogram(
                        [fc['credibility_score'] for fc in fact_checks],
                        bins=10
                    )[0].tolist()
                }
            
            return metrics
            
        except Exception as e:
            logger.error(f"خطا در ایجاد معیارهای پایه: {str(e)}")
            return {}