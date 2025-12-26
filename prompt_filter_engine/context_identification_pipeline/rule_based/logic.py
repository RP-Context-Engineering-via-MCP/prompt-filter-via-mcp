import re
from datetime import datetime
from typing import Dict, Any, Optional
from .patterns import EMAIL_PATTERNS, PHONE_PATTERNS, SSN_PATTERNS, DL_PATTERNS

class RuleBasedProcessor:
    def __init__(self):
        self.email_patterns = EMAIL_PATTERNS
        self.phone_patterns = PHONE_PATTERNS
        self.ssn_patterns = SSN_PATTERNS
        self.dl_patterns = DL_PATTERNS

    def apply_rules(self, entity: Dict) -> Dict:
        """Apply deterministic rules based on entity type"""
        label = entity['label'].lower()
        text = entity['text']
        context = {}
        
        if label == 'age':
            context.update(self._analyze_age(text))
        elif label == 'email':
            context.update(self._analyze_email(text))
        elif label == 'phone number':
            context.update(self._analyze_phone(text))
        elif label == 'ssn':
            context.update(self._analyze_ssn(text))
        elif label == 'driver license':
            context.update(self._analyze_driver_license(text))
        elif label == 'date':
            context.update(self._analyze_date(text))
        elif label == 'name':
            context.update(self._analyze_name(text))
        elif label == 'gender':
            context.update(self._analyze_gender(text))
        elif label == 'ethnicity':
            context.update(self._analyze_ethnicity(text))
            
        return context
    
    def _analyze_age(self, text: str) -> Dict:
        """Age → Life Stage"""
        try:
            age = int(re.search(r'\d+', text).group())
            if age <= 12:
                stage = 'child'
            elif age <= 19:
                stage = 'teen'
            elif age <= 59:
                stage = 'adult'
            else:
                stage = 'senior'
            return {'life_stage': stage, 'confidence': 1.0}
        except:
            return {'life_stage': 'unknown', 'confidence': 0.0}
    
    def _analyze_email(self, text: str) -> Dict:
        """Email → Domain Type, Region"""
        context = {}
        
        # Domain type
        if re.search(self.email_patterns['gov'], text):
            context['domain_type'] = 'government'
            context['confidence_domain'] = 1.0
        elif re.search(self.email_patterns['edu'], text):
            context['domain_type'] = 'educational'
            context['confidence_domain'] = 1.0
        elif re.search(self.email_patterns['work'], text):
            context['domain_type'] = 'personal/work'
            context['confidence_domain'] = 0.7
        else:
            context['domain_type'] = 'unknown'
            context['confidence_domain'] = 0.0
        
        # Region
        if '.lk' in text.lower():
            context['region'] = 'sri_lanka'
            context['confidence_region'] = 1.0
        else:
            context['region'] = 'international'
            context['confidence_region'] = 0.8
            
        return context
    
    def _analyze_phone(self, text: str) -> Dict:
        """Phone → Region, Carrier Type"""
        clean = re.sub(r'[^\d+]', '', text)
        
        if re.match(self.phone_patterns['sl_mobile'], clean):
            return {
                'region': 'sri_lanka',
                'carrier_type': 'mobile',
                'confidence': 1.0
            }
        elif re.match(self.phone_patterns['sl_landline'], clean):
            return {
                'region': 'sri_lanka',
                'carrier_type': 'landline',
                'confidence': 1.0
            }
        elif re.match(self.phone_patterns['international'], clean):
            return {
                'region': 'international',
                'carrier_type': 'unknown',
                'confidence': 0.9
            }
        else:
            return {
                'region': 'unknown',
                'carrier_type': 'unknown',
                'confidence': 0.0
            }
    
    def _analyze_ssn(self, text: str) -> Dict:
        """SSN → Issuing Country"""
        if re.match(self.ssn_patterns['us'], text):
            return {'issuing_country': 'us', 'confidence': 1.0}
        else:
            return {'issuing_country': 'unknown', 'confidence': 0.5}
    
    def _analyze_driver_license(self, text: str) -> Dict:
        """Driver License → Issuing Region, Format"""
        clean = text.strip().upper()
        
        if re.match(self.dl_patterns['sl_new'], clean):
            return {
                'issuing_region': 'sri_lanka',
                'format_type': 'new_sl',
                'confidence': 1.0
            }
        elif re.match(self.dl_patterns['sl_old'], clean):
            return {
                'issuing_region': 'sri_lanka',
                'format_type': 'old_sl',
                'confidence': 1.0
            }
        else:
            return {
                'issuing_region': 'international',
                'format_type': 'international',
                'confidence': 0.7
            }
    
    def _analyze_date(self, text: str) -> Dict:
        """Date → Recency"""
        try:
            # Try common date formats
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y']:
                try:
                    date_obj = datetime.strptime(text.strip(), fmt)
                    break
                except:
                    continue
            else:
                return {'recency': 'unknown', 'confidence': 0.0}
            
            # Calculate recency
            delta = datetime.now() - date_obj
            years = delta.days / 365.25
            
            if years < 1:
                recency = 'recent'
            elif years <= 5:
                recency = 'medium'
            else:
                recency = 'historical'
                
            return {'recency': recency, 'confidence': 1.0}
        except:
            return {'recency': 'unknown', 'confidence': 0.0}
    
    def _analyze_name(self, text: str) -> Dict:
        """Name → Gender, Origin (temporary solution)"""
        return {
            'gender': 'unknown',
            'cultural_origin': 'sri_lanka',
            'confidence': 0.5
        }
    
    def _analyze_gender(self, text: str) -> Dict:
        """Gender → Binary Classification"""
        text_lower = text.lower()
        if any(word in text_lower for word in ['male', 'man', 'boy', 'he']):
            return {'classification': 'male', 'confidence': 1.0}
        elif any(word in text_lower for word in ['female', 'woman', 'girl', 'she']):
            return {'classification': 'female', 'confidence': 1.0}
        else:
            return {'classification': 'non-binary', 'confidence': 0.6}
    
    def _analyze_ethnicity(self, text: str) -> Dict:
        """Ethnicity → Ethnic Group"""
        text_lower = text.lower()
        
        if 'sinhala' in text_lower or 'sinhalese' in text_lower:
            return {'ethnic_group': 'sinhala', 'region_context': 'sri_lanka', 'confidence': 1.0}
        elif 'tamil' in text_lower:
            return {'ethnic_group': 'tamil', 'region_context': 'sri_lanka', 'confidence': 1.0}
        elif 'muslim' in text_lower or 'moor' in text_lower:
            return {'ethnic_group': 'muslim', 'region_context': 'sri_lanka', 'confidence': 1.0}
        elif 'burgher' in text_lower:
            return {'ethnic_group': 'burgher', 'region_context': 'sri_lanka', 'confidence': 1.0}
        else:
            return {'ethnic_group': 'other', 'region_context': 'unknown', 'confidence': 0.3}
