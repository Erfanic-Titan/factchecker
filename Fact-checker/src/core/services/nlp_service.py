"""
Natural Language Processing service for text analysis and processing.
"""
from typing import Dict, List, Optional, Tuple
import logging
from pathlib import Path
import json

import spacy
from transformers import pipeline
from nltk.sentiment import SentimentIntensityAnalyzer
import torch

logger = logging.getLogger(__name__)

class NLPService:
    """Handles natural language processing tasks."""
    
    def __init__(self):
        self.initialize_models()
        
    def initialize_models(self):
        """Initialize NLP models and pipelines."""
        try:
            # Load spaCy model for Persian
            self.nlp = spacy.load("xx_ent_wiki_sm")  # Multilingual model
            
            # Initialize sentiment analyzer
            self.sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model="HooshvareLab/bert-fa-base-uncased"
            )
            
            # Initialize zero-shot classifier
            self.classifier = pipeline(
                "zero-shot-classification",
                model="joeddav/xlm-roberta-large-xnli"
            )
            
            # Load custom entity patterns
            self.load_custom_patterns()
            
        except Exception as e:
            logger.error(f"Error initializing NLP models: {str(e)}")
            raise

    def load_custom_patterns(self):
        """Load custom entity patterns for Persian text."""
        try:
            patterns_path = Path(__file__).parent / "data" / "entity_patterns.json"
            if patterns_path.exists():
                with open(patterns_path, 'r', encoding='utf-8') as f:
                    self.custom_patterns = json.load(f)
            else:
                self.custom_patterns = {}
                
        except Exception as e:
            logger.error(f"Error loading custom patterns: {str(e)}")
            self.custom_patterns = {}

    async def extract_entities(self, text: str) -> List[Dict]:
        """
        Extract named entities from text.
        
        Args:
            text: Input text
            
        Returns:
            List of extracted entities with their types
        """
        try:
            doc = self.nlp(text)
            entities = []
            
            # Extract entities from spaCy
            for ent in doc.ents:
                entities.append({
                    'text': ent.text,
                    'label': ent.label_,
                    'start': ent.start_char,
                    'end': ent.end_char
                })
                
            # Apply custom patterns
            entities.extend(self._apply_custom_patterns(text))
            
            return entities
            
        except Exception as e:
            logger.error(f"Error extracting entities: {str(e)}")
            return []

    async def analyze_sentiment(self, text: str) -> float:
        """
        Analyze sentiment of text.
        
        Args:
            text: Input text
            
        Returns:
            Sentiment score between -1 (negative) and 1 (positive)
        """
        try:
            result = self.sentiment_analyzer(text)
            
            # Map sentiment labels to scores
            sentiment_mapping = {
                'LABEL_0': -1.0,  # Negative
                'LABEL_1': 0.0,   # Neutral
                'LABEL_2': 1.0    # Positive
            }
            
            return sentiment_mapping.get(result[0]['label'], 0.0)
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return 0.0

    async def classify_claim_type(self, text: str) -> str:
        """
        Classify the type of claim.
        
        Args:
            text: Input text
            
        Returns:
            Claim type classification
        """
        try:
            # Define possible claim types
            candidate_labels = [
                "SCIENTIFIC",
                "STATISTICAL",
                "POLITICAL",
                "HISTORICAL",
                "SOCIAL",
                "HEALTH",
                "ECONOMIC"
            ]
            
            result = self.classifier(
                text,
                candidate_labels,
                multi_label=False
            )
            
            return result['labels'][0]
            
        except Exception as e:
            logger.error(f"Error classifying claim: {str(e)}")
            return "UNKNOWN"

    async def detect_language(self, text: str) -> str:
        """
        Detect the language of text.
        
        Args:
            text: Input text
            
        Returns:
            ISO language code
        """
        try:
            doc = self.nlp(text)
            return doc.lang_
            
        except Exception as e:
            logger.error(f"Error detecting language: {str(e)}")
            return "unknown"

    def _apply_custom_patterns(self, text: str) -> List[Dict]:
        """Apply custom entity patterns to text."""
        entities = []
        
        for pattern_type, patterns in self.custom_patterns.items():
            for pattern in patterns:
                # Apply regex patterns
                matches = pattern['regex'].finditer(text)
                for match in matches:
                    entities.append({
                        'text': match.group(),
                        'label': pattern_type,
                        'start': match.start(),
                        'end': match.end()
                    })
                    
        return entities

    async def extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text."""
        try:
            doc = self.nlp(text)
            keywords = []
            
            # Extract nouns and proper nouns
            for token in doc:
                if token.pos_ in ['NOUN', 'PROPN'] and not token.is_stop:
                    keywords.append(token.text)
                    
            return list(set(keywords))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Error extracting keywords: {str(e)}")
            return []

    async def extract_quotes(self, text: str) -> List[Dict]:
        """Extract quotes and their potential sources from text."""
        try:
            doc = self.nlp(text)
            quotes = []
            
            # Find text between quotation marks
            quote_pairs = []
            current_start = None
            
            for i, token in enumerate(doc):
                if token.text in ['"', '"', '"']:
                    if current_start is None:
                        current_start = i
                    else:
                        quote_pairs.append((current_start, i))
                        current_start = None
                        
            # Extract quotes and try to identify speakers
            for start, end in quote_pairs:
                quote_text = doc[start+1:end].text
                
                # Look for potential speaker before the quote
                speaker = None
                if start > 0:
                    previous_tokens = doc[max(0, start-5):start]
                    for token in previous_tokens:
                        if token.pos_ == "PROPN":
                            speaker = token.text
                            
                quotes.append({
                    'text': quote_text,
                    'speaker': speaker,
                    'start': doc[start].idx,
                    'end': doc[end].idx + len(doc[end])
                })
                
            return quotes
            
        except Exception as e:
            logger.error(f"Error extracting quotes: {str(e)}")
            return []

    async def analyze_credibility_indicators(self, text: str) -> Dict[str, float]:
        """
        Analyze various indicators of text credibility.
        
        Args:
            text: Input text
            
        Returns:
            Dictionary of credibility indicators and their scores
        """
        try:
            doc = self.nlp(text)
            indicators = {
                'has_sources': 0.0,
                'factual_language': 0.0,
                'emotional_language': 0.0,
                'click_bait': 0.0,
                'hedge_words': 0.0
            }
            
            # Check for source citations
            source_patterns = [
                'according to',
                'based on',
                'cited in',
                'reported by',
                'به گزارش',
                'به نقل از',
                'طبق'
            ]
            indicators['has_sources'] = any(pattern in text.lower() for pattern in source_patterns)
            
            # Analyze language features
            factual_count = 0
            emotional_count = 0
            hedge_count = 0
            
            for token in doc:
                # Count factual indicators
                if token.pos_ in ['NUM', 'PROPN'] or token.ent_type_ in ['DATE', 'TIME', 'PERCENT']:
                    factual_count += 1
                    
                # Count emotional language
                if token._.is_emotional:  # Requires custom attribute
                    emotional_count += 1
                    
                # Count hedge words
                if token.text.lower() in self.hedge_words:
                    hedge_count += 1
                    
            # Normalize counts
            doc_length = len(doc)
            indicators['factual_language'] = min(1.0, factual_count / max(1, doc_length))
            indicators['emotional_language'] = min(1.0, emotional_count / max(1, doc_length))
            indicators['hedge_words'] = min(1.0, hedge_count / max(1, doc_length))
            
            # Detect clickbait features
            clickbait_score = self._analyze_clickbait(text)
            indicators['click_bait'] = clickbait_score
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error analyzing credibility indicators: {str(e)}")
            return {k: 0.0 for k in ['has_sources', 'factual_language', 'emotional_language', 'click_bait', 'hedge_words']}

    def _analyze_clickbait(self, text: str) -> float:
        """Analyze text for clickbait characteristics."""
        clickbait_indicators = 0
        total_indicators = 4
        
        # Check for excessive punctuation
        if '!!!' in text or '???' in text:
            clickbait_indicators += 1
            
        # Check for all caps words
        if any(word.isupper() and len(word) > 3 for word in text.split()):
            clickbait_indicators += 1
            
        # Check for sensational words
        sensational_words = [
            'shocking',
            'incredible',
            'unbelievable',
            'mind-blowing',
            'باورنکردنی',
            'عجیب',
            'شگفت‌انگیز',
            'جنجالی'
        ]
        if any(word in text.lower() for word in sensational_words):
            clickbait_indicators += 1
            
        # Check for numbered lists at start
        if bool(re.match(r'^\d+\s+', text)):
            clickbait_indicators += 1
            
        return clickbait_indicators / total_indicators

    @property
    def hedge_words(self) -> Set[str]:
        """Get set of hedge words for credibility analysis."""
        return {
            'maybe',
            'perhaps',
            'possibly',
            'شاید',
            'احتمالاً',
            'ممکن است',
            'به نظر می‌رسد',
            # Add more hedge words as needed
        }