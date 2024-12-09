[... کد قبلی حفظ می‌شود ...]

    def _process_evidence(self, evidence: List[Dict]) -> List[Dict]:
        """
        پردازش و ساختاردهی شواهد
        
        Args:
            evidence: لیست شواهد خام
            
        Returns:
            شواهد پردازش شده
        """
        try:
            processed_evidence = []
            
            for item in evidence:
                processed_item = {
                    'type': item.get('type', 'unknown'),
                    'content': item.get('content', ''),
                    'source': item.get('source', ''),
                    'relevance': item.get('relevance', 0),
                    'verification_status': item.get('verification_status', 'unverified'),
                    'confidence_score': item.get('confidence_score', 0),
                    'extracted_at': item.get('extracted_at', datetime.now().isoformat()),
                    'key_findings': self._extract_key_findings(item),
                    'supporting_material': self._process_supporting_material(item)
                }
                
                processed_evidence.append(processed_item)
                
            # مرتب‌سازی بر اساس ارتباط و اطمینان
            processed_evidence.sort(
                key=lambda x: (x['relevance'], x['confidence_score']),
                reverse=True
            )
            
            return processed_evidence
            
        except Exception as e:
            logger.error(f"Error processing evidence: {str(e)}")
            return []

    def _extract_key_findings(self, evidence_item: Dict) -> List[str]:
        """
        استخراج نکات کلیدی از یک شاهد
        
        Args:
            evidence_item: دیکشنری شاهد
            
        Returns:
            لیست نکات کلیدی
        """
        try:
            findings = []
            content = evidence_item.get('content', '')
            
            # تقسیم به جملات
            sentences = content.split('.')
            
            for sentence in sentences:
                # شناسایی جملات کلیدی
                if any(indicator in sentence.lower() for indicator in [
                    'مهم',
                    'کلیدی',
                    'اصلی',
                    'نتیجه',
                    'یافته',
                    'نشان می‌دهد'
                ]):
                    findings.append(sentence.strip())
            
            return findings[:5]  # حداکثر 5 نکته کلیدی
            
        except Exception as e:
            logger.error(f"Error extracting key findings: {str(e)}")
            return []

    def _process_sources(self, sources: List[Dict]) -> List[Dict]:
        """
        پردازش و ارزیابی منابع
        
        Args:
            sources: لیست منابع
            
        Returns:
            منابع پردازش شده
        """
        try:
            processed_sources = []
            
            for source in sources:
                processed_source = {
                    'url': source.get('url', ''),
                    'title': source.get('title', ''),
                    'type': source.get('type', 'unknown'),
                    'credibility_score': source.get('credibility_score', 0),
                    'publication_date': source.get('publication_date'),
                    'authors': source.get('authors', []),
                    'domain_info': self._get_domain_info(source.get('url', '')),
                    'citations': self._process_citations(source.get('citations', [])),
                    'bias_assessment': self._assess_source_bias(source)
                }
                
                processed_sources.append(processed_source)
                
            # مرتب‌سازی بر اساس اعتبار
            processed_sources.sort(
                key=lambda x: x['credibility_score'],
                reverse=True
            )
            
            return processed_sources
            
        except Exception as e:
            logger.error(f"Error processing sources: {str(e)}")
            return []

    def _get_domain_info(self, url: str) -> Dict[str, any]:
        """
        دریافت اطلاعات دامنه یک منبع
        
        Args:
            url: آدرس منبع
            
        Returns:
            اطلاعات دامنه
        """
        try:
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            
            return {
                'domain': domain,
                'is_known': domain in self.known_domains,
                'category': self.domain_categories.get(domain, 'unknown'),
                'trust_score': self.domain_trust_scores.get(domain, 0.5)
            }
            
        except Exception as e:
            logger.error(f"Error getting domain info: {str(e)}")
            return {}

    def _assess_source_bias(self, source: Dict) -> Dict[str, any]:
        """
        ارزیابی سوگیری احتمالی منبع
        
        Args:
            source: اطلاعات منبع
            
        Returns:
            نتیجه ارزیابی سوگیری
        """
        try:
            bias_indicators = {
                'language': self._analyze_language_bias(source.get('content', '')),
                'perspective': self._analyze_perspective_bias(source),
                'sources_cited': self._analyze_citation_bias(source.get('citations', [])),
                'topic_coverage': self._analyze_coverage_bias(source)
            }
            
            # محاسبه امتیاز کلی سوگیری
            bias_score = sum(bias_indicators.values()) / len(bias_indicators)
            
            return {
                'indicators': bias_indicators,
                'overall_score': bias_score,
                'assessment': self._get_bias_assessment(bias_score)
            }
            
        except Exception as e:
            logger.error(f"Error assessing source bias: {str(e)}")
            return {}

    def _describe_methodology(self, results: Dict) -> Dict[str, any]:
        """
        توضیح روش‌شناسی بررسی
        
        Args:
            results: نتایج فکت‌چک
            
        Returns:
            توضیحات روش‌شناسی
        """
        try:
            methodology = {
                'overview': """
                این بررسی با استفاده از یک رویکرد چندوجهی انجام شده است که شامل:
                تحلیل محتوا، بررسی منابع، ارزیابی شواهد و تحلیل داده‌های پشتیبان است.
                """,
                
                'steps': [
                    {
                        'name': 'جمع‌آوری داده',
                        'description': 'جمع‌آوری اطلاعات از منابع مختلف و معتبر',
                        'tools_used': results.get('tools', []),
                        'duration': results.get('collection_duration')
                    },
                    {
                        'name': 'تحلیل محتوا',
                        'description': 'بررسی دقیق محتوا و استخراج ادعاهای اصلی',
                        'techniques': results.get('analysis_techniques', [])
                    },
                    {
                        'name': 'ارزیابی منابع',
                        'description': 'بررسی اعتبار و کیفیت منابع مورد استفاده',
                        'criteria': results.get('evaluation_criteria', [])
                    },
                    {
                        'name': 'نتیجه‌گیری',
                        'description': 'جمع‌بندی یافته‌ها و تعیین درجه صحت ادعا',
                        'confidence': results.get('confidence_score')
                    }
                ],
                
                'limitations': results.get('limitations', []),
                'assumptions': results.get('assumptions', []),
                'data_quality': self._assess_data_quality(results)
            }
            
            return methodology
            
        except Exception as e:
            logger.error(f"Error describing methodology: {str(e)}")
            return {}

    def _generate_statistical_analysis(self, results: Dict) -> Dict[str, any]:
        """
        تولید تحلیل‌های آماری
        
        Args:
            results: نتایج فکت‌چک
            
        Returns:
            تحلیل‌های آماری
        """
        try:
            if not results.get('data'):
                return {}
                
            analysis = {
                'sample_size': len(results['data']),
                'time_period': {
                    'start': min(results['data'], key=lambda x: x.get('date')).get('date'),
                    'end': max(results['data'], key=lambda x: x.get('date')).get('date')
                },
                'distributions': self._calculate_distributions(results['data']),
                'correlations': self._calculate_correlations(results['data']),
                'trends': self._analyze_trends(results['data']),
                'outliers': self._detect_outliers(results['data']),
                'confidence_intervals': self._calculate_confidence_intervals(results['data']),
                'statistical_tests': self._run_statistical_tests(results['data'])
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error generating statistical analysis: {str(e)}")
            return {}

    def _generate_technical_notes(self, results: Dict) -> List[Dict]:
        """
        تولید یادداشت‌های فنی
        
        Args:
            results: نتایج فکت‌چک
            
        Returns:
            لیست یادداشت‌های فنی
        """
        try:
            notes = []
            
            # نکات مربوط به جمع‌آوری داده
            if 'data_collection' in results:
                notes.append({
                    'category': 'data_collection',
                    'title': 'جمع‌آوری داده',
                    'content': self._format_data_collection_notes(results['data_collection'])
                })
                
            # نکات مربوط به پردازش
            if 'processing' in results:
                notes.append({
                    'category': 'processing',
                    'title': 'پردازش داده',
                    'content': self._format_processing_notes(results['processing'])
                })
                
            # نکات مربوط به تحلیل
            if 'analysis' in results:
                notes.append({
                    'category': 'analysis',
                    'title': 'تحلیل',
                    'content': self._format_analysis_notes(results['analysis'])
                })
                
            # محدودیت‌ها و چالش‌ها
            if 'limitations' in results:
                notes.append({
                    'category': 'limitations',
                    'title': 'محدودیت‌ها',
                    'content': self._format_limitation_notes(results['limitations'])
                })
            
            return notes
            
        except Exception as e:
            logger.error(f"Error generating technical notes: {str(e)}")
            return []

    def _generate_css(self, style: Dict) -> str:
        """
        تولید CSS برای گزارش
        
        Args:
            style: تنظیمات ظاهری
            
        Returns:
            کد CSS
        """
        try:
            css_template = self.template_env.get_template('report_style.css')
            return css_template.render(style=style)
            
        except Exception as e:
            logger.error(f"Error generating CSS: {str(e)}")
            return ""

    def _load_style_config(self) -> Dict[str, any]:
        """
        بارگذاری تنظیمات پیش‌فرض ظاهری
        
        Returns:
            تنظیمات ظاهری
        """
        try:
            style_path = os.path.join(REPORT_TEMPLATES_PATH, 'style_config.json')
            with open(style_path, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Error loading style config: {str(e)}")
            return {
                'fonts': {
                    'primary': 'Vazir',
                    'secondary': 'Arial'
                },
                'colors': {
                    'primary': '#1a73e8',
                    'secondary': '#34a853',
                    'text': '#202124',
                    'background': '#ffffff'
                },
                'spacing': {
                    'base': '1rem',
                    'large': '2rem'
                }
            }

    async def close(self):
        """
        آزادسازی منابع
        """
        # در صورت نیاز به بستن اتصالات یا آزادسازی منابع

    def __del__(self):
        """
        پاکسازی منابع هنگام حذف شیء
        """
        pass
