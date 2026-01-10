# Privacy Preserve prompt filter engine via MCP

An advanced privacy-focused system designed to detect and redact Personally Identifiable Information (PII) and User Sensitive Data from prompts in real-time. This system leverages the Model Context Protocol (MCP) for seamless integration and uses a fine-tuned Small Language Model (SLM) for intelligent data handling.

## Key Features

-   **Intelligent Redaction**: sophisticated multi-pass detection algorithm to identify and mask PII and User Sensitive Data.
-   **Context Enrichment**: Goes beyond simple matching by understanding the *context* of the data (e.g., distinguishing between a personal address and a business location).
-   **Model Context Protocol (MCP)**: Built on the standard Model Context Protocol, ensuring easy integration with various LLM orchestrators and clients.
-   **Real-Time Processing**: Provides instant feedback and redaction via Server-Sent Events (SSE), ensuring a smooth user experience.
-   **Privacy First**: Ensures sensitive user data is sanitized before it ever leaves your local environment or reaches an external LLM.

## Technology Stack

### Frontend
-   **React 18**: For a dynamic and responsive user interface.
-   **Vite**: Next-generation frontend tooling for fast builds and development.
-   **Tailwind CSS**: Utility-first CSS framework for rapid and modern UI styling.

### Middleware (MCP Server)
-   **Node.js**: The Javascript runtime powering the server.
-   **Express**: Fast, unopinionated, minimalist web framework for Node.js.
-   **MCP SDK**: Official SDK for implementing the Model Context Protocol.

### AI Engine & Backend
-   **Python**: The core language for the AI and data processing logic.
-   **FastAPI**: Modern, fast (high-performance) web framework for building APIs with Python.
-   **GLiNER**: A Generalist and Lightweight Named Entity Recognition model used for efficient entity detection.
-   **SLM (Small Language Model)**: `Qwen2.5-0.5B-Instruct` (Fine-tuned) for specialized anonymization and context-aware value generation.

## System Architecture

The system follows a modular architecture:

1.  **Web Client (Port 3002)**: The user interface where prompts are entered. It connects to the MCP Server.
2.  **MCP Server (Port 3001)**: Acts as the bridge. It receives prompts from the client, sends them to the Filter Engine for processing, and streams the results back to the client.
3.  **Prompt Filter Engine (Port 3003)**: The intelligence layer. It uses the GLiNER model to detect entities and the Qwen SLM to generate context-appropriate redacted values.

## Installation & Usage

To run the system, you need to start each component independently.

### Prerequisites
-   Node.js (v18 or higher recommended)
-   Python (v3.10 or higher recommended)

### 1. Start the Prompt Filter Engine (PFE)
Navigate to the engine directory and start the FastAPI server.
```bash
cd prompt_filter_engine
# Ensure you have your python environment activated and dependencies installed
python server.py
# Server runs on http://localhost:3003
```

### 2. Start the MCP Server
Navigate to the server directory, install dependencies (if new), and start the server.
```bash
cd mcp-server
npm install  # requests dependencies
npm start
# Server runs on http://localhost:3001
```

### 3. Start the Web Client
Navigate to the client directory and start the development server.
```bash
cd web-client
npm install  # requests dependencies
npm run dev
# Application runs on http://localhost:3002
```

## API Reference

-   **Web Client**: `http://localhost:3002` - Main User Interface.
-   **MCP Server**: `http://localhost:3001` - Handles MCP protocol messages and SSE connections.
-   **Filter Engine**: `http://localhost:3003` - internal API for redaction services (`POST /filter`).
