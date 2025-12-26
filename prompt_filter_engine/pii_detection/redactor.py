from gliner import GLiNER
from prompt_filter_engine.context_identification_pipeline.pipeline import ContextPipeline

class UniversalRedactor:
    def __init__(self):
        print("Loading Generalist Model...")
        self.model = GLiNER.from_pretrained("urchade/gliner_medium-v2.1")
        self.context_enricher = ContextPipeline()
        
        # Group 1: Identity & PII (High Priority)
        self.batch_pii = [
            "name", "age", "gender", "ethnicity", 
            "phone number", "email", "address", 
            "SSN", "driver license", "financial situation", 
            "legal", "employment", "date"
        ]
        
        # Group 2: Health & Medical (PHI)
        self.batch_health = [
            "physical health", "mental health", "disabilities", 
            "medications", "allergies", "family history", 
            "smoker", "exercise hours", "diet type"
        ]
        
        # Group 3: Lifestyle & Preferences
        self.batch_lifestyle = [
            "relationship status", "sexual orientation", "religious beliefs",
            "favorite food", "favorite hobbies", "pet",
            "movie genre", "vacation preference"
        ]

    def redact(self, text, return_enriched=False):
        all_entities = []
        
        # --- PASS 1: Detect PII ---
        entities_pii = self.model.predict_entities(text, self.batch_pii, threshold=0.3)
        all_entities.extend(entities_pii)
        
        # --- PASS 2: Detect Health ---
        entities_health = self.model.predict_entities(text, self.batch_health, threshold=0.3)
        all_entities.extend(entities_health)
        
        # --- PASS 3: Detect Lifestyle ---
        entities_life = self.model.predict_entities(text, self.batch_lifestyle, threshold=0.3)
        all_entities.extend(entities_life)
        
        # --- CONTEXT ENRICHMENT ---
        enriched_entities = self.context_enricher.enrich_entities(text, all_entities)
        
        # --- MERGE & CLEANUP ---
        enriched_entities.sort(key=lambda x: x['start'], reverse=True)
        
        redacted_text = text
        audit_log = []

        for entity in enriched_entities:
            start = entity['start']
            end = entity['end']
            label = entity['label']
            
            mask = f"[{label.upper()}]"
            
            if "][" not in redacted_text[start:end]: 
                redacted_text = redacted_text[:start] + mask + redacted_text[end:]
                
                # Enhanced audit log with context
                log_entry = f"Redacted '{entity['text']}' as {label}"
                if entity.get('context'):
                    log_entry += f" | Context: {entity['context']}"
                audit_log.append(log_entry)

        if return_enriched:
            return redacted_text, audit_log, enriched_entities
        return redacted_text, audit_log
