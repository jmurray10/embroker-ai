# AI Insurance Chatbot - Agent Architecture & Flow

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Agent Interaction Flow](#agent-interaction-flow)
3. [Detailed Agent Descriptions](#detailed-agent-descriptions)
4. [Communication Patterns](#communication-patterns)
5. [Data Flow Diagrams](#data-flow-diagrams)
6. [Integration Points](#integration-points)
7. [Scalability & Performance](#scalability--performance)

## Architecture Overview

The AI Insurance Chatbot employs a sophisticated multi-agent architecture designed for modularity, scalability, and intelligent task distribution. Each agent specializes in specific insurance operations while maintaining seamless communication with other components.

### Core Design Principles
- **Separation of Concerns**: Each agent handles a specific domain
- **Asynchronous Operations**: Non-blocking design for optimal performance
- **Fail-Safe Escalation**: Automatic human handoff when needed
- **Knowledge-Driven**: Vector database integration for accurate responses
- **Real-Time Monitoring**: Parallel analysis without performance impact

## Agent Interaction Flow

### 1. Standard Conversation Flow

```
User Message
    ↓
[Main Insurance Agent]
    ├─→ Vector Store Search (Knowledge Retrieval)
    ├─→ Context Enhancement
    └─→ Response Generation
         ↓
    [Parallel Monitoring Agent] (Async)
         ├─→ Sentiment Analysis
         ├─→ Complexity Assessment
         └─→ Escalation Detection
              ↓
         [Response to User]
```

### 2. Specialized Task Flow

```
User Request (e.g., "I need a quote")
    ↓
[Main Insurance Agent]
    ├─→ Intent Recognition
    └─→ Route to Specialist
         ├─→ [Background Agent] - Company Analysis
         ├─→ [Risk Assessment Agent] - Risk Report
         ├─→ [Application Agent] - Form Completion
         └─→ [Underwriting Agent] - Decision Making
              ↓
         [Formatted Response]
```

### 3. Escalation Flow

```
[Parallel Monitoring Agent]
    ├─→ Detects Escalation Trigger
    └─→ Sends Signal
         ↓
    [Escalation Agent]
         ├─→ Analyzes Context
         ├─→ Determines Priority
         └─→ Creates Slack Thread
              ↓
         [Conversation Coordinator]
              ├─→ Links Chat to Slack
              ├─→ Manages Bidirectional Messages
              └─→ Tracks Specialist Presence
```

## Detailed Agent Descriptions

### 1. Main Insurance Agent (`agents/core/agents_insurance_chatbot.py`)

**Primary Role**: Central hub for all insurance queries and agent orchestration

**Key Responsibilities**:
- First point of contact for all user messages
- Intent recognition and routing
- Knowledge base integration
- Response synthesis from multiple sources

**Technical Details**:
```python
class InsuranceKnowledgeAgent:
    - Models: gpt-4.1-2025-04-14 (main), gpt-4o-mini (fast ops)
    - Vector Stores: OpenAI & Pinecone (fallback)
    - Tools: search_insurance_knowledge, analyze_underwriting, web_search
```

**Flow Logic**:
1. Receives user message
2. Searches vector databases for relevant knowledge
3. Enhances context with Embroker-specific information
4. Determines if specialized agent needed
5. Generates comprehensive response
6. Sends to Parallel Monitoring Agent

### 2. Parallel Monitoring Agent (PMA) (`agents/monitoring/parallel_monitoring_agent.py`)

**Primary Role**: Asynchronous conversation monitoring for quality and escalation needs

**Key Responsibilities**:
- Real-time sentiment analysis
- Frustration detection
- Complexity assessment
- Escalation triggering
- Zero-latency operation

**Technical Details**:
```python
class ParallelMonitoringAgent:
    - Runs on separate thread
    - Uses dedicated API key (optional)
    - Event-driven architecture
    - Queue-based processing
```

**Monitoring Criteria**:
- Negative sentiment patterns
- Repeated questions (unresolved queries)
- Explicit escalation requests
- Complex technical inquiries
- High-stakes conversations (large policies)

**Flow Logic**:
1. Receives conversation events asynchronously
2. Analyzes without blocking main chat
3. Maintains conversation state
4. Evaluates escalation criteria
5. Generates escalation signals when needed

### 3. Background Agent (`agents/analysis/background_agent.py`)

**Primary Role**: Company information retrieval and analysis

**Key Responsibilities**:
- NAIC classification lookup
- Industry risk profiling
- Company data caching
- Background processing

**Technical Details**:
```python
class CompanyAnalysisAgent:
    - External API: NAIC Classification API
    - Caching: In-memory storage
    - Processing: Background threads
```

**Flow Logic**:
1. Receives company name/website
2. Queries NAIC API for classification
3. Analyzes industry codes
4. Caches results for performance
5. Returns structured data

### 4. Risk Assessment Agent (`agents/analysis/risk_assessment_agent.py`)

**Primary Role**: Generate comprehensive risk assessment reports

**Key Responsibilities**:
- Risk analysis based on industry
- Coverage recommendations
- Claim examples generation
- Professional report formatting

**Technical Details**:
```python
class RiskAssessmentAgent:
    - Model: gpt-4 (reasoning)
    - Knowledge: Embroker product portfolio
    - Output: Structured risk reports
```

**Report Sections**:
1. Executive Summary
2. Risk Manager's Analysis
3. Coverage Recommendations
   - Tech E&O/Cyber
   - EPLI
   - D&O
   - General Liability
4. Industry-Specific Claims Examples

### 5. Application Agent (`agents/customer_service/application_agent.py`)

**Primary Role**: Guide users through insurance application process

**Key Responsibilities**:
- Conversational form completion
- Field validation
- Progress tracking
- Data pre-filling from context

**Technical Details**:
```python
class ApplicationAgent:
    - Model: gpt-4o-mini-2024-07-18
    - Sections: Company Profile, Technology, Coverage, Risk Management
    - Integration: NAIC data auto-fill
```

**Application Flow**:
1. Start application session
2. Pre-fill known data
3. Ask questions conversationally
4. Validate responses
5. Track progress
6. Generate summary

### 6. Underwriting Agent (`agents/analysis/underwriting_agent.py`)

**Primary Role**: Automated underwriting decisions

**Key Responsibilities**:
- Eligibility assessment
- Risk evaluation
- Decision making (Accept/Review/Decline)
- Guideline compliance

**Technical Details**:
```python
class UnderwritingAgent:
    - Knowledge: Embroker underwriting guidelines
    - Decision Types: Accept, Review, Decline
    - Factors: Industry, revenue, employees, risk profile
```

**Decision Flow**:
1. Analyze company information
2. Check against guidelines
3. Evaluate risk factors
4. Make preliminary decision
5. Provide detailed reasoning

### 7. Escalation Agent (`agents/monitoring/escalation_agent.py`)

**Primary Role**: Manage escalations to human specialists

**Key Responsibilities**:
- Escalation analysis
- Priority determination
- Slack notification
- Customer communication

**Technical Details**:
```python
class EscalationAgent:
    - Model: gpt-4.1-2025-04-14
    - Integration: Slack API
    - Routing: Team-based rules
```

**Escalation Types & Routing**:
- UNDERWRITING_REVIEW → underwriting_team
- COMPLEX_QUOTE → senior_underwriter
- COMPLIANCE_ISSUE → compliance_team
- CUSTOMER_COMPLAINT → customer_success
- TECHNICAL_ISSUE → technical_support

### 8. Conversation Coordinator (`agents/core/conversation_coordinator.py`)

**Primary Role**: Session management and Slack integration

**Key Responsibilities**:
- Session lifecycle management
- Slack thread mapping
- Message routing
- State persistence

**Technical Details**:
```python
class ConversationCoordinator:
    - Storage: JSON persistence
    - Mapping: Bidirectional (chat ↔ Slack)
    - State: Active, Escalated, Resolved
```

**Coordination Flow**:
1. Create/manage sessions
2. Handle escalation requests
3. Map conversations to Slack threads
4. Route messages bidirectionally
5. Track specialist presence

### 9. Risk Formatter Agent (`agents/formatting/risk_formatter_agent.py`)

**Primary Role**: Format risk reports into professional HTML

**Key Responsibilities**:
- Text to HTML conversion
- Consistent styling
- Professional formatting
- Print-friendly output

## Communication Patterns

### 1. Synchronous Communication
- User ↔ Main Insurance Agent
- Main Agent → Specialized Agents
- Response synthesis and delivery

### 2. Asynchronous Communication
- All conversations → PMA (non-blocking)
- Background processing for company analysis
- Slack notifications

### 3. Event-Driven Communication
- PMA escalation signals
- Slack Socket Mode events
- Real-time message updates

## Data Flow Diagrams

### Knowledge Retrieval Flow
```
User Query → Main Agent
    ↓
Vector Search
    ├─→ OpenAI Vector Store (Primary)
    └─→ Pinecone (Fallback)
         ↓
    Context Enhancement
         ├─→ Embroker Knowledge Base
         └─→ Web Search (if needed)
              ↓
         Enhanced Response
```

### Escalation Data Flow
```
Conversation Data → PMA
    ↓
Analysis (Sentiment, Complexity)
    ↓
Escalation Signal
    ↓
Escalation Agent
    ├─→ Context Preparation
    ├─→ Slack Notification
    └─→ Customer Response
         ↓
    Conversation Coordinator
         ├─→ Session Update
         └─→ Message Routing
```

## Integration Points

### 1. External APIs
- **NAIC Classification API**: Industry classification
- **OpenAI API**: All AI operations
- **Slack API**: Human escalation
- **Pinecone API**: Vector search

### 2. Internal Integrations
- **Vector Stores**: Knowledge retrieval
- **Database**: Session persistence
- **WebSocket**: Real-time updates
- **Message Queues**: Async processing

## Scalability & Performance

### Performance Optimizations
1. **Parallel Processing**: PMA runs independently
2. **Caching**: Company data cached in memory
3. **Fast Models**: gpt-4o-mini for quick operations
4. **Vector Search**: Optimized embeddings

### Scalability Features
1. **Modular Architecture**: Add agents without disruption
2. **Queue-Based Processing**: Handle high volumes
3. **Stateless Agents**: Horizontal scaling ready
4. **API Rate Limiting**: Built-in protection

### Monitoring & Observability
1. **Logging**: Comprehensive agent logs
2. **Metrics**: Response times, escalation rates
3. **Health Checks**: Agent status monitoring
4. **Error Handling**: Graceful degradation

## Best Practices

### Agent Development
1. Single responsibility principle
2. Async-first design
3. Comprehensive error handling
4. Clear logging standards

### Integration Guidelines
1. Use environment variables
2. Implement retry logic
3. Cache external API calls
4. Document API contracts

### Testing Strategy
1. Unit tests per agent
2. Integration tests for flows
3. Load testing for scalability
4. Monitoring in production

## Future Enhancements

### Planned Improvements
1. **ML-Based Routing**: Smart agent selection
2. **Predictive Escalation**: Proactive handoffs
3. **Multi-Language Support**: Global expansion
4. **Advanced Analytics**: Conversation insights
5. **Voice Integration**: Phone support capability

This architecture ensures the AI Insurance Chatbot delivers intelligent, scalable, and reliable service while maintaining the flexibility to evolve with business needs.