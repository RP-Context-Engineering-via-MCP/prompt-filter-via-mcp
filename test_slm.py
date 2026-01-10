import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from prompt_filter_engine.entity_value_generator.generator import EntityValueGenerator

def test_slm_generation():
    print("Testing SLM Value Generator...")
    try:
        generator = EntityValueGenerator()
        
        original_address = "No. 102, Lake View Road, Nawala, Sri Lanka"
        
        # Test 1: SL Context
        print("\n--- Test 1: SL Context ---")
        generated_sl = generator.generate(original_address, "address", {"region": "SL"})
        print(f"Original: {original_address}")
        print(f"Generated (SL): {generated_sl}")
        
        if generated_sl != "[FAKE_ADDRESS]":
             print("SUCCESS: SLM used for SL context.")
        else:
             print("FAILURE: SLM NOT used (Fallback returned).")

        # Test 2: International Context
        print("\n--- Test 2: International Context ---")
        generated_intl = generator.generate(original_address, "address", {"region": "INTL"})
        print(f"Generated (INTL): {generated_intl}")
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    test_slm_generation()
