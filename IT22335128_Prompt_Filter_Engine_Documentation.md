# IT22335128 - Prompt Filter Engine via MCP

## Overview
The Prompt Filter Engine via MCP provides context-aware privacy protection through real-time prompt filtering integrated with the Model Context Protocol (MCP). The system detects and redacts sensitive information (PII, health data, lifestyle preferences) from user prompts while enriching detected entities with contextual metadata. Currently, users can submit prompts and receive detailed analysis of detected PIIs and sensitive information, with the context identification pipeline focusing on direct identifiable entities. The system is under active development with plans to fine-tune a specialized SLM model and create domain-specific datasets.

## Current Logic

### 1. Data Flow Architecture
The system operates through three interconnected components:
- **Web Client** (React + Vite): User interface for prompt submission and result visualization
- **MCP Server** (Node.js + Express): Implements Model Context Protocol for standardized communication
- **Prompt Filter Engine** (Python + FastAPI): Core processing engine for entity detection and context enrichment

### 2. Entity Detection Pipeline
The UniversalRedactor performs multi-pass entity detection using GLiNER (Generalist and Lightweight Named Entity Recognition) model:

**Pass 1 - Identity & PII (High Priority):**
- Entities: name, age, gender, ethnicity, phone number, email, address, SSN, driver license, financial situation, legal, employment, date
- Threshold: 0.3

**Pass 2 - Health & Medical (PHI):**
- Entities: physical health, mental health, disabilities, medications, allergies, family history, smoker, exercise hours, diet type
- Threshold: 0.3

**Pass 3 - Lifestyle & Preferences:**
- Entities: relationship status, sexual orientation, religious beliefs, favorite food, favorite hobbies, pet, movie genre, vacation preference
- Threshold: 0.3

### 3. Context Enrichment Pipeline
The system employs a two-phase context identification approach:

**Phase 1 - Rule-Based Context Identification:**
Applies deterministic logical rules based on entity type:
- **Age Analysis**: Maps numerical age → life stage (child/teen/adult/senior)
- **Email Analysis**: Extracts domain type (government/educational/work) and region (Sri Lanka/international)
- **Phone Analysis**: Identifies region (Sri Lanka/international) and carrier type (mobile/landline)
- **SSN/Driver License**: Validates format and determines issuing region
- **Date Analysis**: Parses and categorizes date types
- **Name/Gender/Ethnicity**: Applies standardized taxonomies

**Phase 2 - Window-Based Context Identification:**
Extracts ±50 words around each entity and applies keyword matching:
- **Employment Context**: Matches employment status, sector, and industry keywords
- **Financial Context**: Identifies financial status level indicators
- **Date Type Context**: Determines date purpose (birthday, appointment, etc.)

Context from Phase 1 (rule-based) takes precedence; Phase 2 (window-based) fills gaps.

### 4. Redaction Process
- Entities sorted by position (right-to-left) to maintain text integrity
- Each entity replaced with `[LABEL]` mask (e.g., `[NAME]`, `[EMAIL]`)
- Overlapping entities handled to prevent double redaction
- Audit log generated with original text, label, and enriched context

### 5. MCP Integration
- **SSE Transport**: Maintains persistent user-specific sessions via Server-Sent Events
- **Tool Definition**: `process_prompt` tool accepts user prompts and returns redacted text with analysis
- **Session Management**: Each client connection assigned unique `sessionId` for isolated processing
- **Error Handling**: Graceful fallback with original prompt if filter engine fails

## Key Principles
- **Context-Aware Redaction**: Beyond simple masking, the system enriches each entity with contextual metadata for informed decision-making
- **Multi-Pass Detection**: Three specialized passes ensure comprehensive coverage across PII, health, and lifestyle domains
- **Modular Architecture**: Rule-based and window-based processors work in tandem, allowing independent refinement
- **Real-Time Processing**: MCP integration enables synchronous filtering without breaking conversational flow
- **Privacy-First Design**: All sensitive data redacted before reaching LLM endpoints

## Constraints & Challenges

### 1. PII Detection Model Selection
**Challenge**: Finding a suitable pre-trained model capable of detecting diverse entity types (personal, health, lifestyle) without extensive fine-tuning.

**Solution**: Adopted GLiNER medium-v2.1, a generalist NER model that accepts custom label sets at inference time, eliminating need for domain-specific retraining.

**Limitation**: Detection accuracy varies by entity type; currently operates at 0.3 threshold, resulting in some false positives/negatives.

### 2. Context Identification Accuracy
**Challenge**: Determining meaningful context for detected entities beyond surface-level labels.

**Solution**: Implemented dual-phase pipeline:
- **Logical Form (Rule-Based)**: Deterministic rules for structured entities (emails, phones, dates)
- **Window-Based**: Keyword matching in surrounding text for unstructured entities (employment, financial status)

**Limitation**: Window-based approach relies on keyword proximity, which may miss implicit context or misinterpret ambiguous phrasing.

### 3. MCP Integration Complexity
**Challenge**: Managing user-specific sessions in stateless HTTP/SSE environment while maintaining MCP protocol compliance.

**Solution**: SSEServerTransport generates unique `sessionId` per connection, stored in Map structure for session-to-transport mapping.

