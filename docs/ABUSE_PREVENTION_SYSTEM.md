# Abuse Prevention System Documentation

## Overview

The Abuse Prevention System is a background monitoring agent that protects the insurance chatbot from automated attacks, spam, and abuse while maintaining natural conversation flow. It operates silently without interrupting legitimate users.

## Architecture

### Components

1. **AbusePreventionAgent** (`agents/monitoring/abuse_prevention_agent.py`)
   - Core monitoring agent running in a separate thread
   - Processes events asynchronously using a queue system
   - Maintains state for rate limiting and pattern detection

2. **Flask Integration** (`src/app.py`)
   - Intercepts all chat requests at the `/api/chat` endpoint
   - Extracts IP addresses, user agents, and message content
   - Submits events to the monitoring queue

3. **Admin Endpoints**
   - `/api/abuse-prevention-stats` - View real-time statistics
   - `/api/clear-blocked-ips` - Manage blocked IPs

## How It Works

### 1. Request Monitoring Flow

```
User Request → Flask Endpoint → Extract Metadata → Queue Event → Continue Chat
                                                         ↓
                                              Background Processing
                                                         ↓
                                              Abuse Detection → Action
```

### 2. Detection Methods

#### Rate Limiting
- **Per Minute**: 10 messages max
- **Per Hour**: 100 messages max
- **Per Day**: 500 messages max
- **IP-Based**: 150 messages/hour per IP
- **Rapid Fire**: Minimum 1 second between messages

#### Pattern Detection
- **Bot Patterns**: Detects common bot user agents and behaviors
  - `curl`, `wget`, `python`, `axios`, `fetch`
  - Test users like `test123`, `user456`, `bot789`
  - SQL injection attempts
  - Script injections
  - JSON-like message patterns

- **Spam Patterns**: Identifies commercial spam
  - Discount offers with percentages
  - "Click here" with URLs
  - Lottery/prize notifications
  - Known spam keywords

#### AI-Powered Analysis
- Every 5th message gets deep content analysis
- Uses OpenAI to detect:
  - Sophisticated spam attempts
  - Context-inappropriate messages
  - Automated testing patterns
  - Coordinated attack behavior

### 3. Action Levels

1. **Monitor** (Low Severity)
   - Track suspicious behavior
   - Log for analysis
   - No user impact

2. **Warn** (Medium Severity)
   - Flag conversation for review
   - Increase monitoring frequency
   - Still allows messages

3. **Throttle** (High Severity)
   - Slow down response processing
   - Add artificial delays
   - Discourage rapid requests

4. **Block** (Critical Severity)
   - Ban IP address completely
   - Reject all requests from IP
   - Log for security review

### 4. State Management

The system maintains several state stores:

```python
# Rate limiting state
ip_requests = {
    "192.168.1.1": [timestamp1, timestamp2, ...],
    "10.0.0.1": [timestamp3, timestamp4, ...]
}

# Abuse tracking
blocked_ips = {"192.168.1.100", "10.0.0.50"}
warned_conversations = {"conv-123", "conv-456"}
conversation_abuse_scores = {
    "conv-123": 0.85,  # High risk
    "conv-456": 0.25   # Low risk
}
```

## Implementation Details

### Request Event Structure
```python
@dataclass
class RequestEvent:
    conversation_id: str
    user_id: Optional[str]
    ip_address: str
    user_agent: str
    message: str
    timestamp: datetime
    request_metadata: Dict[str, Any]
```

### Abuse Signal Structure
```python
@dataclass
class AbuseSignal:
    conversation_id: str
    abuse_type: str  # bot, script, spam, ddos, off_topic
    severity: str  # low, medium, high, critical
    confidence: float  # 0.0 to 1.0
    indicators: List[str]
    action: str  # monitor, warn, throttle, block
    timestamp: datetime
    ip_address: str
```

## API Usage

