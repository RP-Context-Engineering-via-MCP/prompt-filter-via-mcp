import random
import re
import ipaddress
from typing import Optional
from prompt_filter_engine.slm_entity_generator.inference import FineTunedAnonymizer

class EntityValueGenerator:
    def __init__(self):
        print("Initializing Entity Value Generator...")
        print("Initializing Entity Value Generator...")
        try:
            self.address_engine = FineTunedAnonymizer()
        except Exception as e:
            print(f"Warning: Could not load SLM model ({e}). Address generation may fail.")
            self.address_engine = None

    def generate(self, original_text: str, entity_type: str, context: dict = None) -> str:
        """
        Routes the generation to the correct method based on entity type.
        """
        entity_type = entity_type.lower()
        context = context or {}
        
        # Dispatch table
        if "ip" in entity_type:
            return self._generate_ip(original_text)
            
        elif "address" in entity_type:
            # Check context for region
            region_context = "SL"
            if context.get("region") in ["INTL", "international"]:
                region_context = "INTL"
            return self._generate_address(original_text, region_context)
            
        elif "phone" in entity_type:
             region_context = "SL"
             if context.get("region") == "INTL":
                 region_context = "INTL"
             return self._generate_phone(region_context)
             
        elif "bank" in entity_type or "account" in entity_type:
            return self._generate_bank(original_text)
            
        elif "age" in entity_type:
            return self._generate_age(original_text)
            
        else:
            # Fallback: simple masking if no generator exists
            return f"[ANONYMIZED_{entity_type.upper()}]"

    def _generate_address(self, original: str, context: str) -> str:
        if self.address_engine:
            try:
                return self.address_engine.predict(original, context=context)
            except Exception as e:
                print(f"SLM Generation failed: {e}")
        return "[ANONYMIZED_ADDRESS]"

    def _generate_phone(self, context: str) -> str:
        if context == "SL":
            prefixes = ["70", "71", "72", "74", "75", "76", "77", "78"]
            prefix = random.choice(prefixes)
            number = "".join([str(random.randint(0, 9)) for _ in range(7)])
            return f"+94{prefix}{number}"
        else:
            # Generic International (US-like fallback)
            area = random.randint(200, 999)
            part1 = random.randint(100, 999)
            part2 = random.randint(1000, 9999)
            return f"+1 ({area}) {part1}-{part2}"

    def _generate_bank(self, original: str) -> str:
        # Extract only digits to get length
        digits = re.sub(r"\D", "", original)
        length = len(digits)
        if length == 0:
            length = 10 # Default fallback
            
        # Generate new random string of digits
        new_account = "".join([str(random.randint(0, 9)) for _ in range(length)])
        return new_account

    def _generate_ip(self, original: str) -> str:
        try:
            ip = ipaddress.ip_address(original.strip())
            
            if isinstance(ip, ipaddress.IPv4Address):
                # Class detection
                first_octet = int(original.split('.')[0])
                
                if 0 <= first_octet <= 127: # Class A
                    return f"{random.randint(1, 126)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
                elif 128 <= first_octet <= 191: # Class B
                    return f"{random.randint(128, 191)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
                elif 192 <= first_octet <= 223: # Class C
                    return f"{random.randint(192, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
                else:
                    # Class D/E or other, return a safe random Class C
                    return f"192.168.{random.randint(0, 255)}.{random.randint(1, 254)}"
            
            elif isinstance(ip, ipaddress.IPv6Address):
                # Generate random IPv6
                return str(ipaddress.IPv6Address(random.randint(0, 2**128-1)))
                
        except ValueError:
            pass
            
        # Fallback if parsing failed
        return "192.168.10.10"

    def _generate_age(self, original: str) -> str:
        # Try to parse age
        try:
            match = re.search(r"\d+", original)
            if not match:
                return str(random.randint(20, 50))
            
            age = int(match.group())
            
            # Stages
            if 0 <= age <= 12: # Child
                new_age = random.randint(0, 12)
            elif 13 <= age <= 19: # Teen
                new_age = random.randint(13, 19)
            elif 20 <= age <= 59: # Adult
                new_age = random.randint(20, 59)
            else: # Senior
                new_age = random.randint(60, 99)
                
            # Try to ensure it's different if possible (unless range is tiny)
            if new_age == age and age < 99:
                new_age += 1
                
            return str(new_age)
            
        except:
            return "30"
