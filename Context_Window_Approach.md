# Context Window Approach for Entity Context Identification

## Overview

The system employs a **bidirectional context window** approach to identify and enrich entity context. This method extracts **50 words backward** and **50 words forward** from each detected entity, creating a contextual environment for semantic analysis.

## How It Works

### 1. Window Extraction Process

When an entity is detected in the text (e.g., "Software Engineer" at position 120-137):

1. **Backward Window**: Extract 50 words before the entity's start position
2. **Forward Window**: Extract 50 words after the entity's end position
3. **Combine**: Merge both windows into a single context string

```python
def extract_window(self, text: str, start: int, end: int, words: int = 50) -> str:
    """Extract ±N words around entity"""
    # Find word boundaries
    before = text[:start].split()[-words:]  # Last 50 words before entity
    after = text[end:].split()[:words]      # First 50 words after entity
    
    window = ' '.join(before + after)
    return window.lower()
```

### 2. Keyword Matching

The extracted window text undergoes keyword pattern matching to identify:

- **Employment Context**: Employment status (employed/unemployed/student/retired), sector (government/private/self-employed), industry (IT/healthcare/education/finance)
- **Financial Context**: Financial situation levels (low/middle/high income)
- **Date Context**: Date types (birth/employment/medical/event dates)

### 3. Context Enrichment Pipeline

**Phase 1**: Rule-based context extraction (structure and patterns)  
**Phase 2**: Window-based keyword matching (semantic context)  
**Final**: Merge both phases with rule-based taking precedence

## Example

**Input Text**: "John works as a Software Engineer at Google. He has been employed at the tech company since 2020 and enjoys his position..."

**Detected Entity**: "Software Engineer" (label: employment)

**Window Extraction** (50 words backward + 50 words forward):
- Backward: "john works as a"
- Forward: "at google he has been employed at the tech company since 2020 and enjoys his position..."

**Keyword Matching Results**:
- Employment Status: "employed" (matched: "employed at")
- Sector: "private" (matched: "company")
- Industry: "IT" (matched: "software", "tech", "engineer")

**Enriched Output**:
```json
{
  "text": "Software Engineer",
  "label": "employment",
  "context": {
    "employment_status": "employed",
    "sector": "private",
    "industry": "IT",
    "confidence": 0.8
  }
}
```

## Benefits

- **Captures local semantic meaning** without processing entire document
- **Computationally efficient** with fixed window size
- **Handles long documents** by focusing on relevant surrounding text
- **Balances precision** between immediate context and broader meaning
