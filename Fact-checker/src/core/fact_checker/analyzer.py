"""
Core analyzer module for fact checking functionality.
Handles the main analysis logic for fact checking claims.
"""
from typing import Dict, List, Optional, Tuple
import asyncio
import logging
from datetime import datetime

from ...data.models.models import Claim, FactCheckResult
from ...data.repositories.fact_repository import FactRepository
from ...utils.helpers import calculate_similarity_score
from ..services.nlp_service import NLPService
from ..services.search_service import SearchService

logger = logging.getLogger(__name__)

class FactAnalyzer:
    """Main class for analyzing claims and generating fact check results."""
    
    def __init__(
        self,
        nlp_service: NLPService,
        search_service: SearchService,
        fact_repository: FactRepository
    ):
        self.nlp_service = nlp_service
        self.search_service = search_service
        self.fact_repository = fact_repository

    async def analyze_claim(self, claim_text: str) -> FactCheckResult:
        """
        Analyze a claim and return fact checking results.
        
        Args:
            claim_text: The text of the claim to analyze
            
        Returns:
            FactCheckResult object containing analysis results
        """
        try:
            # Extract key entities and concepts
            entities = await self.nlp_service.extract_entities(claim_text)
            
            # Search for relevant sources
            sources = await self.search_service.find_relevant_sources(claim_text, entities)
            
            # Check claim against database
            similar_claims = await self.fact_repository.find_similar_claims(claim_text)
            
            # Analyze sentiment and credibility
            sentiment_score = await self.nlp_service.analyze_sentiment(claim_text)
            credibility_score = self._calculate_credibility_score(sources)
            
            # Generate verification status
            verification_status = self._determine_verification_status(
                credibility_score,
                similar_claims
            )
            
            # Compile supporting evidence
            evidence = await self._compile_evidence(sources, similar_claims)
            
            return FactCheckResult(
                claim_text=claim_text,
                verification_status=verification_status,
                credibility_score=credibility_score,
                sentiment_score=sentiment_score,
                evidence=evidence,
                sources=sources,
                analyzed_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error analyzing claim: {str(e)}")
            raise

    def _calculate_credibility_score(self, sources: List[Dict]) -> float:
        """Calculate overall credibility score based on sources."""
        if not sources:
            return 0.0
            
        source_scores = [
            source.get('credibility_score', 0) 
            for source in sources
        ]
        return sum(source_scores) / len(source_scores)

    def _determine_verification_status(
        self,
        credibility_score: float,
        similar_claims: List[Claim]
    ) -> str:
        """Determine verification status based on credibility and similar claims."""
        if credibility_score >= 0.8:
            return "VERIFIED"
        elif credibility_score <= 0.2:
            return "FALSE"
        elif 0.2 < credibility_score < 0.8:
            return "PARTIALLY_TRUE"
        return "UNVERIFIED"

    async def _compile_evidence(
        self,
        sources: List[Dict],
        similar_claims: List[Claim]
    ) -> List[Dict]:
        """Compile supporting evidence from sources and similar claims."""
        evidence = []
        
        # Add evidence from sources
        for source in sources:
            if source.get('relevance_score', 0) > 0.7:
                evidence.append({
                    'type': 'SOURCE',
                    'content': source['content'],
                    'url': source.get('url'),
                    'credibility_score': source.get('credibility_score', 0)
                })
                
        # Add evidence from similar claims
        for claim in similar_claims:
            if claim.verification_status in ['VERIFIED', 'FALSE']:
                evidence.append({
                    'type': 'SIMILAR_CLAIM',
                    'content': claim.claim_text,
                    'verification_status': claim.verification_status,
                    'analyzed_at': claim.analyzed_at
                })
                
        return evidence