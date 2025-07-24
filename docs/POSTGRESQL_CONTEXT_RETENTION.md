# PostgreSQL Context Retention System

## Overview

This AI Insurance Chatbot implements a sophisticated context retention system using PostgreSQL, providing ChatGPT/Claude-like conversation memory that persists across sessions. The system maintains complete conversation history for each user, enabling natural, context-aware interactions.

## Database Architecture

### Core Tables

#### 1. Users Table
```sql
users
├── id (INTEGER, PRIMARY KEY)
├── name (VARCHAR(100))
├── company_name (VARCHAR(200))
├── company_email (VARCHAR(200))
└── created_at (TIMESTAMP)
```
- Stores registered user information
- Each user has isolated conversation contexts
- Links to conversations via foreign key relationships

#### 2. Conversations Table
```sql
conversations
├── id (VARCHAR(50), PRIMARY KEY) - Format: chat_timestamp_id
├── user_id (INTEGER, FOREIGN KEY → users.id)
├── started_at (TIMESTAMP)
├── last_activity (TIMESTAMP)
└── status (VARCHAR(20)) - Values: active, escalated, completed
```
- Tracks individual chat sessions
- Maintains conversation metadata
- Enables chat history sidebar functionality

#### 3. Messages Table
```sql
messages
├── id (INTEGER, PRIMARY KEY)
├── conversation_id (VARCHAR(50), FOREIGN KEY → conversations.id)
├── role (VARCHAR(20)) - Values: user, assistant, system
├── content (TEXT)
└── timestamp (TIMESTAMP)
```
- Stores every message in the conversation
- Preserves complete context for AI processing
- Enables conversation replay and history viewing

## Context Retention Features

### 1. Full Conversation Memory
- **Complete History**: Every message is stored and retrieved
- **No Artificial Limits**: System maintains entire conversation history (only applies limits at 100+ messages)
- **Context Processing**: AI processes ALL conversation history for perfect understanding

### 2. User Isolation
- **Separate Contexts**: Each user has completely isolated conversations
- **Privacy**: No cross-contamination between user sessions
- **Multi-tenant Ready**: Supports multiple concurrent users

### 3. Session Persistence
- **Browser Resilience**: Conversations survive page refreshes
- **System Resilience**: Data persists through server restarts
- **Long-term Storage**: Conversations available indefinitely

### 4. Intelligent Context Handling
- **Business Context**: Remembers company type, industry, preferences
- **Topic Continuity**: Maintains context even during topic switches
- **Smart Pivoting**: Connects off-topic discussions back to business context

## Implementation Details

### Connection Configuration
```python
# Environment variable
DATABASE_URL = "postgresql://user:password@host:port/database"

# SQLAlchemy configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
```

### Message Storage Flow
1. User sends message → Stored in messages table
2. AI processes full conversation history from database
3. AI response → Stored in messages table
4. Conversation metadata updated (last_activity)

### Context Retrieval
```python
# Load conversation history
messages = Message.query.filter_by(
    conversation_id=conversation_id
).order_by(Message.timestamp).all()

# Convert to format for AI processing
conversation_history = [
    {"role": msg.role, "content": msg.content}
    for msg in messages
]
```

## Enhanced Context Features

### Recent Enhancements (July 24, 2025)
- **Context Retention Across Topic Switches**: AI maintains specific business details even during off-topic discussions
- **Smart Context Connection**: When returning to business topics, AI connects context intelligently
- **Example**: "Is your AI company working in entertainment?" vs generic "Are you in entertainment?"

### Chat History Sidebar
- **Visual History**: Users see previous conversations in sidebar
- **Quick Access**: Click to load any previous conversation
- **Preview Text**: Shows conversation snippets for easy identification
- **Date Formatting**: "Today", "Yesterday", or relative dates

## Performance Considerations

### Optimizations
- **Connection Pooling**: Prevents connection exhaustion
- **Pool Recycling**: Handles stale connections (300 seconds)
- **Pre-ping**: Verifies connections before use
- **Indexed Queries**: Fast retrieval by conversation_id

### Scalability
- **Efficient Storage**: Text compression for message content
- **Cascade Deletes**: Automatic cleanup of related records
- **Lazy Loading**: Relationships loaded only when needed

## Security Features

### Data Protection
- **User Isolation**: Strict foreign key constraints
- **SQL Injection Prevention**: SQLAlchemy ORM protection
- **Session Management**: Secure conversation ID generation

### Privacy
- **No Cross-User Access**: Database constraints prevent data leakage
- **Audit Trail**: Timestamps on all records
- **Status Tracking**: Monitor conversation states

## Integration with AI Agent

### Agent Instructions Enhancement
```python
CRITICAL - Context retention across topic switches:
- Always remember and maintain context about the user's company
- If they told me they're an AI company, remember that
- When they switch topics, connect it back to their business context
- Never forget key information during topic changes
```

### Process Flow
1. **Registration**: User data → PostgreSQL users table
2. **Conversation Start**: New conversation record created
3. **Message Processing**: 
   - Retrieve full history from PostgreSQL
   - Process with context awareness
   - Store response in database
4. **Context Maintenance**: AI maintains business context throughout

## Benefits

### User Experience
- **Natural Conversations**: No need to repeat information
- **Seamless Continuity**: Pick up where you left off
- **Professional Context**: Business details always remembered

### Technical Advantages
- **True Persistence**: Not dependent on browser storage
- **Scalable Architecture**: PostgreSQL handles large datasets
- **Reliable Storage**: ACID compliance ensures data integrity

## Comparison to Other Systems

### Like ChatGPT/Claude
- ✅ Full conversation history
- ✅ Context awareness across sessions
- ✅ User-specific memory
- ✅ Topic continuity

### Enhanced Features
- ✅ Business context retention
- ✅ Multi-user isolation
- ✅ Conversation search/history
- ✅ Status tracking (active/escalated)

## Conclusion

This PostgreSQL-based context retention system provides enterprise-grade conversation persistence, enabling the AI Insurance Chatbot to deliver personalized, context-aware interactions that rival leading AI platforms while maintaining complete data isolation and security for each user.