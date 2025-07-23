# Abuse Prevention Integration Guide

## Overview
The new abuse prevention system is designed to maintain a positive user experience while preventing off-topic usage. It uses progressive warnings and gentle redirects rather than harsh blocking.

## Key Features

### 1. **Progressive Warning System**
- **First Warning**: Friendly redirect with helpful suggestions
- **Second Warning**: More direct but still polite
- **Final Warning**: Clear notice before any limits
- **Rate Limit**: Only after multiple warnings AND low topic relevance

### 2. **Smart Topic Detection**
- Quick keyword matching for obvious insurance topics
- AI-powered analysis for ambiguous messages
- Tracks conversation topic ratios
- Allows some off-topic if overall conversation is insurance-focused

### 3. **Generous Limits**
- 50 messages/hour (very generous)
- 200 messages/day (plenty for legitimate use)
- 3 warnings before considering limits
- 24-hour warning reset period

## Integration Steps

### 1. Update app.py

Add the import at the top:
```python
from src.abuse_prevention import check_message_allowed, get_user_status
```

### 2. Modify the /chat endpoint

In `src/app.py`, update the chat endpoint (around line 457):

```python
@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data.get('message', '').strip()
        conversation_id = data.get('conversation_id')
        
        # Get user ID (from session or generate)
        user_id = session.get('user_id', f'anon_{session.get("session_id", "unknown")}')
        
        # Check abuse prevention
        allowed, warning = check_message_allowed(user_id, message, conversation_id)
        
        if not allowed:
            return jsonify({
                'response': warning,
                'conversation_id': conversation_id,
                'rate_limited': True
            }), 429
        
        # Continue with normal processing
        # ... existing code ...
        
        # If there's a warning, prepend it to the response
        if warning:
            agent_response = f"{warning}\n\n---\n\n{agent_response}"
```

### 3. Add Status Endpoint

Add a new endpoint for users to check their status:

```python
@app.route('/api/usage-status', methods=['GET'])
def usage_status():
    user_id = session.get('user_id', f'anon_{session.get("session_id", "unknown")}')
    status = get_user_status(user_id)
    return jsonify(status)
```

### 4. Update Frontend (Optional)

In `templates/chat.html`, add visual indicators:

```javascript
// After receiving response
if (data.rate_limited) {
    // Show rate limit message prominently
    addMessage(data.response, 'assistant warning');
} else if (data.response.includes('⚠️')) {
    // Highlight warnings
    addMessage(data.response, 'assistant warning');
} else {
    addMessage(data.response, 'assistant');
}
```

Add CSS for warnings:
```css
.message.warning {
    background-color: #fff3cd;
    border-left: 4px solid #ffc107;
}
```

## How It Works

### Topic Analysis Flow
1. User sends message
2. Quick keyword check for insurance terms
3. If ambiguous, AI analyzes topic relevance
4. Track topic in conversation history
5. Allow with warning if off-topic (up to 3 times)
6. Calculate overall conversation relevance
7. Only limit if persistent off-topic behavior

### Example Interactions

**Good Experience (Insurance-related):**
```
User: "What cyber coverage do I need for my SaaS startup?"
Bot: [Normal response - no warnings]
```

**First Off-Topic:**
```
User: "Can you help me write Python code?"
Bot: "I notice you're asking about Python code. I'm specifically designed to help with insurance and risk management questions for businesses. 

How can I help you with:
• Business insurance coverage recommendations
• Risk assessment for your company
• Understanding different policy types
• Embroker products and services

What insurance or risk management topic can I assist you with today?

[Continues to answer if user insists, but counts as warning]"
```

**Mixed Conversation (Allowed):**
```
User: "What's D&O insurance?"
Bot: [Explains D&O]
User: "Thanks. BTW, what's 2+2?"
Bot: [Might give gentle redirect but allows it since conversation is mostly on-topic]
```

## Configuration

Adjust limits in `abuse_prevention.py`:

```python
self.config = {
    'off_topic_warnings_before_limit': 3,      # Increase for more leniency
    'warning_reset_hours': 24,                 # How long before warnings reset
    'max_messages_per_hour': 50,               # Very generous
    'max_messages_per_day': 200,               # Plenty for legitimate use
    'topic_relevance_threshold': 0.3,          # 30% must be insurance-related
}
```

## Benefits

1. **User-Friendly**: Guides users rather than blocking
2. **Context-Aware**: Considers overall conversation, not just individual messages
3. **Educational**: Teaches users what the bot is for
4. **Flexible**: Allows some off-topic in otherwise good conversations
5. **Protective**: Prevents coding homework and token-intensive abuse

## Monitoring

The system tracks:
- Warning counts per user
- Topic distribution per conversation
- Daily message counts
- Off-topic patterns

Access stats via:
- `/api/usage-status` - Individual user status
- Future: `/admin/abuse-stats` - Admin dashboard

## Testing

Test the system with:
```python
# In main chatbot
"Help me with my Python homework"  # Should warn
"What insurance do I need?"        # Should allow
"Write a 1000-word essay"          # Should warn strongly
"Explain D&O coverage"             # Should allow
```

## Notes

- The system is intentionally lenient to maintain good UX
- Warnings are educational, not punitive
- Real rate limits only apply after multiple warnings
- Insurance professionals asking tangential questions won't be blocked
- The AI model for topic detection is fast and cost-effective (gpt-4o-mini)