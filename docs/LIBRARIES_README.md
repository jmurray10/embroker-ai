# AI Insurance Chatbot - Libraries & Dependencies

## Overview
This document provides a comprehensive list of all libraries and dependencies used in the AI Insurance Chatbot project, along with their purposes and current versions.

## Important Note
This documentation has been updated to reflect the actual versions in requirements.txt. The primary discrepancy from the original documentation is the OpenAI library version (v1.12.0 instead of the documented v1.86.0). All other version numbers now match the actual implementation.

## Core AI & Machine Learning Libraries

### OpenAI (v1.12.0)
- **Purpose**: Primary AI library for chat completions, embeddings, and intelligent agent interactions
- **Current Version**: 1.12.0 (Note: Documentation referenced v1.86.0, but actual implementation uses v1.12.0)
- **Models Used**:
  - `gpt-4.1-2025-04-14` - Main reasoning model (latest)
  - `gpt-4o` - Optimized GPT-4 for faster responses
  - `gpt-4o-mini-2024-07-18` - Fast model for quick operations
  - `gpt-4` - Standard GPT-4 for complex reasoning
  - `text-embedding-3-small` - Latest embedding model
  - `text-embedding-ada-002` - Legacy embedding model
- **Usage**: All agent implementations, vector search, knowledge retrieval

### Pinecone (v3.0.0)
- **Purpose**: Vector database for semantic search and knowledge retrieval
- **Current Version**: 3.0.0 (pinecone-client)
- **Features**:
  - High-performance similarity search
  - Scalable vector storage
  - Real-time updates
- **Usage**: Backup/alternative to OpenAI's vector store for insurance document search

## Web Framework & Extensions

### Flask (v3.0.0)
- **Purpose**: Core web application framework
- **Current Version**: 3.0.0
- **Extensions Used**:
  - **Flask-SocketIO (v5.3.5)**: Real-time bidirectional communication for chat
  - **Flask-SQLAlchemy (v3.1.1)**: Database ORM integration
- **Features**:
  - RESTful API endpoints
  - Template rendering
  - Session management
  - WebSocket support for live chat

### Werkzeug
- **Purpose**: WSGI utility library (Flask dependency)
- **Features**: Request/response handling, security utilities

## Database & ORM

### SQLAlchemy (v2.0.23)
- **Purpose**: SQL toolkit and Object-Relational Mapping
- **Current Version**: 2.0.23
- **Features**:
  - Database abstraction
  - Model definitions
  - Query builder
- **Models**: User, Conversation, Message

### PostgreSQL (v2.9.9)
- **Purpose**: Production database for conversation persistence
- **Current Version**: 2.9.9 (psycopg2-binary)
- **Connection**: Via DATABASE_URL environment variable

## Communication & Integration

### Slack SDK (v3.26.1)
- **Purpose**: Integration with Slack for human agent escalation
- **Current Version**: 3.26.1 (slack-sdk)
- **Components**:
  - **slack_sdk**: Core SDK for Slack API interactions
  - **Socket Mode**: Real-time event handling
  - **Web Client**: REST API interactions
- **Features**:
  - Automated escalation notifications
  - Bidirectional messaging
  - Interactive button components
  - Thread management

### Requests (v2.31.0)
- **Purpose**: HTTP library for API calls
- **Current Version**: 2.31.0
- **Usage**: External API integrations (NAIC classification API)

## Async & Concurrency

### asyncio
- **Purpose**: Asynchronous I/O framework
- **Usage**: 
  - Parallel agent operations
  - Non-blocking API calls
  - Concurrent message processing

### threading
- **Purpose**: Multi-threading support
- **Usage**: 
  - Parallel Monitoring Agent (PMA) background operation
  - Slack Socket Mode handler
  - Independent monitoring without blocking main chat

## Utilities & Support

### python-dotenv (v1.0.0)
- **Purpose**: Environment variable management
- **Current Version**: 1.0.0
- **Usage**: Loading .env file for API keys and configuration

### Additional HTTP Libraries
- **httpx (v0.23.3)**: Modern HTTP client with async support
- **aiohttp (v3.9.1)**: Asynchronous HTTP client/server framework
- **urllib3 (v2.1.0)**: HTTP library with thread-safe connection pooling

### Tokenization & Text Processing
- **tiktoken (v0.5.2)**: OpenAI's tokenizer for counting tokens in text

### Development Tools
- **gunicorn (v21.2.0)**: Python WSGI HTTP Server for production
- **pytest (v7.4.3)**: Testing framework
- **pytest-asyncio (v0.21.1)**: Async test support
- **black (v23.12.1)**: Code formatter
- **flake8 (v6.1.0)**: Style guide enforcement

### json
- **Purpose**: JSON data serialization/deserialization (built-in)
- **Usage**: API responses, configuration, message formatting

### uuid
- **Purpose**: Universally unique identifier generation
- **Usage**: Conversation IDs, session management

### logging
- **Purpose**: Application logging and debugging
- **Features**:
  - Multi-level logging (DEBUG, INFO, WARNING, ERROR)
  - File and console output
  - Structured log formatting

### time & datetime
- **Purpose**: Time-related operations
- **Usage**: Timestamps, session timeouts, rate limiting

### re (Regular Expressions)
- **Purpose**: Pattern matching and text processing
- **Usage**: Message parsing, validation

### os & sys
- **Purpose**: System-level operations
- **Usage**: File paths, environment access, system configuration

## Development Tools

### Gunicorn
- **Purpose**: Production WSGI HTTP Server
- **Configuration**: 2 workers, 60-second timeout
- **Usage**: Serving Flask application in production

### Type Hints
- **typing**: Type annotations for better code clarity
- **dataclasses**: Structured data objects with automatic methods

## Installation

To install all dependencies, ensure you have Python 3.11+ and run:

```bash
# Core dependencies are managed by Replit's package system
# For local development, create a requirements.txt with:

openai==1.86.0
flask
flask-socketio
flask-sqlalchemy
pinecone-client
slack-sdk
python-dotenv
requests
sqlalchemy
gunicorn
```

## Environment Variables Required

```bash
# OpenAI
POC_OPENAI_API=your_openai_api_key
OPENAI_MONITORING_KEY=optional_dedicated_monitoring_key

# Pinecone (Optional)
PINECONE_API_KEY=your_pinecone_key

# Slack Integration
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_APP_TOKEN=your_slack_app_token
SLACK_ESCALATION_CHANNEL=#channel-name

# Database (Optional)
DATABASE_URL=postgresql://...

# Flask
SESSION_SECRET=your_secret_key
```

## Architecture Notes

- **Multi-Agent System**: Uses OpenAI for different specialized agents
- **Real-time Communication**: Flask-SocketIO enables live chat updates
- **Vector Search**: Dual support for Pinecone and OpenAI vector stores
- **Async Operations**: Non-blocking design for scalability
- **Human-in-the-Loop**: Slack integration for escalation when needed

## Version Management

The project uses modern Python patterns and is compatible with Python 3.11+. All dependencies follow semantic versioning, and the project is designed to work with the latest stable versions of all libraries.