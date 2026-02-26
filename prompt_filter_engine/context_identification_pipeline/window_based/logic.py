from typing import Dict, Any, List
from .patterns import (
    EMPLOYMENT_KEYWORDS,
    EMPLOYMENT_SECTOR,
    EMPLOYMENT_INDUSTRY,
    FINANCIAL_KEYWORDS,
    DATE_TYPE_KEYWORDS
)

class WindowBasedProcessor:
    def __init__(self):
        self.employment_keywords = EMPLOYMENT_KEYWORDS
        self.employment_sector = EMPLOYMENT_SECTOR
        self.employment_industry = EMPLOYMENT_INDUSTRY
        self.financial_keywords = FINANCIAL_KEYWORDS
        self.date_type_keywords = DATE_TYPE_KEYWORDS

# ResearchMe: To identify the theoritical way to exmplain why 50 words is good or use another
    def extract_window(self, text: str, start: int, end: int, words: int = 50) -> str:
        """Extract ±N words around entity"""
        # Find word boundaries
        before = text[:start].split()[-words:]
        after = text[end:].split()[:words]
        
        window = ' '.join(before + after)
        return window.lower()
    
    def apply_keywords(self, entity: Dict, window_text: str) -> Dict:
        """Apply keyword matching on window text"""
        label = entity['label'].lower()
        context = {}
        
        if label == 'employment':
            context.update(self._match_employment(window_text))
        elif label == 'financial situation':
            context.update(self._match_financial(window_text))
        elif label == 'date':
            context.update(self._match_date_type(window_text))
        elif label in ('medical_condition', 'medication_name'):
            context.update(self._match_health(label, window_text))

        return context
    
    def _match_employment(self, window: str) -> Dict:
        """Match employment keywords"""
        context = {}
        
        # Employment status
        for status, keywords in self.employment_keywords.items():
            if any(kw in window for kw in keywords):
                context['employment_status'] = status
                context['confidence_status'] = 0.8
                break
        
        # Sector
        for sector, keywords in self.employment_sector.items():
            if any(kw in window for kw in keywords):
                context['sector'] = sector
                context['confidence_sector'] = 0.7
                break
        
        # Industry
        for industry, keywords in self.employment_industry.items():
            if any(kw in window for kw in keywords):
                context['industry'] = industry
                context['confidence_industry'] = 0.7
                break
                
        return context
    
    def _match_financial(self, window: str) -> Dict:
        """Match financial keywords"""
        for level, keywords in self.financial_keywords.items():
            if any(kw in window for kw in keywords):
                return {
                    'status_level': level,
                    'confidence': 0.7
                }
        return {}
    
    def _match_date_type(self, window: str) -> Dict:
        """Match date type keywords"""
        for date_type, keywords in self.date_type_keywords.items():
            if any(kw in window for kw in keywords):
                return {
                    'date_type': date_type,
                    'confidence_date_type': 0.8
                }
        return {}

    def _match_health(self, label: str, window: str) -> dict:
        """Confirm health entity type using surrounding keyword signals."""
        CONDITION_TRIGGERS  = [
            'diagnosed with', 'suffering from', 'has been', 'condition',
            'disorder', 'disease', 'illness', 'syndrome', 'history of',
        ]
        MEDICATION_TRIGGERS = [
            'prescribed', 'taking', 'dose of', 'treatment with',
            'medication', 'tablet', 'mg', 'drug', 'therapy',
        ]

        triggers = CONDITION_TRIGGERS if label == 'medical_condition' else MEDICATION_TRIGGERS
        matched  = [kw for kw in triggers if kw in window]

        if matched:
            return {
                'health_context_confirmed': True,
                'matched_keywords': matched,
                'confidence_health': 0.85,
            }
        return {'health_context_confirmed': False, 'confidence_health': 0.5}
