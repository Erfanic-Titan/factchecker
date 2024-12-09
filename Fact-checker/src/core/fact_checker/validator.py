"""
Validator module for fact checking input validation and preliminary checks.
"""
from typing import Dict, List, Optional, Union
import re
import logging
from datetime import datetime

from ...utils.helpers import clean_text, is_valid_url
from ..services.nlp_service import NLPService

logger = logging.getLogger(__name__)

class InputValidator:
    """Validates and preprocesses input for fact checking."""
    
    def __init__(self, nlp_service: NLPService):
        self.nlp_service = nlp_service
        self.min_claim_length = 10
        self.max_claim_length = 1000
        
    async def validate_claim(
        self,
        claim: Union[str, Dict],
        input_type: str = "text"
    ) -> Dict:
        """
        Validate and preprocess a claim before fact checking.
        
        Args:
            claim: The claim text or claim object to validate
            input_type: Type of input ("text", "url", "image", "audio")
            
        Returns:
            Dict containing validated and preprocessed claim data
            
        Raises:
            ValueError: If claim is invalid
        """
        try:
            # Extract claim text based on input type
            claim_text = await self._extract_claim_text(claim, input_type)
            
            # Basic validation
            self._validate_claim_length(claim_text)
            cleaned_text = clean_text(claim_text)
            
            # Language detection
            language = await self.nlp_service.detect_language(cleaned_text)
            
            # Check for prohibited content
            await self._check_prohibited_content(cleaned_text)
            
            # Classify claim type
            claim_type = await self.nlp_service.classify_claim_type(cleaned_text)
            
            return {
                'claim_text': cleaned_text,
                'input_type': input_type,
                'language': language,
                'claim_type': claim_type,
                'original_content': claim,
                'validated_at': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            raise ValueError(f"Invalid claim: {str(e)}")

    async def _extract_claim_text(
        self,
        claim: Union[str, Dict],
        input_type: str
    ) -> str:
        """Extract claim text from different input types."""
        if input_type == "text":
            return claim if isinstance(claim, str) else str(claim)
            
        elif input_type == "url":
            if not is_valid_url(claim):
                raise ValueError("Invalid URL format")
            # URL content extraction would be handled by a separate service
            
        elif input_type == "image":
            if not claim.get('image_data'):
                raise ValueError("No image data provided")
            # Image text extraction would be handled by OCR service
            
        elif input_type == "audio":
            if not claim.get('audio_data'):
                raise ValueError("No audio data provided")
            # Audio transcription would be handled by speech-to-text service
            
        else:
            raise ValueError(f"Unsupported input type: {input_type}")
            
        return ""  # Placeholder until specific extractors are implemented

    def _validate_claim_length(self, claim_text: str):
        """Validate claim text length."""
        if len(claim_text) < self.min_claim_length:
            raise ValueError(
                f"Claim too short. Minimum length is {self.min_claim_length} characters."
            )
        if len(claim_text) > self.max_claim_length:
            raise ValueError(
                f"Claim too long. Maximum length is {self.max_claim_length} characters."
            )

    async def _check_prohibited_content(self, text: str):
        """Check for prohibited or inappropriate content."""
        # This would integrate with content moderation services
        # For now, implement basic checks
        prohibited_patterns = [
            r'private\s+information',
            r'classified\s+data',
            # Add more patterns as needed
        ]
        
        for pattern in prohibited_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                raise ValueError("Prohibited content detected")
                
class ValidationResult:
    """Stores the results of claim validation."""
    
    def __init__(
        self,
        is_valid: bool,
        claim_text: str,
        input_type: str,
        errors: Optional[List[str]] = None
    ):
        self.is_valid = is_valid
        self.claim_text = claim_text
        self.input_type = input_type
        self.errors = errors or []
        self.validated_at = datetime.utcnow()