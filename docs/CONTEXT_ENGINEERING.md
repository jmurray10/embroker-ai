# Context Engineering for AI Insurance Chatbot

## Overview

Context engineering is the practice of designing, implementing, and optimizing how an AI system accesses, processes, and utilizes contextual information to provide accurate, relevant, and personalized responses. This document outlines the comprehensive context engineering architecture implemented in the Embroker AI Insurance Chatbot.

## Core Context Sources

### 1. PostgreSQL - Conversation Memory
**Purpose**: Persistent conversation history and user context retention

**Implementation**:
- Full conversation history storage (like ChatGPT/Claude)
- User profile and company information persistence
- Session management across multiple interactions
- Complete message history with role tracking

**Key Features**:
```sql
conversations
├── id (conversation identifier)
├── user_id (links to user profile)
├── started_at (timestamp)
├── last_activity (timestamp)
└── status (active, escalated, completed)

messages
├── id (message identifier)
├── conversation_id (links to conversation)
├── role (user, assistant, system)
├── content (full message text)
└── timestamp (when sent)
```

**Context Benefits**:
- Users never need to repeat information
- Business context maintained across topic switches
- Personalized responses based on history
- Seamless conversation continuity

### 2. Pinecone Vector Database - Knowledge Base
**Purpose**: Semantic search for insurance documentation and policies

**Implementation**:
- Primary index: `embroker-insurance-chatbot`
- Embedding model: `text-embedding-ada-002`
- Semantic similarity search with score thresholds
- Forced inclusion of Tech E&O vectors for complete coverage

**Key Features**:
- Real-time semantic search across insurance documents
- Coverage details, limits, and sublimits retrieval
- Policy-specific information access
- Industry classification and appetite guides

**Context Enhancement**:
```python
# Force vector consultation for all queries
if query relates to insurance:
    vector_results = pinecone.search(query, top_k=5)
    context = extract_relevant_content(vector_results)
    response = generate_with_context(context)
```

### 3. OpenAI Web Search - Real-time Information
**Purpose**: Current events, market trends, and time-sensitive data

**Implementation**:
- OpenAI Responses API with `web_search_preview` tool
- Automatic triggering for time-sensitive queries
- Real-time citations from reputable sources
- Cost: $30 per 1,000 queries

**Trigger Patterns**:
- Dates: "2024", "2025", "today", "this week"
- Keywords: "latest", "recent", "current", "now"
- Topics: "news", "trends", "updates", "regulations"
- Companies: Specific company mentions

**Integration**:
```python
tools = [{"type": "web_search_preview"}]
response = client.responses.create(
    model="gpt-4.1",
    tools=tools,
    input=query
)
```

### 4. External Classification API
**Purpose**: Company risk classification and industry analysis

**Endpoint**: `https://emb-classification.onrender.com/classify`

**Data Flow**:
1. Extract domain from user email (jeff@company.com → company.com)
2. Send company name and website to classification API
3. Receive NAICS codes, industry classification, confidence scores
4. Store in background agent cache for risk assessment

**Response Structure**:
```json
{
  "naicsCode": "541511",
  "industry": "Technology",
  "embrokerClass": "Technology",
  "confidence": 0.838,
  "companySummary": "AI-powered platform...",
  "operationsSummary": "Develops and operates..."
}
```

## Context Processing Pipeline

### 1. Query Analysis
```
User Message → Intent Detection → Context Requirements
                     ↓
              Determine which context sources needed:
              - Historical (PostgreSQL)
              - Knowledge (Pinecone)
              - Current (Web Search)
              - Company (Classification API)
```

### 2. Context Aggregation
```
Parallel Context Retrieval:
├── PostgreSQL: Get conversation history
├── Pinecone: Search relevant documents
├── Web Search: Get current information
└── Background Agent: Retrieve company data
         ↓
    Merge all contexts with priority weighting
```

### 3. Context-Aware Response Generation
```python
context = {
    "conversation_history": postgres_messages[-20:],  # Last 20 messages
    "user_profile": user_data,
    "company_context": classification_data,
    "relevant_knowledge": pinecone_results,
    "current_events": web_search_results
}

response = generate_response_with_context(
    query=user_message,
    context=context,
    instructions=agent_instructions
)
```

## Advanced Context Strategies

### 1. Mandatory Vector Consultation
- **Strategy**: Force vector search for ALL insurance queries
- **Implementation**: `_mandatory_vector_search_wrapper()`
- **Benefit**: Ensures accurate, specific information delivery

### 2. Context Retention Instructions
```python
CRITICAL - Context retention across topic switches:
- Always remember user's company throughout conversation
- Connect off-topic discussions back to business context
- Never forget key information during topic changes
```

### 3. Intelligent Fallbacks
- Primary: Pinecone vector search
- Secondary: Comprehensive search across indexes
- Tertiary: Web search for current information
- Final: Graceful degradation with helpful message

### 4. Context Caching
- Background agent maintains company analysis cache
- Risk assessments stored for quick retrieval
- Session data persists across worker processes

## Context Quality Assurance

### 1. Relevance Scoring
- Pinecone: Minimum score threshold (0.01)
- Negative scores included for comprehensive coverage
- Force inclusion of specific vector categories

### 2. Context Freshness
- Web search for any time-sensitive queries
- Background refresh of company data
- Timestamp tracking on all context sources

### 3. Context Isolation
- User-specific conversation contexts
- No cross-contamination between users
- Strict foreign key constraints in PostgreSQL

## Performance Optimizations

### 1. Parallel Processing
- Simultaneous retrieval from all context sources
- Non-blocking background analysis
- Asynchronous web search operations

### 2. Smart Caching
- Company classification results cached
- Risk assessments stored in agent memory
- Conversation history efficiently indexed

### 3. Context Prioritization
- Recent messages weighted higher
- Exact matches prioritized in vector search
- Current information overrides outdated data

## Future Context Enhancements

### 1. Semantic Response Caching
- Cache similar question patterns
- Reuse successful response structures
- Reduce API calls for common queries

### 2. Graph-Based Relationships
- Coverage dependency graphs
- Industry risk networks
- Regulatory requirement trees

### 3. Event-Driven Context
- Real-time news monitoring
- Legislative change tracking
- Industry alert integration

### 4. Geospatial Context
- Location-based risk assessment
- State regulatory mapping
- Competitive landscape analysis

## Monitoring and Metrics

### 1. Context Usage Tracking
```python
context_metrics = {
    "postgres_queries": count,
    "pinecone_searches": count,
    "web_searches": count,
    "api_calls": count,
    "cache_hits": percentage
}
```

### 2. Response Quality Metrics
- Context relevance scores
- User satisfaction indicators
- Escalation patterns analysis

### 3. Performance Monitoring
- Context retrieval latency
- End-to-end response time
- Resource utilization

## Best Practices

### 1. Context Hygiene
- Regular cleanup of stale conversations
- Vector index optimization
- Cache invalidation strategies

### 2. Privacy and Security
- User context isolation
- Secure API communication
- Audit trail maintenance

### 3. Continuous Improvement
- Regular context source evaluation
- A/B testing context strategies
- User feedback integration

## Conclusion

The multi-layered context engineering approach enables the Embroker AI Insurance Chatbot to deliver highly personalized, accurate, and timely responses. By combining persistent memory (PostgreSQL), semantic knowledge (Pinecone), real-time information (Web Search), and company intelligence (Classification API), the system provides a comprehensive context-aware experience that rivals human insurance advisors while maintaining the efficiency and scalability of AI automation.