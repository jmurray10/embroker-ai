"""
Abuse Prevention Agent
Monitors conversations and request patterns in the background to detect and prevent abuse
without interrupting natural conversation flow.
"""

import os
import json
import time
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
import threading
from queue import Queue, Empty
from collections import defaultdict
import hashlib
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

@dataclass
class RequestEvent:
    """Represents a request event for abuse monitoring"""
    conversation_id: str
    user_id: Optional[str]
    ip_address: str
    user_agent: str
    message: str
    timestamp: datetime
    request_metadata: Dict[str, Any]

@dataclass
class AbuseSignal:
    """Represents an abuse detection signal"""
    conversation_id: str
    abuse_type: str  # bot, script, spam, ddos, off_topic
    severity: str  # low, medium, high, critical
    confidence: float  # 0.0 to 1.0
    indicators: List[str]
    action: str  # monitor, warn, throttle, block
    timestamp: datetime
    ip_address: str

class AbusePreventionAgent:
    """
    Background abuse prevention that doesn't interrupt conversations
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the abuse prevention agent"""
        self.api_key = api_key or os.getenv("OPENAI_MONITORING_KEY") or os.getenv("POC_OPENAI_API")
        self.client = OpenAI(api_key=self.api_key)
        
        # Configuration
        self.config = {
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
            },
            'patterns': {
                'bot_patterns': [
                    r'curl|wget|python|axios|fetch',
                    r'test\d+|user\d+|bot\d+',
                    r'SELECT.*FROM|DROP TABLE|INSERT INTO',
                    r'<script|javascript:|onerror=',
                    r'{\s*".*"\s*:\s*".*"\s*}'  # JSON-like patterns
                ],
                'spam_patterns': [
                    r'(buy|sell|cheap|discount|offer).*\d+%',
                    r'click here|visit.*http',
                    r'congratulations.*won',
                    r'(viagra|casino|lottery)'
                ]
            }
        }
        
        # State tracking
        self.request_queue = Queue()
        self.abuse_signals = Queue()
        self.monitoring_active = True
        
        # Rate limiting state
        self.ip_requests = defaultdict(list)  # IP -> [timestamps]
        self.user_requests = defaultdict(list)  # user_id -> [timestamps]
        self.conversation_messages = defaultdict(list)  # conversation_id -> [messages]
        
        # Abuse detection state
        self.blocked_ips = set()
        self.warned_conversations = set()
        self.conversation_abuse_scores = defaultdict(float)
        
        # Start monitoring thread
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        print("Abuse Prevention Agent initialized and monitoring")

    def add_request(self, conversation_id: str, user_id: Optional[str], ip_address: str, 
                   user_agent: str, message: str, metadata: Optional[Dict] = None):
        """Add a request event to monitoring queue (non-blocking)"""
        try:
            event = RequestEvent(
                conversation_id=conversation_id,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                message=message,
                timestamp=datetime.now(),
                request_metadata=metadata or {}
            )
            self.request_queue.put(event, block=False)
        except Exception as e:
            print(f"Abuse Prevention: Error adding event: {e}")

    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Process events
                try:
                    event = self.request_queue.get(timeout=1.0)
                    self._analyze_request(event)
                    self.request_queue.task_done()
                except Empty:
                    # Periodic cleanup of old data
                    self._cleanup_old_data()
                    continue
                    
            except Exception as e:
                print(f"Abuse Prevention: Error in monitoring loop: {e}")
                time.sleep(1)

    def _analyze_request(self, event: RequestEvent):
        """Analyze a request for abuse patterns"""
        try:
            # Skip if IP is already blocked
            if event.ip_address in self.blocked_ips:
                self._create_abuse_signal(event, "blocked_ip", "critical", 1.0, 
                                        ["IP already blocked"], "block")
                return
            
            # Rate limiting check
            rate_limit_result = self._check_rate_limits(event)
            if rate_limit_result:
                return
            
            # Pattern-based detection
            bot_score = self._calculate_bot_score(event)
            spam_score = self._calculate_spam_score(event)
            
            # Content analysis (using AI)
            content_analysis = self._analyze_content(event)
            
            # Aggregate scoring
            abuse_indicators = []
            severity = "low"
            action = "monitor"
            
            if bot_score > self.config['thresholds']['bot_score_threshold']:
                abuse_indicators.append(f"Bot-like behavior detected (score: {bot_score:.2f})")
                severity = "high"
                action = "block"
                
            if spam_score > self.config['thresholds']['spam_score_threshold']:
                abuse_indicators.append(f"Spam patterns detected (score: {spam_score:.2f})")
                severity = "medium" if severity == "low" else severity
                action = "warn" if action == "monitor" else action
                
            if content_analysis.get('off_topic_confidence', 0) > self.config['thresholds']['off_topic_threshold']:
                abuse_indicators.append("Persistent off-topic content")
                # Don't block for off-topic, just monitor
                
            # Create signal if abuse detected
            if abuse_indicators:
                self._create_abuse_signal(event, "mixed", severity, 
                                        max(bot_score, spam_score), 
                                        abuse_indicators, action)
                
                # Update conversation score
                self.conversation_abuse_scores[event.conversation_id] += 0.1
                
        except Exception as e:
            print(f"Abuse Prevention: Error analyzing request: {e}")

    def _check_rate_limits(self, event: RequestEvent) -> Optional[AbuseSignal]:
        """Check rate limiting rules"""
        now = event.timestamp
        limits = self.config['rate_limits']
        
        # Clean old timestamps
        cutoff_hour = now - timedelta(hours=1)
        cutoff_day = now - timedelta(days=1)
        
        # IP rate limiting
        ip_times = self.ip_requests[event.ip_address]
        ip_times = [t for t in ip_times if t > cutoff_hour]
        
        if len(ip_times) >= limits['ip_messages_per_hour']:
            self._create_abuse_signal(event, "rate_limit", "high", 1.0,
                                    [f"IP exceeded hourly limit ({len(ip_times)}/{limits['ip_messages_per_hour']})"],
                                    "block")
            return True
            
        # Check minimum interval
        if ip_times and (now - ip_times[-1]).total_seconds() < limits['min_interval_seconds']:
            self._create_abuse_signal(event, "rapid_fire", "medium", 0.9,
                                    ["Messages sent too quickly"], "throttle")
            return True
            
        # Update tracking
        ip_times.append(now)
        self.ip_requests[event.ip_address] = ip_times[-100:]  # Keep last 100
        
        return None

    def _calculate_bot_score(self, event: RequestEvent) -> float:
        """Calculate probability that request is from a bot"""
        score = 0.0
        
        # Check user agent
        bot_agents = ['bot', 'spider', 'crawler', 'scraper', 'curl', 'wget', 'python']
        if any(agent in event.user_agent.lower() for agent in bot_agents):
            score += 0.5
            
        # Check message patterns
        for pattern in self.config['patterns']['bot_patterns']:
            if re.search(pattern, event.message, re.IGNORECASE):
                score += 0.3
                
        # Check request timing patterns
        conv_messages = self.conversation_messages[event.conversation_id]
        if len(conv_messages) >= 3:
            # Check for consistent intervals (bot-like)
            intervals = []
            for i in range(1, len(conv_messages)):
                interval = (conv_messages[i][0] - conv_messages[i-1][0]).total_seconds()
                intervals.append(interval)
            
            if intervals:
                avg_interval = sum(intervals) / len(intervals)
                variance = sum((i - avg_interval) ** 2 for i in intervals) / len(intervals)
                if variance < 1.0:  # Very consistent timing
                    score += 0.3
                    
        # Store message
        conv_messages.append((event.timestamp, event.message))
        self.conversation_messages[event.conversation_id] = conv_messages[-20:]  # Keep last 20
        
        return min(score, 1.0)

    def _calculate_spam_score(self, event: RequestEvent) -> float:
        """Calculate spam probability"""
        score = 0.0
        
        # Check spam patterns
        for pattern in self.config['patterns']['spam_patterns']:
            if re.search(pattern, event.message, re.IGNORECASE):
                score += 0.4
                
        # Check for repeated messages
        conv_messages = self.conversation_messages[event.conversation_id]
        recent_messages = [msg for _, msg in conv_messages[-5:]]
        if recent_messages.count(event.message) >= 2:
            score += 0.5
            
        # Check for excessive links
        link_pattern = r'https?://\S+'
        links = re.findall(link_pattern, event.message)
        if len(links) >= 3:
            score += 0.3
            
        return min(score, 1.0)

    def _analyze_content(self, event: RequestEvent) -> Dict[str, Any]:
        """Use AI to analyze content for abuse patterns"""
        try:
            # Only analyze every 5th message to save API calls
            if event.conversation_id not in self.conversation_messages or \
               len(self.conversation_messages[event.conversation_id]) % 5 != 0:
                return {}
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "system",
                    "content": """Analyze this message for potential abuse. Return JSON with:
                    - abuse_type: none, spam, scam, harassment, off_topic_persistent
                    - confidence: 0.0 to 1.0
                    - reason: brief explanation
                    
                    Only flag as off_topic_persistent if user repeatedly ignores insurance context."""
                }, {
                    "role": "user",
                    "content": f"Message: {event.message}\nConversation messages: {len(self.conversation_messages[event.conversation_id])}"
                }],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=200
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            print(f"Abuse Prevention: AI analysis error: {e}")
            return {}

    def _create_abuse_signal(self, event: RequestEvent, abuse_type: str, severity: str,
                           confidence: float, indicators: List[str], action: str):
        """Create and queue an abuse signal"""
        signal = AbuseSignal(
            conversation_id=event.conversation_id,
            abuse_type=abuse_type,
            severity=severity,
            confidence=confidence,
            indicators=indicators,
            action=action,
            timestamp=event.timestamp,
            ip_address=event.ip_address
        )
        
        try:
            self.abuse_signals.put(signal, block=False)
            
            # Take immediate action for critical signals
            if severity == "critical" or action == "block":
                self.blocked_ips.add(event.ip_address)
                print(f"Abuse Prevention: Blocked IP {event.ip_address} - {indicators}")
                
        except Exception as e:
            print(f"Abuse Prevention: Error creating signal: {e}")

    def _cleanup_old_data(self):
        """Periodic cleanup of old tracking data"""
        try:
            now = datetime.now()
            cutoff = now - timedelta(hours=24)
            
            # Clean IP requests
            for ip in list(self.ip_requests.keys()):
                self.ip_requests[ip] = [t for t in self.ip_requests[ip] if t > cutoff]
                if not self.ip_requests[ip]:
                    del self.ip_requests[ip]
                    
            # Clean conversation scores
            if len(self.conversation_abuse_scores) > 1000:
                # Keep only recent conversations
                sorted_convs = sorted(self.conversation_abuse_scores.items(), 
                                    key=lambda x: x[1], reverse=True)
                self.conversation_abuse_scores = dict(sorted_convs[:500])
                
        except Exception as e:
            print(f"Abuse Prevention: Cleanup error: {e}")

    def check_request_allowed(self, ip_address: str, conversation_id: str) -> tuple[bool, Optional[str]]:
        """Quick check if a request should be allowed"""
        if ip_address in self.blocked_ips:
            return False, "Your IP has been blocked due to suspicious activity"
            
        if self.conversation_abuse_scores.get(conversation_id, 0) > 1.0:
            return False, "This conversation has been flagged for unusual activity"
            
        return True, None

    def get_abuse_signals(self) -> List[AbuseSignal]:
        """Get pending abuse signals"""
        signals = []
        try:
            while not self.abuse_signals.empty():
                signals.append(self.abuse_signals.get_nowait())
        except Empty:
            pass
        return signals

    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get current monitoring statistics"""
        return {
            'blocked_ips': len(self.blocked_ips),
            'monitored_conversations': len(self.conversation_messages),
            'high_risk_conversations': sum(1 for score in self.conversation_abuse_scores.values() if score > 0.5),
            'requests_last_hour': sum(len(times) for times in self.ip_requests.values()),
            'active': self.monitoring_active
        }

# Global instance
_abuse_prevention_agent = None

def get_abuse_prevention_agent() -> AbusePreventionAgent:
    """Get or create the global abuse prevention agent"""
    global _abuse_prevention_agent
    if _abuse_prevention_agent is None:
        _abuse_prevention_agent = AbusePreventionAgent()
    return _abuse_prevention_agent