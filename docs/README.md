# Embroker AI Insurance Chatbot

An advanced AI-powered insurance interaction platform that transforms complex insurance processes through intelligent multi-agent communication and innovative technology. Built with Flask, OpenAI GPT-4o, and integrated with real-time external APIs for comprehensive risk assessment and classification.

![Embroker AI](https://img.shields.io/badge/AI-Powered-blue) ![Insurance](https://img.shields.io/badge/Industry-Insurance-green) ![Flask](https://img.shields.io/badge/Framework-Flask-red) ![OpenAI](https://img.shields.io/badge/AI-GPT--4o-orange)

##  Features

### Core Capabilities
- **AI-Powered Chat Interface**: ChatGPT-style conversational interface for natural insurance consultations
- **Real-Time Risk Assessment**: Automated company analysis and risk evaluation using external classification APIs
- **Multi-Agent Architecture**: Specialized agents for different insurance domains and processes
- **Vector Knowledge Base**: Pinecone integration for accurate, context-aware responses
- **Slack Integration**: Seamless escalation to human specialists with real-time messaging
- **External API Integration**: Live company classification using https://emb-classification.onrender.com/classify

### Advanced Features
- **Parallel Monitoring Agent (PMA)**: Independent monitoring system for conversation analysis and smart escalation
- **Dynamic Risk Reports**: 500-1000 word professional risk assessment reports with NAICS codes
- **Company Classification**: Automatic industry analysis with confidence scoring and Embroker class codes
- **Conversational Applications**: Complete insurance application workflow through natural chat
- **Background Processing**: Non-blocking company analysis and risk assessment generation

##  Architecture

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
│                  Multi-Agent System                         │
│  Insurance Agent • Risk Assessment • Background Analysis    │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────┼───────────────────────────────────────┐
│    External APIs    │    Knowledge Base    │    Database    │
│  • Classification   │  • OpenAI Vector     │  • PostgreSQL  │
│  • NAICS Lookup     │  • Pinecone Index    │  • Sessions    │
│  • Company Data     │  • Insurance Docs    │  • Logs        │
└─────────────────────┴───────────────────────────────────────┘
```

### Agent Architecture
- **Main Insurance Agent** (`agents_insurance_chatbot.py`): Primary customer-facing AI
- **Background Agent** (`background_agent.py`): Company analysis and classification
- **Risk Assessment Agent** (`risk_assessment_agent.py`): Professional report generation
- **Application Agent** (`application_agent.py`): Conversational insurance applications
- **Escalation Agent** (`escalation_agent.py`): Human specialist coordination
- **Conversation Coordinator** (`conversation_coordinator.py`): Session and message routing

##  Technology Stack

### Backend
- **Framework**: Flask with SQLAlchemy
- **AI Models**: OpenAI GPT-4o, o3-mini for enhanced reasoning
- **Vector Database**: OpenAI Vector Store + Pinecone backup
- **Database**: PostgreSQL with connection pooling
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

##  Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL database
- OpenAI API key
- Slack workspace (optional)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd embroker-insurance-chatbot
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
   python -c "from app import app, db; app.app_context().push(); db.create_all()"
   ```

5. **Start the application**
   ```bash
   # Development server
   python app.py

   # Production server
   gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
   ```

### Environment Configuration

```bash
# Required API Keys
POC_OPENAI_API=sk-proj-...              # Primary API key for main chat agent
OPENAI_MONITORING_KEY=sk-proj-...       # Dedicated API key for Parallel Monitoring Agent
SESSION_SECRET=your-session-secret

# Database
DATABASE_URL=postgresql://user:pass@host:port/dbname

# Optional Slack Integration
SLACK_BOT_TOKEN=xoxb-...
SLACK_ESCALATION_CHANNEL=C08GE53HL85
```

## 📊 Key Workflows

### 1. User Registration & Risk Assessment
```
User Registration → Email Domain Extraction → Classification API Call → 
Risk Assessment Generation → Professional Report (500-1000 words)
```

### 2. Chat Interaction Flow
```
User Message → Vector Knowledge Search → AI Response Generation → 
Parallel Monitoring → Escalation Decision → Specialist Alert (if needed)
```

### 3. Insurance Application Process
```
Application Start → Background Data Integration → Conversational Questions → 
Progress Tracking → Completion Summary → Quote Generation
```

##  API Integration

### External Classification API
- **Endpoint**: `https://emb-classification.onrender.com/classify`
- **Input**: Company name and website URL
- **Output**: NAICS codes, industry classification, confidence scores
- **Response Time**: 20-40 seconds for comprehensive analysis

### Data Flow
1. User registers with company email
2. System extracts domain (e.g., `jeff@embroker.com` → `https://embroker.com`)
3. Sends `companyName` + `websiteUrl` to classification API
4. Receives detailed industry analysis with 80%+ confidence
5. Generates customized risk assessment starting with classification data

##  Performance Metrics

- **Response Time**: 4-12 seconds for complete risk assessments
- **Report Length**: 5,000-8,000 characters (500-1000 words)
- **API Integration**: 30-second external classification processing
- **Concurrent Users**: Supports multiple simultaneous conversations
- **Accuracy**: 83%+ confidence in company classifications

## 🔧 Development

### Project Structure
```
├── agents/                     # AI agent implementations
├── integrations/               # External service integrations
├── templates/                  # HTML templates
├── attached_assets/            # Insurance documentation
├── app.py                     # Main Flask application
├── models.py                  # Database models
├── main.py                   # Application entry point
└── requirements.txt          # Python dependencies
```

### Key Components
- **Vector Knowledge Base**: Embroker-specific insurance documentation
- **Logging System**: Comprehensive analytics and error tracking
- **Session Management**: Persistent conversation state
- **Mobile Optimization**: Responsive design for all devices

##  Security Features

- **API Key Management**: Separate keys for main system and monitoring
- **Session Encryption**: Secure session management
- **Database Security**: Connection pooling with SSL
- **Input Validation**: Sanitized user inputs and API responses

##  User Experience

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

### Replit Deployment (Recommended)
1. Connect repository to Replit
2. Configure environment variables
3. Use "Start application" workflow for production
4. Automatic SSL and domain management

### Manual Deployment
```bash
# Production server
gunicorn --bind 0.0.0.0:5000 --workers 2 --reload main:app
```

##  Analytics & Monitoring

- **Built-in Dashboard**: `/admin/logs` for system analytics
- **Performance Tracking**: Response times, token usage, model metrics
- **Error Management**: Comprehensive logging with severity levels
- **Conversation Analytics**: User engagement and escalation patterns
t

## License

This project is proprietary software developed for Embroker's insurance technology platform.


---

**Built with by the Embroker Engineering Team**

*Transforming insurance through AI-powered conversation and intelligent automation.*
