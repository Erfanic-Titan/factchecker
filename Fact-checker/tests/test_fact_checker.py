"""
تست‌های مربوط به سرویس فکت‌چکر
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.core.services.fact_checker import FactCheckerService
from src.core.services.text_analysis_service import TextAnalysisService
from src.core.services.image_analysis_service import ImageAnalysisService

@pytest.fixture
async def fact_checker():
    """فیکسچر سرویس فکت‌چکر"""
    service = FactCheckerService()
    await service.initialize()
    return service

@pytest.fixture
def mock_text_analyzer():
    """فیکسچر ماک سرویس تحلیل متن"""
    analyzer = Mock(spec=TextAnalysisService)
    analyzer.analyze_text.return_value = {
        'sentiment': {'positive': 0.3, 'negative': 0.2, 'neutral': 0.5},
        'entities': [{'text': 'تهران', 'type': 'LOCATION'}],
        'keywords': [{'word': 'خبر', 'score': 0.8}]
    }
    return analyzer

@pytest.fixture
def mock_image_analyzer():
    """فیکسچر ماک سرویس تحلیل تصویر"""
    analyzer = Mock(spec=ImageAnalysisService)
    analyzer.analyze_image.return_value = {
        'objects': [{'label': 'person', 'confidence': 0.9}],
        'text': {'fa': {'text': 'متن تست', 'confidence': 0.8}},
        'manipulation_check': {'probability': 0.1}
    }
    return analyzer

@pytest.mark.asyncio
async def test_check_claim(fact_checker, mock_text_analyzer):
    """تست بررسی ادعای متنی"""
    claim = "تهران پرجمعیت‌ترین شهر ایران است"
    
    with patch.object(fact_checker, 'text_analyzer', mock_text_analyzer):
        result = await fact_checker.check_claim(claim)
        
        assert result is not None
        assert 'status' in result
        assert 'confidence_score' in result
        assert 'sources' in result
        assert isinstance(result['confidence_score'], float)
        assert 0 <= result['confidence_score'] <= 1

@pytest.mark.asyncio
async def test_check_image(fact_checker, mock_image_analyzer):
    """تست بررسی تصویر"""
    image_path = "tests/test_data/test_image.jpg"
    
    with patch.object(fact_checker, 'image_analyzer', mock_image_analyzer):
        result = await fact_checker.check_media(
            media_type='image',
            media_path=image_path
        )
        
        assert result is not None
        assert 'status' in result
        assert 'manipulation_check' in result
        assert isinstance(result.get('manipulation_check', {}).get('probability'), float)

@pytest.mark.asyncio
async def test_check_multiple_sources(fact_checker, mock_text_analyzer):
    """تست بررسی همزمان چند منبع"""
    claims = [
        "تهران پرجمعیت‌ترین شهر ایران است",
        "اصفهان دومین شهر پرجمعیت ایران است"
    ]
    
    with patch.object(fact_checker, 'text_analyzer', mock_text_analyzer):
        results = await fact_checker.check_multiple_claims(claims)
        
        assert isinstance(results, list)
        assert len(results) == len(claims)
        for result in results:
            assert 'status' in result
            assert 'confidence_score' in result

@pytest.mark.asyncio
async def test_get_user_statistics(fact_checker):
    """تست دریافت آمار کاربر"""
    user_id = 12345
    
    stats = await fact_checker.get_user_statistics(user_id)
    
    assert isinstance(stats, dict)
    assert 'total_checks' in stats
    assert 'verified_count' in stats
    assert 'false_count' in stats
    assert isinstance(stats['total_checks'], int)

@pytest.mark.asyncio
async def test_update_user_info(fact_checker):
    """تست بروزرسانی اطلاعات کاربر"""
    user_data = {
        'user_id': 12345,
        'username': 'testuser',
        'first_name': 'Test',
        'last_name': 'User',
        'language_code': 'fa'
    }
    
    result = await fact_checker.update_user_info(**user_data)
    assert result is True

@pytest.mark.asyncio
async def test_invalid_claim(fact_checker):
    """تست بررسی ادعای نامعتبر"""
    invalid_claims = ["", None, "   "]
    
    for claim in invalid_claims:
        with pytest.raises(ValueError):
            await fact_checker.check_claim(claim)

@pytest.mark.asyncio
async def test_source_credibility(fact_checker):
    """تست بررسی اعتبار منابع"""
    sources = [
        {'url': 'https://isna.ir/news/123', 'type': 'news'},
        {'url': 'https://example.com/blog', 'type': 'blog'}
    ]
    
    credibility_scores = await fact_checker.evaluate_sources(sources)
    
    assert isinstance(credibility_scores, list)
    assert len(credibility_scores) == len(sources)
    for score in credibility_scores:
        assert 0 <= score <= 1

@pytest.mark.asyncio
async def test_similar_fact_checks(fact_checker, mock_text_analyzer):
    """تست یافتن بررسی‌های مشابه"""
    claim = "تهران پرجمعیت‌ترین شهر ایران است"
    
    with patch.object(fact_checker, 'text_analyzer', mock_text_analyzer):
        similar_checks = await fact_checker.find_similar_checks(claim)
        
        assert isinstance(similar_checks, list)
        for check in similar_checks:
            assert 'claim' in check
            assert 'similarity_score' in check
            assert 0 <= check['similarity_score'] <= 1

@pytest.mark.asyncio
async def test_fact_check_caching(fact_checker, mock_text_analyzer):
    """تست کش کردن نتایج بررسی"""
    claim = "تهران پرجمعیت‌ترین شهر ایران است"
    
    with patch.object(fact_checker, 'text_analyzer', mock_text_analyzer):
        # بررسی اول
        result1 = await fact_checker.check_claim(claim)
        
        # بررسی دوم باید از کش برگردد
        result2 = await fact_checker.check_claim(claim)
        
        assert result1 == result2
        assert mock_text_analyzer.analyze_text.call_count == 1

@pytest.mark.asyncio
async def test_fact_check_report(fact_checker, mock_text_analyzer):
    """تست تولید گزارش بررسی"""
    claim = "تهران پرجمعیت‌ترین شهر ایران است"
    
    with patch.object(fact_checker, 'text_analyzer', mock_text_analyzer):
        result = await fact_checker.check_claim(claim)
        report = await fact_checker.generate_report(result['id'])
        
        assert isinstance(report, dict)
        assert 'summary' in report
        assert 'details' in report
        assert 'sources' in report
        assert 'created_at' in report
        assert isinstance(report['created_at'], datetime)

if __name__ == '__main__':
    pytest.main(['-v'])
