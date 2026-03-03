import random
import re
import string
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

        elif "driver" in entity_type or "license" in entity_type:
            return self._generate_driver_license(original_text, context)

        elif "api" in entity_type and "key" in entity_type:
            return self._generate_api_key(original_text)

        elif "credit" in entity_type or "card" in entity_type:
            return self._generate_credit_card(original_text)

        elif entity_type == "medical_condition":
            return self._generate_medical_condition(original_text, context)

        elif entity_type == "medication_name":
            return self._generate_medication(original_text, context)

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

    # ------------------------------------------------------------------
    # Driver License generator — format-aware
    # ------------------------------------------------------------------

    def _generate_driver_license(self, original: str, context: dict) -> str:
        """
        Generate a fake driver license number that matches the detected format.
        Formats:
          SL new:  2 uppercase letters + 8 digits  (e.g. AB12345678)
          SL old:  1 uppercase letter  + 7 digits  (e.g. B1234567)
          International: preserve length & alphanumeric charset
        """
        fmt = context.get("format_type", "international")
        clean = original.strip().upper()

        if fmt == "new_sl":
            letters = ''.join(random.choices(string.ascii_uppercase, k=2))
            digits  = ''.join(random.choices(string.digits, k=8))
            return f"{letters}{digits}"

        elif fmt == "old_sl":
            letter = random.choice(string.ascii_uppercase)
            digits = ''.join(random.choices(string.digits, k=7))
            return f"{letter}{digits}"

        else:
            # International fallback: preserve length, replace each char class
            length = max(len(re.sub(r'[\s\-]', '', clean)), 8)
            result = []
            for ch in clean:
                if ch.isdigit():
                    result.append(random.choice(string.digits))
                elif ch.isalpha():
                    result.append(random.choice(string.ascii_uppercase))
                elif ch in ('-', ' '):
                    result.append(ch)  # preserve separators
                else:
                    result.append(random.choice(string.ascii_uppercase + string.digits))
            return ''.join(result) if result else ''.join(
                random.choices(string.ascii_uppercase + string.digits, k=length)
            )

    # ------------------------------------------------------------------
    # API Key generator — format-preserving
    # ------------------------------------------------------------------

    def _generate_api_key(self, original: str) -> str:
        """
        Generate a fake API key that preserves length, prefix, and
        character set of the original.
        """
        clean = original.strip()
        if not clean:
            # Fallback: generic 32-char hex key
            return ''.join(random.choices(string.hexdigits[:16], k=32))

        # Detect a common prefix pattern like "sk-", "pk_live_", "AKIA", "ghp_"
        prefix_match = re.match(r'^([a-zA-Z]{2,6}[_\-])', clean)
        prefix = prefix_match.group(1) if prefix_match else ""
        body = clean[len(prefix):]

        # Determine the character set of the body
        has_upper = any(c.isupper() for c in body)
        has_lower = any(c.islower() for c in body)
        has_digit = any(c.isdigit() for c in body)
        body_len  = len(body)

        # Build charset
        charset = ""
        if has_upper:
            charset += string.ascii_uppercase
        if has_lower:
            charset += string.ascii_lowercase
        if has_digit:
            charset += string.digits
        if not charset:
            charset = string.ascii_letters + string.digits

        new_body = ''.join(random.choices(charset, k=body_len))
        return f"{prefix}{new_body}"

    # ------------------------------------------------------------------
    # Credit Card generator — network-aware with Luhn check digit
    # ------------------------------------------------------------------

    def _generate_credit_card(self, original: str) -> str:
        """
        Generate a fake credit card number that matches the card network
        (Visa, Mastercard, Amex) and passes the Luhn checksum.
        """
        digits_only = re.sub(r'\D', '', original)
        length = len(digits_only) if len(digits_only) >= 13 else 16

        # Detect card network from first digits
        if digits_only.startswith('4'):
            # Visa — starts with 4, usually 16 digits
            prefix = '4'
            target_len = 16
        elif digits_only[:2] in ('51', '52', '53', '54', '55'):
            # Mastercard — starts with 51-55, 16 digits
            prefix = digits_only[:2]
            target_len = 16
        elif digits_only[:2] in ('34', '37'):
            # Amex — starts with 34 or 37, 15 digits
            prefix = digits_only[:2]
            target_len = 15
        elif digits_only.startswith('6011') or digits_only.startswith('65'):
            # Discover
            prefix = digits_only[:4] if digits_only.startswith('6011') else '65'
            target_len = 16
        else:
            # Unknown — use Visa-like
            prefix = '4'
            target_len = length if length >= 13 else 16

        # Generate random middle digits (leave last for Luhn)
        middle_len = target_len - len(prefix) - 1
        middle = ''.join(random.choices(string.digits, k=middle_len))
        partial = prefix + middle

        # Compute Luhn check digit
        check = self._luhn_check_digit(partial)
        card_number = partial + str(check)

        # Format output to match original (spaces, dashes, or plain)
        if '-' in original:
            return self._format_card(card_number, '-')
        elif ' ' in original:
            return self._format_card(card_number, ' ')
        return card_number

    @staticmethod
    def _luhn_check_digit(partial: str) -> int:
        """Compute the Luhn check digit for a partial card number."""
        digits = [int(d) for d in partial]
        # Double every second digit from the right
        for i in range(len(digits) - 1, -1, -2):
            digits[i] *= 2
            if digits[i] > 9:
                digits[i] -= 9
        total = sum(digits)
        return (10 - (total % 10)) % 10

    @staticmethod
    def _format_card(number: str, separator: str) -> str:
        """Format card number with separator in groups of 4."""
        if len(number) == 15:  # Amex: 4-6-5
            return f"{number[:4]}{separator}{number[4:10]}{separator}{number[10:]}"
        # Default: groups of 4
        return separator.join(number[i:i+4] for i in range(0, len(number), 4))

    # ------------------------------------------------------------------
    # Health PHI generators — deterministic template lookup
    # Tier definitions:
    #   1 = Critical (mental health, substance use, sexual health)
    #   2 = High     (metabolic, cardiovascular, oncology, etc.)
    #   3 = Standard OTC → keep original text (non-sensitive)
    #   null → GLiNER false positive, caller already dropped entity;
    #           this method is never called for null, but returns original
    #           as a safety net
    # ------------------------------------------------------------------

    # Tier 1 & 2 condition templates (keyed by therapeutic_area)
    _CONDITION_TEMPLATES = {
        # Tier 1
        "mental_health":    "mental health condition",
        "substance_use":    "substance use condition",
        "sexual_health":    "confidential health condition",
        # Tier 2
        "metabolic":        "metabolic condition",
        "cardiovascular":   "cardiovascular condition",
        "respiratory":      "respiratory condition",
        "oncology":         "chronic health condition",
        "renal":            "chronic health condition",
        "autoimmune":       "chronic health condition",
        "neurological":     "neurological condition",
    }

    # Tier 1 & 2 medication templates (keyed by drug_class)
    _MEDICATION_TEMPLATES = {
        # Tier 1
        "antidepressant":       "antidepressant medication",
        "antipsychotic":        "antipsychotic medication",
        "mood_stabilizer":      "mood stabilizer medication",
        "anxiolytic":           "anxiety medication",
        "opioid_replacement":   "opioid replacement therapy",
        # Tier 2
        "antidiabetic":         "diabetes medication",
        "antihypertensive":     "blood pressure medication",
        "statin":               "cholesterol medication",
        "bronchodilator":       "respiratory medication",
        "inhalant":             "respiratory medication",
        "antihistamine":        "antihistamine medication",
        "NSAID":                "pain relief medication",
    }

    # Therapeutic area → Tier mapping (for condition fallback)
    _TIER_MAP = {
        "mental_health": 1, "substance_use": 1, "sexual_health": 1,
        "metabolic": 2, "cardiovascular": 2, "respiratory": 2,
        "oncology": 2, "renal": 2, "autoimmune": 2, "neurological": 2,
        "common_acute": 3,
    }

    def _generate_medical_condition(self, original_text: str, context: dict) -> str:
        """Generate synthetic replacement for a medical condition."""
        drug_class = context.get("drug_class")
        if drug_class:
            return drug_class

        tier             = context.get("effective_tier") or context.get("tier")
        therapeutic_area = context.get("therapeutic_area")

        # Tier 3 (OTC / non-sensitive) → keep original
        if tier == 3 or therapeutic_area == "common_acute":
            return original_text

        # Null tier → false positive, keep original (safety net)
        if tier is None:
            return original_text

        # Lookup by therapeutic_area
        if therapeutic_area and therapeutic_area in self._CONDITION_TEMPLATES:
            return self._CONDITION_TEMPLATES[therapeutic_area]

        # Generic fallback by tier
        return "health condition" if tier == 2 else "health condition"

    def _generate_medication(self, original_text: str, context: dict) -> str:
        """Generate synthetic replacement for a medication."""
        drug_class       = context.get("drug_class")
        if drug_class:
            return drug_class

        tier             = context.get("effective_tier") or context.get("tier")
        therapeutic_area = context.get("therapeutic_area")

        # Tier 3 → keep original
        if tier == 3 or therapeutic_area == "common_acute":
            return original_text

        # Null tier → false positive, keep original
        if tier is None:
            return original_text

        # Fallback to therapeutic_area-based label
        if therapeutic_area:
            ta_labels = {
                "mental_health": "mental health medication",
                "metabolic":     "metabolic medication",
                "cardiovascular": "cardiovascular medication",
                "respiratory":   "respiratory medication",
            }
            if therapeutic_area in ta_labels:
                return ta_labels[therapeutic_area]

        return "medication"
