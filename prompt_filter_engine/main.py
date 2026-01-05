import sys
import json
import argparse
from prompt_filter_engine.pii_detection.redactor import UniversalRedactor

def main():
    parser = argparse.ArgumentParser(description="Prompt Filter Engine CLI")
    parser.add_argument("prompt", nargs="?", help="The text to anonymize")
    args = parser.parse_args()

    redactor = UniversalRedactor()

    if args.prompt:
        # CLI Mode for MCP Server
        clean_text, log, enriched = redactor.redact(args.prompt, return_enriched=True)
        
        response = {
            "original_text": args.prompt,
            "redacted_text": clean_text,
            "audit_log": log,
            "entities": enriched
        }
        
        # Ensure only JSON is printed to stdout so MCP can parse it
        print(json.dumps(response))
    else:
        # Demo Mode
        text = """
        My name is Sarah, I'm 28 and I live in Chicago. I have Type 2 Diabetes and take Insulin. 
        I love watching Horror movies and my favorite food is Sushi. 
        I am currently single and Christian. My SSN is 000-11-2222.
        I work as a software engineer at a tech company. My email is sarah@example.com.
        My phone number is +94771234567. I was born on 1995-06-15.
        My Bank Account is 123456789012. My IP is 192.168.1.1.
        """
        
        print("\n--- RUNNING DEMO MODE ---\n")
        clean_text, log, enriched = redactor.redact(text, return_enriched=True)
    
        print(f"ORIGINAL:\n{text}\n")
        print(f"ANONYMIZED:\n{clean_text}\n")
        print("=" * 80)
        print("AUDIT LOG:")
        for entry in log:
            print(f" - {entry}")
        print("=" * 80)

if __name__ == "__main__":
    main()