### Check Statistics
```bash
GET /api/abuse-prevention-stats

Response:
{
    "success": true,
    "statistics": {
        "blocked_ips": 2,
        "monitored_conversations": 15,
        "high_risk_conversations": 3,
        "requests_last_hour": 127,
        "active": true
    },
    "recent_signals": [
        {
            "conversation_id": "conv-123",
            "abuse_type": "bot",
            "severity": "high",
            "confidence": 0.92,
            "action": "block",
            "ip_address": "192.168.1.100",
            "timestamp": "2025-07-24T13:45:00Z",
            "indicators": ["curl user agent", "rapid requests", "test pattern"]
        }
    ]
}
```

### Clear Blocked IPs
```bash
# Clear specific IP
POST /api/clear-blocked-ips
{
    "ip_address": "192.168.1.100"
}

# Clear all blocked IPs
POST /api/clear-blocked-ips
{}
```

## Configuration

Default configuration in the agent:

```python
config = {
    'rate_limits': {
        'messages_per_minute': 10,
        'messages_per_hour': 100,
        'messages_per_day': 500,
        'ip_messages_per_hour': 150,
        'min_interval_seconds': 1
    },
    'thresholds': {
        'bot_score_threshold': 0.8,
        'spam_score_threshold': 0.7,
        'off_topic_threshold': 0.85,
        'pattern_match_threshold': 3
    }
}
```

## Performance Impact

- **Zero Chat Latency**: Background processing doesn't block chat responses
- **Async Queue System**: Events processed independently
- **Resource Efficient**: Single monitoring thread handles all conversations
- **Graceful Degradation**: If monitoring fails, chat continues normally

## Security Benefits

1. **Bot Protection**: Blocks automated scripts and crawlers
2. **Spam Prevention**: Filters commercial spam and phishing
3. **DDoS Mitigation**: Rate limiting prevents resource exhaustion
4. **Attack Detection**: Identifies SQL injection and XSS attempts
5. **Pattern Recognition**: Learns from attack patterns over time

## Monitoring and Maintenance

### Health Checks
- Monitor the `/api/abuse-prevention-stats` endpoint
- Check `requests_last_hour` for traffic patterns
- Review `blocked_ips` count for effectiveness
- Analyze `recent_signals` for false positives

### Tuning Parameters
- Adjust rate limits based on legitimate usage patterns
- Fine-tune pattern matching for your use case
- Modify AI analysis frequency for cost/accuracy balance
- Update threshold scores based on observed behavior

## Integration Example

The system automatically integrates when the Flask app starts:

```python
# In app.py - automatic initialization
from agents.monitoring.abuse_prevention_agent import get_abuse_prevention_agent

# During request handling
abuse_prevention = get_abuse_prevention_agent()
event = RequestEvent(
    conversation_id=conversation_id,
    user_id=user_id,
    ip_address=request.remote_addr,
    user_agent=request.headers.get('User-Agent', ''),
    message=message,
    timestamp=datetime.now(),
    request_metadata={'endpoint': '/api/chat'}
)
abuse_prevention.submit_event(event)
```

## Best Practices

1. **Regular Monitoring**: Check statistics daily for anomalies
2. **IP Whitelist**: Consider maintaining trusted IP list for partners
3. **Log Analysis**: Review abuse signals for pattern improvements
4. **Threshold Tuning**: Adjust based on false positive rate
5. **Documentation**: Keep track of blocked IPs and reasons

## Troubleshooting

### High False Positive Rate
- Lower threshold scores
- Review pattern matches
- Exclude legitimate bot user agents

### Legitimate Users Blocked
- Check rate limits against usage patterns
- Review blocked IP list
- Implement IP whitelist for known users

### Performance Issues
- Monitor queue size
- Check thread health
- Review AI analysis frequency

## Future Enhancements

1. **Machine Learning**: Train custom models on historical abuse data
2. **Geographic Filtering**: Block or monitor by country/region
3. **Behavioral Analysis**: Track conversation patterns over time
4. **Integration APIs**: Connect with external threat intelligence
5. **Dashboard UI**: Visual monitoring interface