# Embroker AI Insurance Chatbot

An advanced AI-powered insurance interaction platform that transforms complex insurance processes through intelligent multi-agent communication and innovative technology. Built with Flask, OpenAI GPT-4o, Pinecone vector database, and integrated with real-time external APIs for comprehensive risk assessment and classification.

![Embroker AI](https://img.shields.io/badge/AI-Powered-blue) ![Insurance](https://img.shields.io/badge/Industry-Insurance-green) ![Flask](https://img.shields.io/badge/Framework-Flask-red) ![OpenAI](https://img.shields.io/badge/AI-GPT--4o-orange) ![Pinecone](https://img.shields.io/badge/Vector-Pinecone-purple)

## 🚀 Features

### Core Capabilities
- **AI-Powered Chat Interface**: ChatGPT-style conversational interface for natural insurance consultations
- **Real-Time Risk Assessment**: Automated company analysis and risk evaluation using external classification APIs
- **Multi-Agent Architecture**: Specialized agents organized by function for different insurance domains
- **Vector Knowledge Base**: Pinecone-powered insurance knowledge retrieval system
- **Slack Integration**: Seamless escalation to human specialists with real-time messaging
- **External API Integration**: Live company classification using https://emb-classification.onrender.com/classify

### Advanced Features
- **Parallel Monitoring Agent (PMA)**: Independent monitoring system for conversation analysis and smart escalation
- **Dynamic Risk Reports**: 500-1000 word professional risk assessment reports with NAICS codes
- **Company Classification**: Automatic industry analysis with confidence scoring and Embroker class codes
- **Conversational Applications**: Complete insurance application workflow through natural chat
- **Background Processing**: Non-blocking company analysis and risk assessment generation

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Interface                        │
│  ChatGPT-style UI • Real-time Chat • Mobile Responsive     │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────┐
│                   Flask Application                         │
│     Main Server • Session Management • API Routing         │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────┐
│              Organized Multi-Agent System                   │
│  Core • Analysis • Customer Service • Monitoring • Format   │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────┼───────────────────────────────────────┐
│    External APIs    │  Vector Knowledge Base │   Database    │
│  • Classification   │  • Pinecone Index      │  • SQLAlchemy │
│  • NAICS Lookup     │  • Insurance Docs      │  • Sessions   │
│  • Company Data     │  • Embeddings          │  • SQLite Logs│
└─────────────────────┴───────────────────────────────────────┘
```

### Agent Organization (Updated Structure)

```
agents/
├── core/                              # Main orchestration
│   ├── agents_insurance_chatbot.py    # Primary customer-facing AI
│   └── conversation_coordinator.py    # Session management
├── analysis/                          # Business analysis & risk
│   ├── background_agent.py            # Company analysis
│   ├── risk_assessment_agent.py       # Risk reports
│   └── underwriting_agent.py          # Underwriting decisions
├── customer_service/                  # Application handling
│   ├── application_agent.py           # Application processing
│   └── conversational_application_agent.py
├── monitoring/                        # Real-time monitoring
│   ├── parallel_monitoring_agent.py   # Conversation monitoring
│   └── escalation_agent.py            # Human handoff
└── formatting/                        # Report formatting
    └── risk_formatter_agent.py        # Professional formatting
```

## 🛠️ Technology Stack

### Backend
- **Framework**: Flask with SQLAlchemy
- **AI Models**: GPT-4.1-2025-04-14 (primary), GPT-4o-mini-2024-07-18 (fast operations)
- **Vector Knowledge Base**: Pinecone (insurance-docs-index) with comprehensive Embroker documentation
- **Database**: PostgreSQL (optional) or SQLite for session storage
- **Real-time**: WebSocket support for live updates

### Frontend
- **Interface**: ChatGPT-style responsive design
- **JavaScript**: Vanilla JS with real-time polling
- **Styling**: CSS3 with custom variables and themes
- **Icons**: SVG-based arrow send buttons

### Integrations
- **Slack API**: Socket Mode for real-time specialist communication
- **Classification API**: External company analysis at https://emb-classification.onrender.com
- **OpenAI APIs**: Chat completions, embeddings, and vector search
- **Pinecone**: Primary vector knowledge base with Embroker-specific insurance documentation

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL database (optional)
- OpenAI API key
- Pinecone API key
- Slack workspace (optional)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/jmurray10/embroker-ai.git
   cd embroker-ai
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize database**
   ```bash
   python -c "from src.app import app, db; app.app_context().push(); db.create_all()"
   ```

5. **Start the application**
   ```bash
   # Development server
   python src/app.py

   # Production server
   gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
   ```

### Environment Configuration

```bash
# Required API Keys
POC_OPENAI_API=sk-proj-...              # Primary API key for main chat agent
OPENAI_MONITORING_KEY=sk-proj-...       # Dedicated API key for Parallel Monitoring Agent
PINECONE_API_KEY=pcsk_...               # Pinecone vector database
SESSION_SECRET=your-session-secret

# Database (Optional - uses SQLite by default)
DATABASE_URL=postgresql://user:pass@host:port/dbname  # Optional for production

# Optional Slack Integration
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...                # For Socket Mode
SLACK_ESCALATION_CHANNEL=C08GE53HL85
SLACK_SIGNING_SECRET=...
```

## 📊 Key Workflows

### 1. User Registration & Risk Assessment
```
User Registration → Email Domain Extraction → Classification API Call → 
Risk Assessment Generation → Professional Report (500-1000 words)
```

### 2. Chat Interaction Flow
```
User Message → Pinecone Knowledge Search → AI Response Generation → 
Parallel Monitoring → Escalation Decision → Slack Alert (if needed)
```

### 3. Insurance Application Process
```
Application Start → Background Data Integration → Conversational Questions → 
Progress Tracking → Completion Summary → Quote Generation
```

## 🎯 API Integration

### External Classification API
- **Endpoint**: `https://emb-classification.onrender.com/classify`
- **Input**: Company name and website URL
- **Output**: NAICS codes, industry classification, confidence scores
- **Response Time**: 20-40 seconds for comprehensive analysis

### Vector Knowledge Base Architecture
- **Pinecone** (`insurance-docs-index`) - Primary Knowledge Base
  - Embroker-specific insurance documentation
  - Policy templates and underwriting guidelines
  - Risk assessment criteria and claim examples
  - Industry-specific coverage recommendations
  - Used by all agents for knowledge retrieval
- **Note**: OpenAI's file_search tool is used internally by some agents for additional context

## 📈 Performance Metrics

- **Response Time**: 4-12 seconds for complete risk assessments
- **Report Length**: 5,000-8,000 characters (500-1000 words)
- **API Integration**: 30-second external classification processing
- **Concurrent Users**: Supports multiple simultaneous conversations
- **Accuracy**: 83%+ confidence in company classifications
- **Vector Search**: <1 second Pinecone query response with caching

## 🔧 Development

### Project Structure
```
├── agents/                     # AI agents organized by function
│   ├── core/                  # Main orchestration agents
│   ├── analysis/              # Risk and company analysis
│   ├── customer_service/      # Application handling
│   ├── monitoring/            # Real-time monitoring
│   └── formatting/            # Report formatting
├── integrations/              # External service integrations
│   ├── rag_pinecone.py       # Pinecone RAG implementation
│   ├── openai_vector_store.py # OpenAI vector fallback
│   └── slack_*.py            # Slack integrations
├── templates/                 # HTML templates
├── attached_assets/           # Insurance documentation PDFs
├── src/
│   ├── app.py               # Main Flask application
│   ├── models.py            # Database models
│   └── logger.py            # Logging system
└── main.py                   # Application entry point
```

### Key Components
- **Pinecone Knowledge Base**: Primary vector store with Embroker insurance documentation
- **Embroker Knowledge Base**: Enhanced wrapper combining Pinecone and OpenAI sources
- **Logging System**: Comprehensive analytics and error tracking  
- **Session Management**: Persistent conversation state with coordinator
- **Background Analysis**: Asynchronous company classification and risk assessment

## 🔐 Security Features

- **API Key Management**: Separate keys for different services
- **Session Encryption**: Secure session management
- **Database Security**: Connection pooling with SSL
- **Input Validation**: Sanitized user inputs and API responses
- **Slack Signature Verification**: Ensures webhook security

## 📱 User Experience

### ChatGPT-Style Interface
- Clean, minimal design without chat bubbles
- Black arrow send buttons for modern aesthetics
- Responsive layout for desktop and mobile
- Real-time message delivery and typing indicators

### Professional Features
- Background risk analysis with notification system
- Hamburger menu for report access
- Specialist escalation with dedicated chat panels
- Progress tracking for insurance applications

## 🚀 Deployment

### Docker Deployment (Recommended for Local Testing)
```bash
# Quick start
cp .env.docker.example .env
# Add your API keys to .env
docker-compose up -d

# Access at http://localhost:5000
```

See [DOCKER_README.md](./DOCKER_README.md) for detailed Docker instructions.

### Replit Deployment (Cloud)
1. Connect repository to Replit
2. Configure environment variables
3. Use "Start application" workflow for production
4. Automatic SSL and domain management

### Manual Deployment
```bash
# Install dependencies
pip install -r requirements.txt

# Production server with workers
gunicorn --bind 0.0.0.0:5000 --workers 2 --reload main:app
```

## 📊 Analytics & Monitoring

- **Built-in Dashboard**: `/admin/logs` for system analytics
- **Performance Tracking**: Response times, token usage, model metrics
- **Error Management**: Comprehensive logging with severity levels
- **Conversation Analytics**: User engagement and escalation patterns
- **Vector Search Analytics**: Query performance and relevance tracking

## 📄 License

This project is proprietary software developed for Embroker's insurance technology platform.


**Built by the Embroker Data Team**

*Transforming insurance through AI-powered conversation and intelligent automation.*