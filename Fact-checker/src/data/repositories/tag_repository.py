"""
ریپازیتوری مخصوص عملیات مربوط به تگ‌ها.
این ماژول امکان مدیریت تگ‌ها و ارتباط آنها با فکت‌چک‌ها را فراهم می‌کند.
"""

[...کد قبلی حفظ می‌شود...]

    async def get_tag_trends(
        self,
        tag_names: List[str],
        days: int = 30
    ) -> Dict[str, List[Dict]]:
        """
        دریافت روند استفاده از تگ‌ها در طول زمان
        
        Args:
            tag_names: لیست نام تگ‌ها
            days: تعداد روزهای گذشته
            
        Returns:
            دیکشنری از نام تگ به لیست آمار روزانه
        """
        try:
            trends = {}
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            for tag_name in tag_names:
                tag = await self.get_by_name(tag_name)
                if not tag:
                    continue
                
                # آمار روزانه
                daily_stats = await self.session.execute(
                    select(
                        func.date(FactCheck.created_at).label('date'),
                        func.count().label('count')
                    )
                    .join(factcheck_tags)
                    .join(Tag)
                    .where(
                        and_(
                            Tag.name == tag_name,
                            FactCheck.created_at >= cutoff_date
                        )
                    )
                    .group_by(func.date(FactCheck.created_at))
                    .order_by('date')
                )
                
                # تبدیل نتایج به فرمت مناسب
                trends[tag_name] = [
                    {
                        'date': row.date.strftime('%Y-%m-%d'),
                        'count': row.count
                    }
                    for row in daily_stats
                ]
                
                # پر کردن روزهای خالی با مقدار صفر
                date_set = {
                    (cutoff_date + timedelta(days=i)).strftime('%Y-%m-%d')
                    for i in range(days + 1)
                }
                existing_dates = {stat['date'] for stat in trends[tag_name]}
                for missing_date in date_set - existing_dates:
                    trends[tag_name].append({
                        'date': missing_date,
                        'count': 0
                    })
                
                # مرتب‌سازی بر اساس تاریخ
                trends[tag_name].sort(key=lambda x: x['date'])
            
            return trends
        except SQLAlchemyError as e:
            logger.error(f"Error getting tag trends: {str(e)}")
            return {}

    async def get_tag_correlations(self, min_correlation: float = 0.1) -> List[Dict]:
        """
        محاسبه همبستگی بین تگ‌ها
        
        Args:
            min_correlation: حداقل میزان همبستگی
            
        Returns:
            لیست روابط همبستگی
        """
        try:
            # دریافت همه تگ‌ها و تعداد استفاده از هر کدام
            tag_usage = await self.session.execute(
                select(
                    Tag.name,
                    func.count(factcheck_tags.c.factcheck_id).label('total_usage')
                )
                .join(factcheck_tags)
                .group_by(Tag.name)
            )
            
            tag_stats = {
                row.name: row.total_usage for row in tag_usage
            }
            
            correlations = []
            processed_pairs = set()
            
            # محاسبه همبستگی برای هر جفت تگ
            for tag1 in tag_stats:
                for tag2 in tag_stats:
                    if tag1 >= tag2 or (tag1, tag2) in processed_pairs:
                        continue
                    
                    # محاسبه تعداد استفاده مشترک
                    co_occurrence = await self.session.execute(
                        select(func.count(distinct(factcheck_tags.c.factcheck_id)))
                        .select_from(
                            factcheck_tags.join(
                                Tag,
                                factcheck_tags.c.tag_id == Tag.id
                            )
                        )
                        .where(
                            and_(
                                Tag.name.in_([tag1, tag2]),
                                factcheck_tags.c.factcheck_id.in_(
                                    select(factcheck_tags.c.factcheck_id)
                                    .where(Tag.name.in_([tag1, tag2]))
                                    .group_by(factcheck_tags.c.factcheck_id)
                                    .having(func.count() > 1)
                                )
                            )
                        )
                    )
                    
                    co_occurrence_count = co_occurrence.scalar_one()
                    
                    # محاسبه ضریب همبستگی
                    correlation = (
                        co_occurrence_count /
                        math.sqrt(tag_stats[tag1] * tag_stats[tag2])
                    )
                    
                    if correlation >= min_correlation:
                        correlations.append({
                            'tag1': tag1,
                            'tag2': tag2,
                            'correlation': correlation,
                            'co_occurrence': co_occurrence_count
                        })
                        
                    processed_pairs.add((tag1, tag2))
            
            return sorted(
                correlations,
                key=lambda x: x['correlation'],
                reverse=True
            )
        except SQLAlchemyError as e:
            logger.error(f"Error calculating tag correlations: {str(e)}")
            return []

    async def get_tag_hierarchy(self) -> Dict[str, List[str]]:
        """
        ایجاد سلسله مراتب تگ‌ها بر اساس همبستگی و استفاده مشترک
        
        Returns:
            دیکشنری از تگ‌های والد به لیست تگ‌های فرزند
        """
        try:
            correlations = await self.get_tag_correlations(min_correlation=0.5)
            hierarchy = {}
            
            # استفاده از تگ‌های با کاربرد بیشتر به عنوان والد
            for corr in correlations:
                tag1_usage = await self.session.execute(
                    select(func.count(factcheck_tags.c.factcheck_id))
                    .join(Tag)
                    .where(Tag.name == corr['tag1'])
                )
                tag2_usage = await self.session.execute(
                    select(func.count(factcheck_tags.c.factcheck_id))
                    .join(Tag)
                    .where(Tag.name == corr['tag2'])
                )
                
                parent = corr['tag1'] if tag1_usage > tag2_usage else corr['tag2']
                child = corr['tag2'] if parent == corr['tag1'] else corr['tag1']
                
                if parent not in hierarchy:
                    hierarchy[parent] = []
                if child not in hierarchy[parent]:
                    hierarchy[parent].append(child)
            
            return hierarchy
        except SQLAlchemyError as e:
            logger.error(f"Error building tag hierarchy: {str(e)}")
            return {}

    async def merge_tags(self, source_name: str, target_name: str) -> bool:
        """
        ادغام دو تگ با انتقال تمام ارتباط‌ها
        
        Args:
            source_name: نام تگ مبدا
            target_name: نام تگ مقصد
            
        Returns:
            True در صورت موفقیت، False در صورت خطا
        """
        try:
            source_tag = await self.get_by_name(source_name)
            target_tag = await self.get_by_name(target_name)
            
            if not source_tag or not target_tag:
                return False
            
            # انتقال تمام ارتباط‌ها به تگ مقصد
            await self.session.execute(
                update(factcheck_tags)
                .where(factcheck_tags.c.tag_id == source_tag.id)
                .values(tag_id=target_tag.id)
            )
            
            # حذف تگ مبدا
            await self.session.delete(source_tag)
            await self.session.commit()
            
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error merging tags: {str(e)}")
            await self.session.rollback()
            return False

    async def split_tag(
        self,
        source_name: str,
        new_tags: List[Dict[str, str]]
    ) -> List[Tag]:
        """
        تقسیم یک تگ به چند تگ جدید
        
        Args:
            source_name: نام تگ مبدا
            new_tags: لیست دیکشنری‌های حاوی اطلاعات تگ‌های جدید
            
        Returns:
            لیست تگ‌های جدید ایجاد شده
        """
        try:
            source_tag = await self.get_by_name(source_name)
            if not source_tag:
                return []
            
            created_tags = []
            
            # ایجاد تگ‌های جدید
            for tag_info in new_tags:
                new_tag = await self.create(**tag_info)
                if new_tag:
                    created_tags.append(new_tag)
                    
                    # کپی ارتباط‌های مرتبط به تگ جدید
                    factcheck_ids = await self.session.execute(
                        select(factcheck_tags.c.factcheck_id)
                        .where(factcheck_tags.c.tag_id == source_tag.id)
                    )
                    
                    for row in factcheck_ids:
                        await self.session.execute(
                            factcheck_tags.insert().values(
                                factcheck_id=row.factcheck_id,
                                tag_id=new_tag.id
                            )
                        )
            
            # حذف تگ مبدا
            await self.session.delete(source_tag)
            await self.session.commit()
            
            return created_tags
        except SQLAlchemyError as e:
            logger.error(f"Error splitting tag: {str(e)}")
            await self.session.rollback()
            return []
