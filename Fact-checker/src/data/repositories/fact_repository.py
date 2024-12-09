"""
ریپوزیتوری اصلی برای دسترسی به داده‌های راستی‌آزمایی.
این ماژول مسئول تمام تعاملات با پایگاه داده است.
"""

[... حفظ کد قبلی ...]

                user_id=user_id,
                fact_check_id=fact_check_id,
                report_type=report_type,
                description=description
            )
            
            self.session.add(report)
            self.session.commit()
            
            logger.info(f"Saved report with id {report.id}")
            return report.id
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error in save_report: {str(e)}")
            raise

    async def get_user_statistics(self, user_id: int) -> Dict:
        """
        دریافت آمار فعالیت‌های کاربر.
        
        Args:
            user_id: شناسه کاربر
            
        Returns:
            دیکشنری حاوی آمار کاربر
        """
        try:
            # تعداد کل بررسی‌ها
            total_claims = self.session.query(func.count(Claim.id)).filter(
                Claim.user_id == user_id
            ).scalar()
            
            # آمار وضعیت‌های مختلف
            status_counts = self.session.query(
                FactCheck.verification_status,
                func.count(FactCheck.id)
            ).join(Claim).filter(
                Claim.user_id == user_id
            ).group_by(
                FactCheck.verification_status
            ).all()
            
            # تبدیل به دیکشنری
            status_stats = {
                status: count
                for status, count in status_counts
            }
            
            # زمان عضویت و آخرین فعالیت
            user = self.session.query(User).get(user_id)
            join_date = user.created_at if user else None
            
            last_activity = self.session.query(
                func.max(Claim.created_at)
            ).filter(
                Claim.user_id == user_id
            ).scalar()
            
            return {
                'total_checks': total_claims or 0,
                'verified_count': status_stats.get('VERIFIED', 0),
                'false_count': status_stats.get('FALSE', 0),
                'partially_true_count': status_stats.get('PARTIALLY_TRUE', 0),
                'unverified_count': status_stats.get('UNVERIFIED', 0),
                'join_date': join_date.isoformat() if join_date else None,
                'last_activity': last_activity.isoformat() if last_activity else None
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Error in get_user_statistics: {str(e)}")
            return {}

    async def get_user_settings(self, user_id: int) -> Dict:
        """
        دریافت تنظیمات کاربر.
        
        Args:
            user_id: شناسه کاربر
            
        Returns:
            دیکشنری حاوی تنظیمات کاربر
        """
        try:
            user = self.session.query(User).get(user_id)
            if not user:
                return {}
                
            return user.settings or {
                'language': user.language_code,
                'report_format': 'text',
                'notifications': True
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Error in get_user_settings: {str(e)}")
            return {}

    async def save_user_settings(
        self,
        user_id: int,
        settings: Dict
    ) -> bool:
        """
        ذخیره تنظیمات کاربر.
        
        Args:
            user_id: شناسه کاربر
            settings: دیکشنری تنظیمات
            
        Returns:
            نتیجه عملیات
        """
        try:
            user = self.session.query(User).get(user_id)
            if not user:
                return False
                
            user.settings = settings
            if settings.get('language'):
                user.language_code = settings['language']
                
            self.session.commit()
            logger.info(f"Updated settings for user {user_id}")
            return True
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error in save_user_settings: {str(e)}")
            return False

    async def get_trending_claims(
        self,
        days: int = 7,
        limit: int = 10
    ) -> List[Dict]:
        """
        دریافت ادعاهای پربازدید.
        
        Args:
            days: تعداد روزهای اخیر
            limit: حداکثر تعداد نتایج
            
        Returns:
            لیست ادعاهای پربازدید
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            trending_claims = self.session.query(
                Claim,
                func.count(Feedback.id).label('feedback_count'),
                func.count(Comment.id).label('comment_count')
            ).outerjoin(
                Feedback,
                Comment
            ).filter(
                Claim.created_at >= start_date
            ).group_by(
                Claim.id
            ).order_by(
                desc('feedback_count'),
                desc('comment_count')
            ).limit(limit).all()
            
            results = []
            for claim, feedback_count, comment_count in trending_claims:
                fact_check = claim.fact_checks[0] if claim.fact_checks else None
                
                results.append({
                    'id': claim.id,
                    'claim_text': claim.claim_text,
                    'created_at': claim.created_at.isoformat(),
                    'feedback_count': feedback_count,
                    'comment_count': comment_count,
                    'verification_status': fact_check.verification_status if fact_check else None,
                    'credibility_score': fact_check.credibility_score if fact_check else None
                })
                
            return results
            
        except SQLAlchemyError as e:
            logger.error(f"Error in get_trending_claims: {str(e)}")
            return []

    async def get_similar_claims_by_id(
        self,
        claim_id: int,
        min_similarity: float = 0.7,
        limit: int = 5
    ) -> List[Dict]:
        """
        یافتن ادعاهای مشابه بر اساس شناسه.
        
        Args:
            claim_id: شناسه ادعا
            min_similarity: حداقل میزان شباهت
            limit: حداکثر تعداد نتایج
            
        Returns:
            لیست ادعاهای مشابه
        """
        try:
            claim = self.session.query(Claim).get(claim_id)
            if not claim:
                return []
                
            return await self.find_similar_claims(
                claim.claim_text,
                min_similarity,
                limit
            )
            
        except SQLAlchemyError as e:
            logger.error(f"Error in get_similar_claims_by_id: {str(e)}")
            return []

    async def mark_claim_as_spam(self, claim_id: int) -> bool:
        """
        علامت‌گذاری ادعا به عنوان اسپم.
        
        Args:
            claim_id: شناسه ادعا
            
        Returns:
            نتیجه عملیات
        """
        try:
            claim = self.session.query(Claim).get(claim_id)
            if not claim:
                return False
                
            # غیرفعال کردن ادعا
            claim.status = 'SPAM'
            claim.updated_at = datetime.utcnow()
            
            # بایگانی نتایج مرتبط
            for fact_check in claim.fact_checks:
                fact_check.verification_status = 'SPAM'
                fact_check.updated_at = datetime.utcnow()
            
            self.session.commit()
            logger.info(f"Marked claim {claim_id} as spam")
            return True
            
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error in mark_claim_as_spam: {str(e)}")
            return False

    async def get_source_credibility(self, domain: str) -> float:
        """
        دریافت امتیاز اعتبار یک منبع.
        
        Args:
            domain: دامنه منبع
            
        Returns:
            امتیاز اعتبار
        """
        try:
            source = self.session.query(Source).filter_by(
                domain=domain,
                is_active=True
            ).first()
            
            return source.base_credibility if source else 0.1
            
        except SQLAlchemyError as e:
            logger.error(f"Error in get_source_credibility: {str(e)}")
            return 0.1