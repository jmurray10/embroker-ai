# AI Insurance Chatbot - Libraries & Dependencies

## Overview
This document provides a comprehensive list of all libraries and dependencies used in the AI Insurance Chatbot project, along with their purposes and current versions.

## Core AI & Machine Learning Libraries

### OpenAI (v1.86.0)
- **Purpose**: Primary AI library for chat completions, embeddings, and intelligent agent interactions
- **Current Version**: 1.86.0 (Latest available: 1.97.1)
- **Models Used**:
  - `gpt-4.1-2025-04-14` - Main reasoning model (latest)
  - `gpt-4o` - Optimized GPT-4 for faster responses
  - `gpt-4o-mini-2024-07-18` - Fast model for quick operations
  - `gpt-4` - Standard GPT-4 for complex reasoning
  - `text-embedding-3-small` - Latest embedding model
  - `text-embedding-ada-002` - Legacy embedding model
- **Usage**: All agent implementations, vector search, knowledge retrieval

### Pinecone
- **Purpose**: Vector database for semantic search and knowledge retrieval
- **Features**:
  - High-performance similarity search
  - Scalable vector storage
  - Real-time updates
- **Usage**: Backup/alternative to OpenAI's vector store for insurance document search

## Web Framework & Extensions

### Flask
- **Purpose**: Core web application framework
- **Extensions Used**:
  - **Flask-SocketIO**: Real-time bidirectional communication for chat
  - **Flask-SQLAlchemy**: Database ORM integration
- **Features**:
  - RESTful API endpoints
  - Template rendering
  - Session management
  - WebSocket support for live chat

### Werkzeug
- **Purpose**: WSGI utility library (Flask dependency)
- **Features**: Request/response handling, security utilities

## Database & ORM

### SQLAlchemy
- **Purpose**: SQL toolkit and Object-Relational Mapping
- **Features**:
  - Database abstraction
  - Model definitions
  - Query builder
- **Models**: User, Conversation, Message

### PostgreSQL (Optional)
- **Purpose**: Production database for conversation persistence
- **Connection**: Via DATABASE_URL environment variable

## Communication & Integration

### Slack SDK
- **Purpose**: Integration with Slack for human agent escalation
- **Components**:
  - **slack_sdk**: Core SDK for Slack API interactions
  - **Socket Mode**: Real-time event handling
  - **Web Client**: REST API interactions
- **Features**:
  - Automated escalation notifications
  - Bidirectional messaging
  - Interactive button components
  - Thread management

### Requests
- **Purpose**: HTTP library for API calls
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

### python-dotenv
- **Purpose**: Environment variable management
- **Usage**: Loading .env file for API keys and configuration

### json
- **Purpose**: JSON data serialization/deserialization
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