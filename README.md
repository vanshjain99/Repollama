# Repollama 🦙🔍

Repollama is a local-first, privacy-focused repository intelligence and codebase indexing platform. It allows developers to analyze, visualize, and query codebases completely offline. By combining deterministic Abstract Syntax Tree (AST) parsing, Git history mining, local vector database storage, and private LLMs via Ollama, Repollama builds a comprehensive knowledge graph and semantic search index of any repository.

---

## 🎯 The Agenda

Modern software development relies heavily on third-party cloud-based AI tools for codebase understanding, which raises security, privacy, and connectivity concerns. Repollama's agenda is to provide:
1. **Total Privacy**: All analysis, parsing, embedding generation, and model inference run 100% locally.
2. **Deep Semantic & Structural Indexing**: Combine lexical syntax (AST trees) with semantic vector embeddings to understand not just words, but code structure and references.
3. **Temporal Context**: Incorporate Git histories, authorship, and file churn metrics to understand how code evolves over time.
4. **Intuitive UI**: A sleek, local desktop interface that developers can use to select workspaces, monitor indexing in real-time, and run queries.

---

## 💡 Key Use Cases

Repollama's use cases map directly to the core pillars of its agenda:

### 1. 🔒 Privacy-First Code Intelligence (Total Privacy)
- **Air-Gapped Analysis**: Query proprietary or sensitive codebases completely offline. Ideal for security-critical environments (defense, banking, healthtech) where sending code to cloud AI APIs is prohibited.
- **Local LLM Chat & Q&A**: Chat with your local codebase using offline models like Llama 3, Mistral, or Qwen (via Ollama), ensuring zero data telemetry or IP exposure.

### 2. 🕸️ AST & Semantic Navigation (Deep Semantic & Structural Indexing)
- **Structural Impact Analysis**: Use AST knowledge graphs to understand code references, class inheritance, and module imports, helping developers map out refactoring changes before executing them.
- **Natural Language Code Search**: Perform semantic queries (e.g., *"Find where user authentication tokens are signed"*) instead of relying on rigid keyword-based grep.

### 3. 📈 Git-History & Health Metrics (Temporal Context)
- **Technical Debt & Hotspot Auditing**: Trace code evolution using Git metadata and file churn analysis to find highly modified files or complex modules that are prone to bugs.
- **Ownership & Team Alignment**: Assess code ownership, authorship history, and developer contribution patterns over time to streamline knowledge transfer and team collaboration.

### 4. 🎛️ Unified Code Workspace (Intuitive UI)
- **Local Repository Cockpit**: A single desktop interface to select folders, watch indexing logs stream in real-time, visualize workspace statistics (AST nodes, commits, embeddings), and query files interactively.
- **Configurable Search & Chat Interface**: Easily toggle between different local LLM models and indexing options through a user-friendly UI without needing complex CLI commands.

---

## 👥 Target Audience

Repollama is built for:

- **🔒 Enterprise & DevSecOps Teams**: Organizations in highly regulated industries (e.g., Fintech, Healthtech, Government/Defense) requiring strictly audited, zero-data-leakage AI development tools.
- **💻 Privacy-First Software Engineers**: Developers who prefer keeping their codebase analysis, vector database, and inference models entirely on local hardware.
- **✈️ Remote & Offline Developers**: Engineers working in low-bandwidth, high-latency, or completely disconnected environments (e.g., flights, trains, remote sites).
- **🕸️ Software Architects & Tech Leads**: Technical leaders looking to visualize codebases, inspect module dependencies, analyze code churn, and streamline developer onboarding.
- **🛠️ Open-Source Enthusiasts**: Builders who want to leverage open-weights models (via Ollama) without relying on expensive monthly SaaS API subscriptions.

---

## 🛠️ What has been Built So Far

Repollama is divided into a headless Python backend core and a Tauri desktop frontend. Here is a breakdown of the architecture and features implemented:

### 1. Headless Backend Core (`/backend`)
Written in Python and managed using Poetry, the backend handles the heavy lifting of code ingestion, analysis, and API serving:
- **Ollama Connection Manager**: An async HTTPX-based connection manager (`OllamaManager`) that validates connections to the local Ollama instance and verifies model availability.
- **Deterministic AST Parser**: Leverages `tree-sitter` (specifically supporting Python, JavaScript, and TypeScript/TSX) to parse source code files and extract metadata about classes, function signatures, and imports.
- **Git Miner Engine**: Uses `GitPython` to query local repository metadata, parse git commit history, and track file churn metrics.
- **Knowledge Graph Builder**: Uses `NetworkX` to assemble AST elements, imports, and file structures into a queryable knowledge graph.
- **Local Vector Store**: Integrates `ChromaDB` to chunk code representations and manage local embeddings completely on-device.
- **Typer & Rich CLI**: A CLI engine (`repollama`) providing commands for:
  - `health`: Validates system environment (Docker, Ollama status, API health).
  - `models`: Lists locally installed Ollama models.
  - `parse`: Run the AST parser on a file.
  - `git`: Extract git metadata and churn.
  - `index`: Orchestrate directory traversal, AST parsing, and local vector store population.
- **FastAPI SSE API Server**: A FastAPI app exposing endpoint routes:
  - `/health`: Health status.
  - `/api/v1/analyze/stream`: An SSE (Server-Sent Events) endpoint that streams the progress of codebase parsing and indexing back to the client in real-time.

### 2. Desktop Frontend UI (`/frontend`)
A desktop shell that acts as the user interface for Repollama:
- **Tauri Integration**: Configured native desktop windows using Tauri v2 (Rust-under-the-hood).
- **React + TS + Tailwind CSS**: Built with a sleek, dark-themed, glassmorphic layout.
- **Native Directory Picker**: Integrates `@tauri-apps/plugin-dialog` to launch native folder-selection dialogs.
- **Real-Time Indexer Log Terminal**: A styled terminal component on the Dashboard that subscribes to the FastAPI SSE stream, displaying real-time parsing activities, errors, and indexing stats with smooth auto-scroll.
- **Dynamic Stats Board**: Visual indicators displaying the count of AST nodes, parsed git commits, and vector embeddings created upon index completion.

---

## 🚀 Getting Started

### Prerequisites
1. **Ollama**: Download and install [Ollama](https://ollama.com/) locally. Ensure the service is running.
2. **Node.js**: Version 18+ (for the frontend).
3. **Python**: Version 3.9+ with **Poetry** installed.

---

### Step 1: Run the Backend API

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Install Python dependencies:
   ```bash
   poetry install
   ```
3. Start the FastAPI development server:
   ```bash
   poetry run uvicorn repollama.main:app --reload
   ```
   *The backend will run on `http://127.0.0.1:8000`.*

---

### Step 2: Run the Desktop Frontend

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install frontend dependencies:
   ```bash
   npm install
   ```
3. Launch the Tauri development application:
   ```bash
   npx tauri dev
   ```
   *This compiles the Rust backend harness and runs the Vite development server to launch the desktop application window.*

---

## 🧪 Running Tests
To run backend unit and integration tests (such as API streams):
```bash
cd backend
poetry run pytest
```
