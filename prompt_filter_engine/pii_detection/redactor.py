from gliner import GLiNER
from prompt_filter_engine.context_identification_pipeline.pipeline import ContextPipeline
from prompt_filter_engine.entity_value_generator.generator import EntityValueGenerator
from prompt_filter_engine.slm_entity_generator.health_inference import HealthEntityClassifier
from prompt_filter_engine.health_phi.phi_resolver import PHIResolver
from prompt_filter_engine.context_identification_pipeline.rule_based.logic import set_health_classifier

class UniversalRedactor:
    def __init__(self):
        print("Loading Generalist Model...")
        self.model = GLiNER.from_pretrained("urchade/gliner_medium-v2.1")
        self.context_enricher = ContextPipeline()
        self.value_generator = EntityValueGenerator()

        # Health PHI components
        self.health_classifier = HealthEntityClassifier()
        self.phi_resolver = PHIResolver()
        # Wire classifier into rule_based processor (avoids circular imports)
        set_health_classifier(self.health_classifier)

        # Group 1: Identity & PII (User Specified 10 types)
        self.batch_pii = [
            "name", "age", "phone number", "email",
            "bank account number", "driver license", "address",
            "ip address", "api key", "credit card number",
            # Added for better address granularity, will be merged into 'address'
            "city", "country"
        ]

        # Group 2: Health PHI — 2 labels only, clean slate
        self.batch_health = ["medical condition", "medication name"]

    def merge_address_entities(self, text, entities):
        """
        Merges adjacent entities of type address, city, country into a single address entity.
        Checks if the text between them is only punctuation/whitespace.
        """
        if not entities:
            return []
            
        # Target labels to merge
        address_labels = {"address", "city", "country", "location"}
        
        # Sort by start position
        sorted_entities = sorted(entities, key=lambda x: x['start'])
        merged_entities = []
        
        if not sorted_entities:
            return []
            
        current_entity = sorted_entities[0]
        
        for next_entity in sorted_entities[1:]:
            # Check if both are address-related
            is_current_addr = current_entity['label'].lower() in address_labels
            is_next_addr = next_entity['label'].lower() in address_labels
            
            should_merge = False
            if is_current_addr and is_next_addr:
                # Check gap between entities
                gap_start = current_entity['end']
                gap_end = next_entity['start']
                gap_text = text[gap_start:gap_end]
                
                # Allow merging if gap contains only separators (space, comma, newline, hyphen)
                # We can be slightly loose here: if it's short and mostly non-alphanumeric
                if not any(c.isalnum() for c in gap_text) and len(gap_text) < 10:
                    should_merge = True
                # Also handle specific prepositions if needed like " in ", " at " (optional, but requested case is comma separated)
                elif gap_text.strip().lower() in [",", "in", "at", "-"]:
                     should_merge = True

            if should_merge:
                # Merge into current_entity
                # We force label to be 'address' if we found a bigger chunk
                current_entity['end'] = next_entity['end']
                current_entity['text'] = text[current_entity['start']:current_entity['end']]
                current_entity['label'] = "address" # Unify label
                # Score: take max or average? Let's take max.
                current_entity['score'] = max(current_entity.get('score', 0), next_entity.get('score', 0))
            else:
                merged_entities.append(current_entity)
                current_entity = next_entity
        
        merged_entities.append(current_entity)
        return merged_entities

    def redact(self, text, return_enriched=False):
        all_entities = []

        # --- PASS 1: Detect PII (unchanged) ---
        entities_pii = self.model.predict_entities(text, self.batch_pii, threshold=0.3)

        # Merge address fragments before adding to all_entities
        entities_pii = self.merge_address_entities(text, entities_pii)

        all_entities.extend(entities_pii)

        # --- PASS 2: Detect Health PHI (medical_condition + medication_name only) ---
        entities_health = self.model.predict_entities(text, self.batch_health, threshold=0.35)

        # Normalise GLiNER label strings to canonical names
        for e in entities_health:
            if e['label'] == 'medical condition':
                e['label'] = 'medical_condition'
            elif e['label'] == 'medication name':
                e['label'] = 'medication_name'

        # Attach ±30-token context window to each health entity for the SLM
        for e in entities_health:
            words_before = text[:e['start']].split()[-30:]
            words_after  = text[e['end']:].split()[:30]
            e['_window'] = ' '.join(words_before + words_after)

        all_entities.extend(entities_health)
        
        # --- CONTEXT ENRICHMENT ---
        enriched_entities = self.context_enricher.enrich_entities(text, all_entities)

        # --- HEALTH NULL-TIER FILTER ---
        # Drop health entities where SLM returned tier=null (GLiNER false positives)
        enriched_entities = [
            e for e in enriched_entities
            if not (
                e['label'] in ('medical_condition', 'medication_name')
                and e.get('context', {}).get('tier') is None
                and e.get('context', {}).get('confidence', 1.0) > 0.0
            )
        ]

        # --- HEALTH PHI RESOLVER: pair condition ↔ medication ---
        enriched_entities = self.phi_resolver.resolve(enriched_entities)

        # Propagate effective_tier into context for generator
        for e in enriched_entities:
            if e['label'] in ('medical_condition', 'medication_name'):
                ctx = e.setdefault('context', {})
                ctx['effective_tier'] = e.get('effective_tier', ctx.get('tier'))
        
        # --- MERGE & CLEANUP ---
        # Filter out self-referencing labels (e.g., text "my age" for label "age")
        # BUT keep it if it contains digits (e.g., "age 34" should be kept)
        # BUT keep it if it contains digits (e.g., "age 34" should be kept)
        final_entities = []
        # Added male/female to this list to prevent them being caught as names now that 'gender' tag is removed
        ignore_terms = {"i", "my", "me", "he", "she", "it", "we", "us", "they", "them", "male", "female"}
        
        for e in enriched_entities:
            text_lower = e['text'].lower()
            label_lower = e['label'].lower()
            
            # Rule 1: Remove if label is in text, UNLESS it has digits (e.g. "age 34")
            if label_lower in text_lower:
                if not any(char.isdigit() for char in text_lower):
                    continue

            # Rule 2: Remove common pronouns/terms detected as names
            if label_lower == "name" and text_lower in ignore_terms:
                continue

            final_entities.append(e)

        enriched_entities = final_entities
        enriched_entities.sort(key=lambda x: x['start'], reverse=True)
        
        redacted_text = text
        labeled_text = text
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
            
            # Generate Label Value
            label_value = f"[{label.upper()}]"
            labeled_text = labeled_text[:start] + label_value + labeled_text[end:]
            
            # Log
            log_entry = f"Replaced '{original_value}' with '{fake_value}' | Type: {label}"
            if context:
                log_entry += f" | Context: {context}"
            
            audit_log.append(log_entry)
            print(f"[LOG] {log_entry}")

        if return_enriched:
            return redacted_text, labeled_text, audit_log, enriched_entities
        return redacted_text, labeled_text, audit_log
