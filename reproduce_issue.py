import sys
import os

# Add the parent directory to the path so we can import the module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from prompt_filter_engine.pii_detection.redactor import UniversalRedactor

def test_address_redaction():
    redactor = UniversalRedactor()
    text = "Kamal Perera is a 34-year-old individual living at No. 102, Lake View Road, Nawala, Sri Lanka. He can be reached via the phone number +94 77 456 7890 or through the"
    
    print(f"Original Text: {text}")
    print("-" * 50)
    
    redacted_text, audit_log, enriched_entities = redactor.redact(text, return_enriched=True)
    
    print(f"Redacted Text: {redacted_text}")
    print("-" * 50)
    print("Detected Entities:")
    for entity in enriched_entities:
        print(f"Label: {entity['label']}, Text: '{entity['text']}', Start: {entity['start']}, End: {entity['end']}")

if __name__ == "__main__":
    test_address_redaction()
