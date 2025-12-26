from prompt_filter_engine.pii_detection.redactor import UniversalRedactor

if __name__ == "__main__":
    redactor = UniversalRedactor()

    text = """
    My name is Sarah, I'm 28 and I live in Chicago. I have Type 2 Diabetes and take Insulin. 
    I love watching Horror movies and my favorite food is Sushi. 
    I am currently single and Christian. My SSN is 000-11-2222.
    I work as a software engineer at a tech company. My email is sarah@example.com.
    My phone number is +94771234567. I was born on 1995-06-15.
    """

    clean_text, log, enriched = redactor.redact(text, return_enriched=True)

    print(f"ORIGINAL:\n{text}\n")
    print(f"REDACTED:\n{clean_text}\n")
    print("=" * 80)
    print("ENRICHED ENTITIES WITH CONTEXT:")
    print("=" * 80)
    for entity in enriched:
        print(f"\n📌 {entity['label'].upper()}: '{entity['text']}'")
        if entity.get('context'):
            for key, value in entity['context'].items():
                print(f"   • {key}: {value}")
