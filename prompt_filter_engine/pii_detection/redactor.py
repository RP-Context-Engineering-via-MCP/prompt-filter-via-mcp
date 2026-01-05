from gliner import GLiNER
from prompt_filter_engine.context_identification_pipeline.pipeline import ContextPipeline
from prompt_filter_engine.entity_value_generator.generator import EntityValueGenerator

class UniversalRedactor:
    def __init__(self):
        print("Loading Generalist Model...")
        self.model = GLiNER.from_pretrained("urchade/gliner_medium-v2.1")
        self.context_enricher = ContextPipeline()
        self.value_generator = EntityValueGenerator()
        
        # Group 1: Identity & PII (High Priority)
        self.batch_pii = [
            "name", "age", "gender", "ethnicity", 
            "phone number", "email", "address", 
            "SSN", "driver license", "bank account", "ip address",
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
        # Filter out self-referencing labels (e.g., text "my age" for label "age")
        enriched_entities = [
            e for e in enriched_entities 
            if e['label'].lower() not in e['text'].lower()
        ]

        enriched_entities.sort(key=lambda x: x['start'], reverse=True)
        
        redacted_text = text
        audit_log = []

        print(f"\n[INFO] Found {len(enriched_entities)} entities.")

        for entity in enriched_entities:
            start = entity['start']
            end = entity['end']
            label = entity['label']
            original_value = entity['text']
            context = entity.get('context', {})
            
            # Generate Fake Value
            fake_value = self.value_generator.generate(original_value, label, context)
            
            # Replace in text (ensure we don't mess up indices if we go backwards)
            # Since we iterate reverse, replacing is safe for indices < start
            redacted_text = redacted_text[:start] + fake_value + redacted_text[end:]
            
            # Log
            log_entry = f"Replaced '{original_value}' with '{fake_value}' | Type: {label}"
            if context:
                log_entry += f" | Context: {context}"
            
            audit_log.append(log_entry)
            print(f"[LOG] {log_entry}")

        if return_enriched:
            return redacted_text, audit_log, enriched_entities
        return redacted_text, audit_log
