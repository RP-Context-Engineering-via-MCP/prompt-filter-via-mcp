# Redactor Implementation & Testing Guide

## Overview
The `UniversalRedactor` uses the `GLiNER` model to detect and redact sensitive information (PII, Health, Lifestyle) from text. It runs in three passes for different entity groups and enriches the results with context.

## Usage

### 1. Installation
Ensure dependencies are installed:
```bash
pip install gliner
# other dependencies...
```

### 2. Basic Usage
```python
from prompt_filter_engine.pii_detection.redactor import UniversalRedactor

# Initialize (loads model)
redactor = UniversalRedactor()

# Redact text
text = "My name is John Doe and I live in Paris."
redacted_text, audit_log = redactor.redact(text)

print(redacted_text)
# Output: "My name is [NAME] and I live in [ADDRESS]."

print(audit_log)
# Output: ["Redacted 'John Doe' as name", "Redacted 'Paris' as address"]
```

## Testing

The tests use `unittest` and `unittest.mock` to simulate the heavy `GLiNER` model and `ContextPipeline`, allowing for fast execution without loading models.

### Running Tests
Navigate to the `prompt_filter_engine` directory and run:

```bash
python -m unittest discover -s tests
```

### Test Coverage
- **Initialization**: Verifies models are loaded with correct parameters.
- **Basic Redaction**: Checks that entities detected by the model are replaced with `[LABEL]`.
- **Multiple Passes**: Ensures entities from different categories (PII, Health, Lifestyle) are aggregated.
- **Overlapping Entities**: Verifies that entities are applied correctly even if they overlap (processed right-to-left).
- **Context Enrichment**: Checks that the audit log includes context information if available.
- **Return Enriched**: Verifies optional return of detailed entity data.
