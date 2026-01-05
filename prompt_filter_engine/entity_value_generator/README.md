# Entity Value Generator

This module (`entity_value_generator`) is responsible for replacing sensitive PII/PHI entities with realistic fake values that maintain the original context.

## Logic Overview

The generation logic is handled by the `EntityValueGenerator` class in `generator.py`. It uses a combination of Rule-Based Generators and Small Language Models (SLM).

### Supported Entities

| Entity Type | Generation Method | Logic Details |
| :--- | :--- | :--- |
| **Address** | **SLM (Fine-Tuned Qwen)** | Uses a fine-tuned Qwen-0.5B model to generate addresses. It accepts a regional context (`SL` or `INTL`) to produce culturally accurate addresses (e.g., Sri Lankan vs. Western formats). |
| **Phone Number** | **Rule-Based** | **Sri Lanka (`SL`)**: Generates `+94` followed by a valid mobile prefix (e.g., 77, 71, 70) and 7 random digits.<br>**International (`INTL`)**: Generates a generic international format (e.g., `+1 (XXX) XXX-XXXX`). |
| **Bank Account** | **Rule-Based** | Preserves the **exact length** of the original account number. If the input is 12 digits, the output will be a new random 12-digit string. |
| **IP Address** | **Rule-Based (Smart)** | **IPv4**: Detects the Class (A, B, or C) of the original IP.<br>- **Class A**: generated `1-126.x.x.x`<br>- **Class B**: generated `128-191.x.x.x`<br>- **Class C**: generated `192-223.x.x.x`<br>**IPv6**: Generates a valid random IPv6 address. |
| **Age** | **Rule-Based (Stage-Aware)** | Detects the life stage of the original age and generates a new age within that same stage:<br>- **Child**: 0-12<br>- **Teen**: 13-19<br>- **Adult**: 20-59<br>- **Senior**: 60+ |

## Integration

To use this generator:

```python
from prompt_filter_engine.entity_value_generator.generator import EntityValueGenerator

generator = EntityValueGenerator()

# Example Usage
fake_val = generator.generate(
    original_text="192.168.1.5", 
    entity_type="ip address", 
    context={"region": "SL"}
)
# Result: "192.168.55.12" (Preserves Class C)
```