**Limitation**: Session cleanup depends on client disconnect events; unhandled connection drops may cause memory leaks over time.

### 4. Dataset Availability
**Constraint**: No existing labeled datasets for multi-domain entity detection with context annotations.

**Current Approach**: Using synthetic test data and real-world examples for validation. Unit tests employ mocks to simulate GLiNER model behavior.

**Future Work**: Create domain-specific dataset for fine-tuning a specialized SLM model tailored to conversational prompt filtering.

## Architecture Diagram

```
┌─────────────────┐
│   Web Client    │ (React + MCP Client SDK)
│  (Port: 5173)   │
└────────┬────────┘
         │ SSE Connection + Tool Calls
         │
┌────────▼────────┐
│   MCP Server    │ (Express + MCP SDK)
│  (Port: 3001)   │
│                 │
│ • SSE Transport │
│ • Session Mgmt  │
│ • Tool: process_prompt
└────────┬────────┘
         │ HTTP POST /filter
         │
┌────────▼────────┐
│ Filter Engine   │ (FastAPI + GLiNER)
│  (Port: 3003)   │
│                 │
│ ┌─────────────┐ │
│ │ Universal   │ │
│ │ Redactor    │ │
│ │             │ │
│ │ 3-Pass      │ │
│ │ Detection   │ │
│ └──────┬──────┘ │
│        │        │
│ ┌──────▼──────┐ │
│ │  Context    │ │
│ │  Pipeline   │ │
│ │             │ │
│ │ • Rule-Based│ │
│ │ • Window    │ │
│ └─────────────┘ │
└─────────────────┘
```

## Technology Stack

### Frontend
- **React 18**: Component-based UI
- **Vite**: Build tool and dev server
- **Tailwind CSS**: Utility-first styling
- **MCP Client SDK**: Protocol-compliant client implementation

### Backend - MCP Server
- **Node.js**: Runtime environment
- **Express 5**: Web framework
- **@modelcontextprotocol/sdk**: Official MCP implementation
- **SSE Transport**: Real-time bidirectional communication

### Backend - Filter Engine
- **Python 3.x**: Core processing language
- **FastAPI**: High-performance async API framework
- **GLiNER**: Generalist Named Entity Recognition model (urchade/gliner_medium-v2.1)
- **Uvicorn**: ASGI server

## Current Capabilities

### Detection Coverage
- **PII**: Names, ages, contact info, identifiers (SSN, DL)
- **Health**: Conditions, medications, allergies, health behaviors
- **Lifestyle**: Preferences, beliefs, relationships, hobbies

### Context Enrichment
- **Structural**: Email domain types, phone carrier types, license formats
- **Demographic**: Age-based life stages, regional identifiers
- **Behavioral**: Employment sectors, financial indicators, date purposes

### Output Formats
1. **Redacted Text**: Original prompt with entities masked
2. **Audit Log**: List of redactions with labels and context
3. **Enriched Analysis**: Detailed JSON with entity positions, confidence scores, and contextual metadata

## Testing Strategy
- **Unit Tests**: Mocked GLiNER and ContextPipeline to enable fast execution
- **Test Coverage**: Initialization, basic redaction, multi-pass aggregation, overlapping entities, context enrichment
- **Synthetic Data**: Custom test cases covering edge cases (overlaps, multiple entity types, context variations)

## Future Development

### Phase 1: Model Optimization
- Fine-tune specialized SLM model for prompt filtering domain
- Create annotated dataset with context labels
- Improve detection accuracy beyond current 0.3 threshold

### Phase 2: Context Enhancement
- Expand window-based patterns for better coverage
- Implement NLP-based context extraction (semantic similarity, dependency parsing)
- Add confidence calibration for context predictions

### Phase 3: Production Readiness
- Implement persistent session storage (Redis/database)
- Add rate limiting and request validation
- Create monitoring dashboard for detection metrics
- Optimize for latency (model quantization, caching)

### Phase 4: LLM Integration
- Feed enriched entities as structured context to LLMs
- Enable privacy-preserving conversations with contextual awareness
- Implement user consent management for context usage

## API Endpoints

### Filter Engine (Port 3003)
- `GET /health`: Service health check
- `POST /filter`: Process prompt and return redacted text with analysis
  - Request: `{ "prompt": "string" }`
  - Response: `{ "original": "string", "redacted": "string", "enriched_analysis": [...] }`

### MCP Server (Port 3001)
- `GET /`: Server status
- `GET /sse`: Establish SSE connection for MCP transport
- `POST /message?sessionId={id}`: Handle MCP protocol messages

### MCP Tools
- `process_prompt`: Main tool for prompt filtering
  - Input: `{ "prompt": "string" }`
  - Output: Formatted text with redacted content and analysis summary

## Development Status
**Current**: Functional prototype with multi-pass detection, dual-phase context enrichment, and MCP integration. Focuses on direct identifiable entities with rule-based and window-based context extraction.

**In Progress**: Model accuracy improvements, context identification refinement, session management optimization.

**Planned**: SLM fine-tuning, custom dataset creation, NLP-based context extraction, production deployment.

---

*Document Version: 1.0*  
*Last Updated: December 19, 2025*  
*Student ID: IT22335128*A
