from typing import List, Dict
from .rule_based import RuleBasedProcessor
from .window_based import WindowBasedProcessor

class ContextPipeline:
    def __init__(self):
        """Initialize context enrichment rules and patterns"""
        self.rule_processor = RuleBasedProcessor()
        self.window_processor = WindowBasedProcessor()
        
    def enrich_entities(self, text: str, entities: List[Dict]) -> List[Dict]:
        """
        Main enrichment pipeline
        Args:
            text: Original text
            entities: List of entities from GLiNER with {text, label, start, end}
        Returns:
            List of enriched entities with context
        """
        enriched = []
        
        for entity in entities:
            enriched_entity = entity.copy()
            
            # Phase 1: Rule-based context
            phase1_context = self.rule_processor.apply_rules(entity)
            
            # Phase 2: Window + Keywords context
            window_text = self.window_processor.extract_window(text, entity['start'], entity['end'])
            phase2_context = self.window_processor.apply_keywords(entity, window_text)
            
            # Merge contexts (Phase 1 takes precedence, Phase 2 fills gaps)
            final_context = {**phase2_context, **phase1_context}
            
            enriched_entity['context'] = final_context
            enriched.append(enriched_entity)
            
        return enriched
