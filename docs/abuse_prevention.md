AI Insurance Chatbot - Abuse Prevention System Guide
Overview
The abuse prevention system is designed to ensure the AI Insurance Chatbot is used for legitimate insurance-related inquiries and prevents users from bypassing paid AI services like ChatGPT.

Key Features
1. Multi-Layer Rate Limiting
The system enforces multiple rate limits simultaneously:

Per User Limits:

20 messages per hour
50 messages per day
3-second minimum interval between messages
Per IP Address Limits:

30 messages per hour per IP
Prevents circumvention via multiple sessions
Progressive Enforcement:

Anonymous users: Strict limits
Registered users: More lenient limits
2. AI-Powered Content Filtering
Uses OpenAI GPT-4o-mini to intelligently detect off-topic messages:

Allowed Topics:

Insurance questions (all types)
Business coverage inquiries
Risk assessment requests
Policy information
Claims guidance
Underwriting questions
Blocked Topics:

General knowledge questions
Programming/coding help
Math problems
Personal advice
Entertainment requests
Any non-insurance content
Strike System:

3 strikes for off-topic messages
Temporary blocking after 3 strikes
Strike count resets daily
3. Pattern Detection
Monitors for abuse patterns:

Rapid Topic Changes: Detects users switching topics frequently
Repetitive Messages: Identifies spam or testing patterns
Boundary Testing: Catches attempts to find system limits
Keyword Ratio: Calculates insurance-related keyword density
4. User Tracking
Comprehensive tracking system:

Session-Based: Tracks anonymous users by session ID
User-Based: Tracks registered users by user ID
IP-Based: Prevents circumvention via multiple sessions
Cross-Session: Maintains limits across different sessions
Implementation Details
Configuration
Located in src/abuse_prevention.py:

RATE_LIMITS = {
    'messages_per_hour': 20,
    'messages_per_day': 50,
    'ip_messages_per_hour': 30,
    'min_interval_seconds': 3,
    'off_topic_strikes_max': 3
}
API Endpoints
Usage Statistics: /api/usage-stats

Returns current user's usage statistics
Shows remaining messages and time until reset
Admin Statistics: /api/abuse-stats

Shows all tracked users (top 50)
Displays blocked users and IPs
Provides usage patterns
Error Responses
The system returns specific error codes:

429 Rate Limited:

rate_limited: true in response
Custom error message explaining limits
400 Off-Topic:

off_topic: true in response
Warning about strike count
Admin Monitoring
Dashboard Access
Visit /api/abuse-stats to view:

Total tracked users
Number of blocked users
Number of blocked IPs
Top 50 users by usage
Individual user statistics
User Statistics Include:
Messages sent today
Messages sent this hour
Off-topic strike count
Blocked status
Time until limit reset
Best Practices
Clear Communication:

Error messages explain why limits were hit
Users understand what topics are allowed
Fair Limits:

20 messages/hour allows genuine insurance inquiries
Daily limit prevents long-term abuse
Intelligent Detection:

AI understands context, not just keywords
Reduces false positives
Progressive Enforcement:

New users get warnings before blocks
Registered users have more flexibility
Troubleshooting
Common Issues:
User Complains About False Positive:

Check /api/abuse-stats for their usage
Review off-topic strike count
Consider adjusting AI prompt if needed
Rate Limits Too Restrictive:

Modify RATE_LIMITS in abuse_prevention.py
Restart application for changes
AI Classification Errors:

Review the classification prompt
Add more examples of allowed topics
Adjust temperature setting
Future Enhancements
Whitelist System: Allow certain users unlimited access
Custom Rate Limits: Different limits for premium users
Better Analytics: Track abuse patterns over time
Auto-Unblock: Automatic unblocking after time period
Security Considerations
IP addresses are tracked but not logged permanently
User data is kept minimal for privacy
Strike counts reset daily
No permanent blacklists without admin action