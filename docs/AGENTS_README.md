# AI Insurance Chatbot - Multi-Agent Architecture

## Overview

The AI Insurance Chatbot uses a sophisticated multi-agent architecture to provide intelligent, context-aware insurance interactions. Each agent specializes in a specific aspect of the insurance workflow, working together to deliver comprehensive service.

## Agent Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         User Interface                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────┐
│                  Main Insurance Agent                        │
│         (agents/agents_insurance_chatbot.py)                 │
│  • Primary conversational interface                          │
│  • Knowledge retrieval from vector databases                 │
│  • Response generation with GPT-4                            │
└──────┬──────────────┬──────────────┬───────────────┬────────┘
       │              │              │               │
┌──────┴─────┐ ┌─────┴──────┐ ┌────┴─────┐ ┌──────┴────────┐
│Background  │ │Application │ │  Risk    │ │ Underwriting  │
│   Agent    │ │   Agent    │ │Assessment│ │    Agent      │
└────────────┘ └────────────┘ └──────────┘ └───────────────┘
       │
┌──────┴─────────────────────────────────────────────────────┐
│              Parallel Monitoring Agent (PMA)                │
│  • Runs asynchronously in background                        │
│  • Monitors all conversations for escalation triggers       │
└──────────────────────┬─────────────────────────────────────┘
                       │
