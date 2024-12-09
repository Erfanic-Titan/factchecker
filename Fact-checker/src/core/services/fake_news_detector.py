"""
سرویس تشخیص اخبار جعلی با ترکیب چندین روش هوشمند.
"""

[... حفظ کد قبلی تا قسمت __init__ ...]

    def __init__(self, nlp_service: NLPService):
        """
        مقداردهی اولیه کلاس تشخیص اخبار جعلی.
        
        این کلاس همه سرویس‌های مورد نیاز برای تشخیص اخبار جعلی را یکپارچه می‌کند.
        از جمله تحلیل متن، تشخیص دستکاری، بررسی منابع و راستی‌آزمایی گوگل.
        
        Args:
            nlp_service: سرویس پردازش زبان طبیعی
        """
        self.nlp_service = nlp_service
        
        # اضافه کردن سرویس Google Fact Check
        self.google_factcheck = GoogleFactCheckService()
        
        # بارگذاری مدل‌ها و سایر مقداردهی‌های اولیه
        self._load_models()
        
        # تنظیم وزن‌های ترکیب نتایج
        self.result_weights = {
            'bert': 0.25,
            'roberta': 0.15,
            'albert': 0.15,
            'google_factcheck': 0.20,  # اضافه کردن وزن برای نتایج گوگل
            'bias': 0.1,
            'sentiment': 0.05,
            'style': 0.05,
            'references': 0.05
        }

    async def analyze_text(
        self,
        text: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        تحلیل کامل متن و تشخیص احتمال جعلی بودن.
        
        این متد نتایج همه روش‌های تشخیص را با هم ترکیب می‌کند تا به یک نتیجه
        دقیق‌تر و قابل اعتمادتر برسد.
        
        Args:
            text: متن ورودی
            metadata: اطلاعات تکمیلی
            
        Returns:
            دیکشنری حاوی نتایج تحلیل و احتمال جعلی بودن
        """
        try:
            # تمیزسازی و نرمال‌سازی متن
            clean_content = clean_text(text)
            
            # تحلیل‌های موازی
            bert_result, roberta_result, albert_result, \
            factcheck_result, bias_result, sentiment_result, \
            style_result, references_result = await asyncio.gather(
                self._analyze_with_bert(clean_content),
                self._analyze_with_roberta(clean_content),
                self._analyze_with_albert(clean_content),
                self.google_factcheck.check_claim(clean_content),  # اضافه کردن راستی‌آزمایی گوگل
                self._analyze_bias(clean_content),
                self._analyze_sentiment(clean_content),
                self._analyze_writing_style(clean_content),
                self._analyze_references(clean_content, metadata)
            )
            
            # محاسبه احتمال نهایی با در نظر گرفتن نتایج گوگل
            fake_probability = (
                bert_result['fake_probability'] * self.result_weights['bert'] +
                roberta_result['fake_probability'] * self.result_weights['roberta'] +
                albert_result['fake_probability'] * self.result_weights['albert'] +
                (1 - factcheck_result.get('verification_stats', {}).get('credibility_score', 0.5)) * 
                    self.result_weights['google_factcheck'] +
                bias_result['bias_score'] * self.result_weights['bias'] +
                sentiment_result['extreme_sentiment'] * self.result_weights['sentiment'] +
                style_result['suspicious_score'] * self.result_weights['style'] +
                (1 - references_result['credibility']) * self.result_weights['references']
            )
            
            # تصمیم‌گیری نهایی
            is_fake = fake_probability >= self.thresholds['fake_probability']
            
            return {
                'is_fake': is_fake,
                'fake_probability': float(fake_probability),
                'confidence': self._calculate_confidence(
                    [bert_result, roberta_result, albert_result, factcheck_result]
                ),
                'analysis_details': {
                    'bert_analysis': bert_result,
                    'roberta_analysis': roberta_result,
                    'albert_analysis': albert_result,
                    'google_factcheck': factcheck_result,  # اضافه کردن نتایج گوگل
                    'bias_analysis': bias_result,
                    'sentiment_analysis': sentiment_result,
                    'style_analysis': style_result,
                    'references_analysis': references_result
                },
                'explanations': self._generate_explanations(
                    is_fake,
                    fake_probability,
                    [bert_result, roberta_result, albert_result, factcheck_result]
                ),
                'recommendations': self._generate_recommendations(
                    [bert_result, roberta_result, albert_result, factcheck_result]
                ),
                'analyzed_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"خطا در تحلیل متن: {str(e)}")
            raise