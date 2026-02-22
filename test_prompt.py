import json
from prompt_filter_engine.pii_detection.redactor import UniversalRedactor
import warnings
warnings.filterwarnings('ignore')

def main():
    redactor = UniversalRedactor()
    prompt = "I would like to update my profile with the following information: My name is Michael Thompson, I am 42 years old, and my phone number is +1 (415) 555-7823. My email address is michael.thompson82@examplemail.com . My bank account number is 021345678912 and my credit card number is 4539 1488 0343 6467. My driver license number is D4598732 issued in California. I currently live at 742 Evergreen Terrace in San Francisco, United States. My IP address is 192.168.14.27 and my API key is sk_test_51N8kLmP9qR2xYzABCD1234XYZ. For medical records, I have been diagnosed with Type 2 Diabetes and I am currently taking Metformin. Please update and securely store all of this information in the system."
    clean_text, labeled_text, log, enriched = redactor.redact(prompt, return_enriched=True)
    response = {
        "original_text": prompt,
        "redacted_text": clean_text,
        "labeled_text": labeled_text,
        "audit_log": log,
        "entities": enriched
    }
    with open("test_result.json", "w", encoding="utf-8") as f:
        json.dump(response, f, indent=2)

if __name__ == "__main__":
    main()