┌──────────────────────┴─────────────────────────────────────┐
│         Conversation Coordinator & Escalation Agent         │
│  • Manages session states                                   │
│  • Handles Slack integration                                │
│  • Routes escalations to human specialists                  │
└─────────────────────────────────────────────────────────────┘
```

## Agent Descriptions and Functions

### 1. Main Insurance Agent (`agents/agents_insurance_chatbot.py`)

**Purpose**: Primary customer-facing AI that handles all insurance-related queries.

**Key Functions**:
- `process_message()`: Main entry point for processing user messages
- `search_insurance_knowledge()`: Searches vector databases (Pinecone/OpenAI) for relevant information
- `_create_function_tools()`: Defines available tools like web search and underwriting analysis
- `chat()`: Generates responses using GPT-4 with retrieved context

**Capabilities**:
- Multi-source knowledge retrieval (vector stores, knowledge base)
- Intelligent query routing to specialized agents
- Context-aware response generation
- Tool integration (web search, underwriting, risk assessment)

**Models Used**:
- Main reasoning: `gpt-4.1-2025-04-14`
- Fast operations: `gpt-4o-mini-2024-07-18`

### 2. Background Agent / Company Analysis Agent (`agents/background_agent.py`)

**Purpose**: Fetches and analyzes company information from external sources.

**Key Functions**:
- `analyze_company()`: Main analysis function
- `_fetch_naic_classification()`: Retrieves NAIC industry classification
- `_process_classification_response()`: Processes API responses
- Background caching for performance optimization

**Capabilities**:
- NAIC API integration for industry classification
- Company risk profile analysis
- Caching to reduce API calls
- Background processing for non-blocking operations

### 3. Risk Assessment Agent (`agents/risk_assessment_agent.py`)

**Purpose**: Generates detailed, professional risk assessment reports.

**Key Functions**:
- `generate_risk_assessment_report()`: Creates comprehensive risk reports
- `_build_enhanced_assessment_prompt()`: Structures data for AI analysis
- Integration with Embroker knowledge base for industry insights

**Capabilities**:
- Professional report generation using GPT-4
- Coverage recommendations with justifications
- Industry-specific risk analysis
- Real claim examples based on classification codes
- Formatted output for easy reading

**Report Sections**:
1. Executive Summary with operations overview
2. Risk Manager's Analysis
3. Coverage Recommendations (Tech E&O, EPLI, D&O, General Liability)
4. Industry-specific claim examples

### 4. Application Agent (`agents/application_agent.py`)

**Purpose**: Guides users through the insurance application process conversationally.

**Key Functions**:
- `start_application()`: Initiates new application session
- `process_application_response()`: Handles user inputs field by field
- `_validate_field()`: Ensures data quality and completeness
- `_generate_final_summary()`: Creates application summary for review

**Application Sections**:
1. Company Profile (name, website, description, revenue)
2. Technology & Security (tech stack, data handling)
3. Coverage Requirements (limits, deductibles)
4. Risk Management (policies, procedures)
5. Claims History

**Features**:
- Conversational data collection
- Real-time validation
- Progress tracking
- NAIC integration for industry classification

### 5. Underwriting Agent (`agents/underwriting_agent.py`)

**Purpose**: Performs automated underwriting analysis and decisions.

**Key Functions**:
- `analyze_underwriting_eligibility()`: Main underwriting decision function
- Risk factor assessment
- Eligibility determination
- Premium estimation guidance

**Decision Types**:
- **Accept**: Meets all criteria, standard terms
- **Review**: Requires human underwriter evaluation
- **Decline**: Does not meet minimum requirements

**Analysis Factors**:
- Industry risk level
- Company size and revenue
- Technology practices
- Claims history
- Compliance status

### 6. Parallel Monitoring Agent (PMA) (`agents/parallel_monitoring_agent.py`)

**Purpose**: Asynchronously monitors all conversations for escalation triggers.

**Key Functions**:
- `add_conversation_event()`: Non-blocking event addition
- `_monitoring_loop()`: Continuous background monitoring
- `_analyze_conversation_event()`: AI-powered conversation analysis
- `_evaluate_escalation_criteria()`: Determines escalation need
- `_generate_escalation_signal()`: Creates escalation alerts

**Monitoring Criteria**:
- User frustration indicators
- Sentiment degradation
- Complex technical queries
- Repeated questions
- Explicit escalation requests

**Features**:
- Dedicated API key support for independent operation
- Non-blocking architecture (doesn't slow main chat)
- Sentiment tracking over conversation history
- Configurable escalation thresholds

### 7. Conversation Coordinator (`agents/conversation_coordinator.py`)

**Purpose**: Manages conversation sessions and Slack integration.

**Key Functions**:
- `create_session()`: Initializes new conversation sessions
- `escalate_session()`: Links conversations to Slack threads
- `queue_slack_message()`: Handles incoming Slack messages
- `get_session_by_thread()`: Maps Slack threads to conversations
- Session persistence and recovery

**Session Management**:
- Unique conversation IDs
- Bidirectional Slack mapping
- Message history tracking
- Status management (active, escalated, resolved)
- Persistent storage for recovery

### 8. Escalation Agent (`agents/escalation_agent.py`)

**Purpose**: Handles the escalation process to human specialists.

**Key Functions**:
- `create_escalation()`: Main escalation orchestration
- `_analyze_escalation_need()`: Determines type and priority
- `_send_slack_notification()`: Notifies appropriate team
- `_generate_customer_response()`: Creates customer-facing messages

**Escalation Types**:
- UNDERWRITING_REVIEW
- COMPLEX_QUOTE
- COMPLIANCE_ISSUE
- CUSTOMER_COMPLAINT
- TECHNICAL_ISSUE
- HIGH_VALUE_ACCOUNT

**Routing Rules**:
- Each type routes to specific teams
- Priority-based response times
- Formatted Slack notifications with context
- Customer communication templates

### 9. Risk Formatter Agent (`agents/risk_formatter_agent.py`)

**Purpose**: Transforms raw risk assessment text into polished HTML reports.

**Key Functions**:
- `format_risk_report()`: Converts text to structured HTML
- AI-powered formatting for consistency
- Professional styling application

**Output Features**:
- Clean, professional HTML layout
- Consistent formatting across reports
- Responsive design
- Print-friendly styling

## Agent Interaction Flow

### Standard Conversation Flow:
1. User sends message → Main Insurance Agent
2. Main Agent retrieves knowledge → Vector stores/Knowledge base
3. Main Agent may invoke specialized agents:
   - Background Agent for company data
   - Risk Assessment for reports
   - Application Agent for forms
   - Underwriting for decisions
4. Response generated → User

### Parallel Monitoring Flow:
1. All conversations → PMA (asynchronous)
2. PMA analyzes sentiment and complexity
3. If escalation needed → Escalation Signal
4. Conversation Coordinator receives signal
5. Escalation Agent creates Slack thread
6. Human specialist joins conversation

### Escalation Flow:
1. Trigger detected (by PMA or user request)
2. Escalation Agent analyzes need
3. Slack notification sent to appropriate team
4. Conversation Coordinator links chat to Slack
5. Bidirectional messaging enabled
6. Specialist responses routed back to user

## Key Technologies

- **AI Models**: GPT-4, GPT-4o-mini
- **Vector Databases**: Pinecone, OpenAI Vector Store
- **Knowledge Base**: Embroker-specific insurance knowledge
- **External APIs**: NAIC Classification API
- **Communication**: Slack (Socket Mode & Webhooks)
- **Framework**: Asynchronous Python with threading

## Configuration Requirements

### Environment Variables:
- `POC_OPENAI_API`: Main OpenAI API key
- `OPENAI_MONITORING_KEY`: Dedicated key for PMA (optional)
- `PINECONE_API_KEY`: For vector search
- `SLACK_BOT_TOKEN`: Slack bot authentication
- `SLACK_ESCALATION_CHANNEL`: Target channel for escalations

### Performance Considerations:
- PMA runs on separate thread for non-blocking operation
- Conversation Coordinator uses efficient session mapping
- Background Agent implements caching
- Vector search uses fast model for query optimization

## Agent Benefits

1. **Specialization**: Each agent focuses on specific expertise
2. **Scalability**: Agents can be scaled independently
3. **Reliability**: Failure isolation between agents
4. **Flexibility**: Easy to add new agents or modify existing ones
5. **Performance**: Parallel processing and async operations
6. **Human-in-the-loop**: Seamless escalation when needed

This multi-agent architecture ensures comprehensive, intelligent, and efficient insurance interactions while maintaining the flexibility to handle complex scenarios and escalate to human experts when necessary.