
import sys
import os

# Ensure we can import from parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from prompt_filter_engine.pii_detection.redactor import UniversalRedactor

def test_redaction():
    print("Initializing Redactor...")
    redactor = UniversalRedactor()
    
    # Test 1: All 10 Entities (No Gender)
    prompt_all = (
        "My name is John Doe, age 34. "
        "Phone: +94771234567. Email: john.doe@example.com. "
        "Bank Account: 123456789012. License: B1234567. "
        "Address: 123 Lotus Rd, Colombo. "
        "IP: 192.168.1.10. "
        "API Key: sk-abcdef123456. "
        "Credit Card: 4111111111111111."
    )
    
    print("\n--- Test 1: All 10 Entities ---")
    print(f"Original: {prompt_all}")
    redacted_text, logs = redactor.redact(prompt_all)
    print(f"Redacted: {redacted_text}")
    
    # Check if critical parts are hidden
    sensitive_values = [
        "John Doe", "34", "+94771234567", "john.doe@example.com",
        "123456789012", "B1234567", "123 Lotus Rd, Colombo", "192.168.1.10",
        "sk-abcdef123456", "4111111111111111"
    ]
    
    passed = True
    for val in sensitive_values:
        if val in redacted_text:
            print(f"FAILED: Value '{val}' was NOT redacted.")
            passed = False
            
    if passed:
        print("SUCCESS: All sensitive values were redacted.")

    # Test 2: Verify Exclusions (Gender, Lifestyle, Health should NOT be redacted)
    prompt_exclusion = "I am a male who loves tennis."
    print("\n--- Test 2: Exclusions ---")
    print(f"Original: {prompt_exclusion}")
    redacted_text_ex, logs_ex = redactor.redact(prompt_exclusion)
    print(f"Redacted: {redacted_text_ex}")
    
    # "male" (gender) and "tennis" (lifestyle) should remain
    if "male" in redacted_text_ex and "tennis" in redacted_text_ex:
        print("SUCCESS: Excluded categories (Gender/Hobbies) were NOT redacted.")
    else:
        print("FAILED: Excluded categories were WRONGLY redacted.")

if __name__ == "__main__":
    test_redaction()
