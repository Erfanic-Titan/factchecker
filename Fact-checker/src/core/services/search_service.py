"""
سرویس جستجو برای یافتن منابع و اطلاعات مرتبط.
"""
from typing import Dict, List, Optional
import logging
import asyncio
import aiohttp
from datetime import datetime, timedelta
import json

from ...utils.helpers import clean_url, extract_domain, calculate_similarity_score
from ..services.nlp_service import NLPService

logger = logging.getLogger(__name__)

class SearchService:
    """کلاس سرویس جستجو برای بازیابی اطلاعات مرتبط."""
    
    def __init__(self, nlp_service: NLPService):
        self.nlp_service = nlp_service
        self.initialize_sources()
        
    def initialize_sources(self):
        """مقداردهی اولیه پیکربندی منابع معتبر."""
        try:
            # بارگذاری پیکربندی منابع معتبر
            with open('config/trusted_sources.json', 'r', encoding='utf-8') as f:
                self.trusted_sources = json.load(f)
                
            # مقداردهی اولیه کلاینت‌های API
            self.initialize_api_clients()
            
        except Exception as e:
            logger.error(f"خطا در مقداردهی اولیه منابع: {str(e)}")
            self.trusted_sources = {}

    def initialize_api_clients(self):
        """مقداردهی اولیه کلاینت‌های API برای منابع مختلف."""
        self.api_clients = {}
        
        # پیکربندی کلاینت‌های API برای هر منبع
        for source_type, sources in self.trusted_sources.items():
            for source in sources:
                if source.get('api_key'):
                    self.api_clients[source['domain']] = {
                        'api_key': source['api_key'],
                        'base_url': source['api_url'],
                        'rate_limit': source.get('rate_limit', 60)  # درخواست در دقیقه
                    }

    async def find_relevant_sources(
        self,
        claim_text: str,
        entities: List[Dict],
        max_results: int = 10
    ) -> List[Dict]:
        """
        یافتن منابع مرتبط برای راستی‌آزمایی یک ادعا.
        
        پارامترها:
            claim_text: متن ادعا برای بررسی
            entities: لیست موجودیت‌های استخراج شده از ادعا
            max_results: حداکثر تعداد منابع برای بازگرداندن
            
        خروجی:
            لیستی از منابع مرتبط به همراه امتیاز اعتبار آنها
        """
        try:
            # استخراج کلمات کلیدی جستجو
            keywords = await self._generate_search_keywords(claim_text, entities)
            
            # جستجوی همزمان در انواع مختلف منابع
            search_tasks = [
                self._search_news_archives(keywords),
                self._search_academic_sources(keywords),
                self._search_fact_check_databases(keywords),
                self._search_government_sources(keywords)
            ]
            
            results = await asyncio.gather(*search_tasks)
            
            # ترکیب و رتبه‌بندی نتایج
            all_sources = []
            for source_list in results:
                all_sources.extend(source_list)
                
            # فیلتر و رتبه‌بندی منابع
            ranked_sources = await self._rank_sources(all_sources, claim_text)
            
            # بازگرداندن بهترین نتایج
            return ranked_sources[:max_results]
            
        except Exception as e:
            logger.error(f"خطا در یافتن منابع مرتبط: {str(e)}")
            return []

    async def _generate_search_keywords(
        self,
        claim_text: str,
        entities: List[Dict]
    ) -> List[str]:
        """تولید کلمات کلیدی جستجو از متن ادعا و موجودیت‌ها."""
        keywords = []
        
        # افزودن متن موجودیت‌ها
        keywords.extend([
            entity['text'] 
            for entity in entities 
            if entity['label'] in ['PERSON', 'ORG', 'GPE', 'EVENT']
        ])
        
        # استخراج کلمات کلیدی اضافی با استفاده از NLP
        nlp_keywords = await self.nlp_service.extract_keywords(claim_text)
        keywords.extend(nlp_keywords)
        
        # حذف تکرارها و نرمال‌سازی
        keywords = list(set(keywords))
        keywords = [kw.strip().lower() for kw in keywords if kw.strip()]
        
        return keywords

    async def _search_news_archives(self, keywords: List[str]) -> List[Dict]:
        """جستجو در آرشیو اخبار."""
        try:
            sources = []
            search_params = {
                'keywords': ' '.join(keywords),
                'from_date': (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'),
                'language': 'fa'
            }
            
            # جستجو در منابع خبری معتبر
            for source in self.trusted_sources.get('news', []):
                client = self.api_clients.get(source['domain'])
                if client:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            client['base_url'],
                            params={**search_params, 'apikey': client['api_key']}
                        ) as response:
                            if response.status == 200:
                                data = await response.json()
                                for article in data.get('articles', []):
                                    sources.append({
                                        'title': article['title'],
                                        'content': article['description'],
                                        'url': article['url'],
                                        'published_date': article['publishedAt'],
                                        'source_type': 'NEWS',
                                        'domain': source['domain'],
                                        'credibility_score': source.get('base_credibility', 0.7)
                                    })
            
            return sources
            
        except Exception as e:
            logger.error(f"خطا در جستجوی آرشیو اخبار: {str(e)}")
            return []

    async def _search_academic_sources(self, keywords: List[str]) -> List[Dict]:
        """جستجو در منابع علمی و دانشگاهی."""
        try:
            sources = []
            search_params = {
                'query': ' '.join(keywords),
                'lang': 'fa',
                'full_text': True
            }
            
            # جستجو در پایگاه‌های داده علمی
            for source in self.trusted_sources.get('academic', []):
                client = self.api_clients.get(source['domain'])
                if client:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            client['base_url'],
                            params={**search_params, 'key': client['api_key']}
                        ) as response:
                            if response.status == 200:
                                data = await response.json()
                                for paper in data.get('papers', []):
                                    sources.append({
                                        'title': paper['title'],
                                        'content': paper['abstract'],
                                        'url': paper['doi_url'],
                                        'published_date': paper['published_date'],
                                        'source_type': 'ACADEMIC',
                                        'domain': source['domain'],
                                        'credibility_score': source.get('base_credibility', 0.9)
                                    })
            
            return sources
            
        except Exception as e:
            logger.error(f"خطا در جستجوی منابع علمی: {str(e)}")
            return []

    async def _search_fact_check_databases(self, keywords: List[str]) -> List[Dict]:
        """جستجو در پایگاه‌های داده راستی‌آزمایی."""
        try:
            sources = []
            search_params = {
                'text': ' '.join(keywords),
                'language': 'fa'
            }
            
            # جستجو در پایگاه‌های راستی‌آزمایی
            for source in self.trusted_sources.get('fact_check', []):
                client = self.api_clients.get(source['domain'])
                if client:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            client['base_url'],
                            params={**search_params, 'api_token': client['api_key']}
                        ) as response:
                            if response.status == 200:
                                data = await response.json()
                                for fact_check in data.get('claims', []):
                                    sources.append({
                                        'title': fact_check['claim_title'],
                                        'content': fact_check['claim_text'],
                                        'url': fact_check['article_url'],
                                        'published_date': fact_check['date_published'],
                                        'source_type': 'FACT_CHECK',
                                        'domain': source['domain'],
                                        'credibility_score': source.get('base_credibility', 0.95),
                                        'verification_status': fact_check['rating']
                                    })
            
            return sources
            
        except Exception as e:
            logger.error(f"خطا در جستجوی پایگاه‌های راستی‌آزمایی: {str(e)}")
            return []

    async def _search_government_sources(self, keywords: List[str]) -> List[Dict]:
        """جستجو در منابع رسمی و دولتی."""
        try:
            sources = []
            search_params = {
                'query': ' '.join(keywords),
                'type': 'official_data'
            }
            
            # جستجو در وب‌سایت‌ها و پرتال‌های دولتی
            for source in self.trusted_sources.get('government', []):
                client = self.api_clients.get(source['domain'])
                if client:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            client['base_url'],
                            params={**search_params, 'token': client['api_key']}
                        ) as response:
                            if response.status == 200:
                                data = await response.json()
                                for document in data.get('documents', []):
                                    sources.append({
                                        'title': document['title'],
                                        'content': document['description'],
                                        'url': document['url'],
                                        'published_date': document['date'],
                                        'source_type': 'GOVERNMENT',
                                        'domain': source['domain'],
                                        'credibility_score': source.get('base_credibility', 0.95),
                                        'department': document.get('department')
                                    })
            
            return sources
            
        except Exception as e:
            logger.error(f"خطا در جستجوی منابع دولتی: {str(e)}")
            return []

    async def _rank_sources(
        self,
        sources: List[Dict],
        claim_text: str
    ) -> List[Dict]:
        """رتبه‌بندی منابع بر اساس ارتباط و اعتبار."""
        try:
            # محاسبه امتیاز ارتباط برای هر منبع
            for source in sources:
                relevance_score = await calculate_similarity_score(
                    claim_text,
                    f"{source['title']} {source['content']}"
                )
                source['relevance_score'] = relevance_score
                
                # محاسبه امتیاز نهایی
                source['final_score'] = (
                    source['credibility_score'] * 0.6 +
                    source['relevance_score'] * 0.4
                )
                
            # مرتب‌سازی بر اساس امتیاز نهایی
            ranked_sources = sorted(
                sources,
                key=lambda x: x['final_score'],
                reverse=True
            )
            
            return ranked_sources
            
        except Exception as e:
            logger.error(f"خطا در رتبه‌بندی منابع: {str(e)}")
            return sources

    async def validate_source(self, url: str) -> Dict:
        """اعتبارسنجی یک منبع بر اساس URL آن."""
        try:
            domain = extract_domain(url)
            
            # بررسی دامنه در لیست منابع معتبر
            for source_type, sources in self.trusted_sources.items():
                for source in sources:
                    if domain == source['domain']:
                        return {
                            'is_trusted': True,
                            'source_type': source_type,
                            'base_credibility': source.get('base_credibility', 0.5),
                            'details': source.get('details', {})
                        }
            
            # اگر منبع در لیست نباشد
            return {
                'is_trusted': False,
                'source_type': 'UNKNOWN',
                'base_credibility': 0.1,
                'details': {}
            }
            
        except Exception as e:
            logger.error(f"خطا در اعتبارسنجی منبع: {str(e)}")
            return {
                'is_trusted': False,
                'error': str(e)
            }