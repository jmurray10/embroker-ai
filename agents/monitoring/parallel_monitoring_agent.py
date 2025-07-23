"""
Enhanced Parallel Monitoring Agent (PMA) v2.0
Continuously monitors conversations asynchronously without impacting main chat performance.
Detects escalation triggers and signals the orchestration system when human intervention is needed.

NEW FEATURES:
- Real-time performance analytics
- Advanced conversation insights
- Persistent metrics storage
- Enhanced escalation logic
- Live monitoring dashboard
"""

import asyncio
import os
import json
import time
import statistics
import sqlite3
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import threading
from queue import Queue, Empty
from collections import defaultdict, deque
import openai
from dotenv import load_dotenv

load_dotenv()

@dataclass
class ConversationEvent:
    """Represents a conversation event for monitoring"""
    conversation_id: str
    user_message: str
    assistant_response: str
    timestamp: datetime
    user_sentiment: Optional[str] = None
    escalation_indicators: Optional[List[str]] = None
    response_time_ms: Optional[float] = None
    message_length: Optional[int] = None
    ai_confidence: Optional[float] = None
    session_metadata: Optional[Dict[str, Any]] = None

@dataclass
class EscalationSignal:
    """Represents an escalation decision from the monitoring agent"""
    conversation_id: str
    escalation_reason: str
    urgency_level: str  # low, medium, high, critical
    indicators: List[str]
    recommendation: str
    timestamp: datetime
    confidence_score: float
    escalation_type: str  # sentiment, explicit, technical, performance
    context_data: Dict[str, Any]

@dataclass
class PerformanceMetrics:
    """Performance metrics for monitoring"""
    avg_response_time: float
    total_conversations: int
    escalation_rate: float
    user_satisfaction_score: float
    error_rate: float
    peak_concurrent_users: int
    timestamp: datetime

@dataclass
class ConversationAnalytics:
    """Analytics data for a conversation"""
    conversation_id: str
    duration_minutes: float
    message_count: int
    avg_response_time: float
    sentiment_trend: List[str]
    topics_discussed: List[str]
    resolution_status: str  # resolved, escalated, abandoned
    user_satisfaction: Optional[float] = None

class ParallelMonitoringAgent:
    """
    Asynchronous monitoring agent that observes conversations and detects escalation needs
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the enhanced monitoring agent with comprehensive capabilities"""
        # API Configuration
        self.api_key = api_key or os.getenv("OPENAI_MONITORING_KEY") or os.getenv("POC_OPENAI_API")
        self.client = openai.OpenAI(api_key=self.api_key)
        
        # Log which API key is being used for transparency
        if os.getenv("OPENAI_MONITORING_KEY"):
            print("PMA v2.0: Using dedicated monitoring API key")
        else:
            print("PMA v2.0: Using shared API key (consider setting OPENAI_MONITORING_KEY)")
        
        # Core Monitoring Configuration
        self.monitoring_active = True
        self.event_queue = Queue(maxsize=1000)  # Prevent memory overflow
        self.escalation_signals = Queue(maxsize=100)
        
        # Enhanced State Tracking
        self.conversation_states = {}
        self.escalation_history = {}
        self.performance_metrics = deque(maxlen=100)  # Last 100 metric snapshots
        self.conversation_analytics = {}
        
        # Real-time Analytics
        self.active_conversations = set()
        self.hourly_stats = defaultdict(lambda: {
            'conversations': 0, 'escalations': 0, 'avg_response_time': 0
        })
        
        # Performance Tracking
        self.response_times = deque(maxlen=1000)
        self.error_count = 0
        self.total_events_processed = 0
        self.start_time = datetime.now()
        
        # Initialize database for persistent analytics
        self._init_analytics_db()
        
        # Start enhanced monitoring threads
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.analytics_thread = threading.Thread(target=self._analytics_loop, daemon=True)
        self.monitoring_thread.start()
        self.analytics_thread.start()
        
        print("Enhanced Parallel Monitoring Agent v2.0 initialized with analytics")

    def add_conversation_event(self, conversation_id: str, user_message: str, assistant_response: str, 
                             response_time_ms: Optional[float] = None, ai_confidence: Optional[float] = None,
                             session_metadata: Optional[Dict[str, Any]] = None):
        """Add a conversation event to the monitoring queue (non-blocking)"""
        try:
            event = ConversationEvent(
                conversation_id=conversation_id,
                user_message=user_message,
                assistant_response=assistant_response,
                timestamp=datetime.now(),
                response_time_ms=response_time_ms,
                message_length=len(user_message),
                ai_confidence=ai_confidence,
                session_metadata=session_metadata
            )
            
            # Add to queue with overflow protection
            if not self.event_queue.full():
                self.event_queue.put(event, block=False)
                self.active_conversations.add(conversation_id)
                
                # Track response times for analytics
                if response_time_ms:
                    self.response_times.append(response_time_ms)
            else:
                print("PMA: Event queue full, dropping oldest events")
                try:
                    self.event_queue.get_nowait()  # Remove oldest
                    self.event_queue.put(event, block=False)
                except Empty:
                    pass
                    
        except Exception as e:
            self.error_count += 1
            print(f"PMA: Error adding event to queue: {e}")

    def _monitoring_loop(self):
        """Main monitoring loop that processes events asynchronously"""
        while self.monitoring_active:
            try:
                # Process events with timeout to avoid blocking
                try:
                    event = self.event_queue.get(timeout=1.0)
                    self._analyze_conversation_event(event)
                    self.event_queue.task_done()
                except Empty:
                    continue
                    
            except Exception as e:
                print(f"PMA: Error in monitoring loop: {e}")
                time.sleep(1)

    def _analyze_conversation_event(self, event: ConversationEvent):
        """Analyze a conversation event for escalation triggers"""
        try:
            # Update conversation state
            if event.conversation_id not in self.conversation_states:
                self.conversation_states[event.conversation_id] = {
                    'message_count': 0,
                    'frustration_indicators': [],
                    'unresolved_queries': 0,
                    'last_escalation_check': datetime.now(),
                    'sentiment_history': []
                }
            
            state = self.conversation_states[event.conversation_id]
            state['message_count'] += 1
            
            # Analyze the conversation using OpenAI
            analysis = self._get_escalation_analysis(event)
            
            # Update state with analysis
            if analysis.get('sentiment'):
                state['sentiment_history'].append(analysis['sentiment'])
                # Keep only last 5 sentiment readings
                state['sentiment_history'] = state['sentiment_history'][-5:]
            
            # Check escalation criteria
            escalation_needed = self._evaluate_escalation_criteria(event, analysis, state)
            
            if escalation_needed:
                self._generate_escalation_signal(event, analysis, state)
                
            # Update analytics
            self.total_events_processed += 1
            
            # Track conversation timing
            if event.conversation_id not in self.conversation_states:
                self.conversation_states[event.conversation_id]['start_time'] = event.timestamp
            self.conversation_states[event.conversation_id]['last_activity'] = event.timestamp
            
            # Store conversation analytics
            self._update_conversation_analytics(event, analysis)
                
        except Exception as e:
            print(f"PMA: Error analyzing event: {e}")

    def _get_escalation_analysis(self, event: ConversationEvent) -> Dict[str, Any]:
        """Use OpenAI to analyze conversation for escalation indicators"""
        try:
            analysis_prompt = f"""
            Analyze this conversation exchange for escalation indicators:
            
            User: {event.user_message}
            Assistant: {event.assistant_response}
            
            Provide analysis in JSON format:
            {{
                "sentiment": "positive|neutral|negative|frustrated|angry",
                "frustration_level": 0-10,
                "unresolved_query": true/false,
                "complexity_level": "low|medium|high",
                "escalation_indicators": ["list", "of", "indicators"],
                "requires_human": true/false,
                "urgency": "low|medium|high|critical",
                "reasoning": "brief explanation"
            }}
            
            Look for:
            - EXPLICIT requests for human agents ("I want to talk to a human", "transfer me to an agent")
            - Severe user frustration or anger (not just normal questions)
            - Multiple failed attempts by AI to resolve the same issue
            - Compliance violations or legal concerns
            - Users expressing they want to cancel or leave
            
            DO NOT escalate for:
            - Normal insurance questions (coverage limits, claim examples, policy details)
            - Educational questions about insurance concepts
            - Requests for quotes or information
            - General customer service inquiries
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Use faster model for monitoring
                messages=[
                    {"role": "system", "content": "You are an expert conversation analyst. Provide accurate JSON analysis."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.1,
                max_tokens=300
            )
            
            # Parse JSON response
            analysis_text = response.choices[0].message.content
            if analysis_text:
                analysis_text = analysis_text.strip()
                if analysis_text.startswith("```json"):
                    analysis_text = analysis_text[7:-3]
                elif analysis_text.startswith("```"):
                    analysis_text = analysis_text[3:-3]
            else:
                analysis_text = "{}"
                
            return json.loads(analysis_text)
            
        except Exception as e:
            print(f"PMA: Error in OpenAI analysis: {e}")
            return {
                "sentiment": "neutral",
                "frustration_level": 0,
                "unresolved_query": False,
                "complexity_level": "low",
                "escalation_indicators": [],
                "requires_human": False,
                "urgency": "low",
                "reasoning": "Analysis failed"
            }

    def _evaluate_escalation_criteria(self, event: ConversationEvent, analysis: Dict[str, Any], state: Dict[str, Any]) -> bool:
        """Evaluate if escalation is needed based on analysis and conversation state"""
        
        # Check if human specialist is currently active (prevents duplicate escalation)
        if self._is_human_specialist_active(event.conversation_id):
            return False
        
        # Check for explicit human agent requests in user message
        user_msg_lower = event.user_message.lower()
        explicit_keywords = ['human', 'agent', 'transfer', 'speak to someone', 'representative', 'person']
        if any(keyword in user_msg_lower for keyword in explicit_keywords):
            return True
        
        # Only escalate for CRITICAL urgency (not high)
        if analysis.get('urgency') == 'critical':
            return True
            
        # Much higher threshold for frustration (9+ instead of 7+)
        frustration_level = analysis.get('frustration_level', 0)
        if frustration_level >= 9:
            return True
            
        # Require consistent angry sentiment (not just frustrated/negative)
        recent_sentiments = state.get('sentiment_history', [])
        if len(recent_sentiments) >= 4:
            angry_count = sum(1 for s in recent_sentiments[-4:] if s == 'angry')
            if angry_count >= 3:
                return True
        
        # Much longer conversation requirement (12+ messages instead of 8+)
        message_count = state.get('message_count', 0)
        if message_count >= 12 and analysis.get('unresolved_query', False):
            return True
            
        # Remove complexity-based escalation entirely - AI should handle insurance questions
        # Complex insurance questions are exactly what the AI is designed for
            
        return False

    def _is_human_specialist_active(self, conversation_id: str) -> bool:
        """Check if a human specialist is currently active in the conversation"""
        try:
            # Import here to avoid circular imports
            from agents.core.conversation_coordinator import conversation_coordinator
            return conversation_coordinator.is_specialist_active(conversation_id)
        except Exception:
            return False

    def _generate_escalation_signal(self, event: ConversationEvent, analysis: Dict[str, Any], state: Dict[str, Any]):
        """Generate enhanced escalation signal for the orchestration system"""
        
        # Avoid duplicate escalations
        if event.conversation_id in self.escalation_history:
            last_escalation = self.escalation_history[event.conversation_id]
            if datetime.now() - last_escalation < timedelta(minutes=5):
                return
        
        # Determine escalation type
        escalation_type = self._determine_escalation_type(analysis, state)
        
        # Calculate confidence score
        confidence_score = self._calculate_escalation_confidence(analysis, state)
        
        escalation_signal = EscalationSignal(
            conversation_id=event.conversation_id,
            escalation_reason=analysis.get('reasoning', 'Escalation criteria met'),
            urgency_level=analysis.get('urgency', 'medium'),
            indicators=analysis.get('escalation_indicators', []),
            recommendation=self._get_escalation_recommendation(analysis, state),
            timestamp=datetime.now(),
            confidence_score=confidence_score,
            escalation_type=escalation_type,
            context_data={
                'message_count': state.get('message_count', 0),
                'sentiment_history': state.get('sentiment_history', []),
                'conversation_duration': (datetime.now() - state.get('start_time', datetime.now())).total_seconds() / 60
            }
        )
        
        # Add to escalation queue
        self.escalation_signals.put(escalation_signal)
        self.escalation_history[event.conversation_id] = datetime.now()
        
        # Store in database
        self._store_escalation_event(escalation_signal)
        
        print(f"PMA: {escalation_type} escalation signal generated for conversation {event.conversation_id[:8]}... (confidence: {confidence_score:.2f})")

    def _determine_escalation_type(self, analysis: Dict[str, Any], state: Dict[str, Any]) -> str:
        """Determine the type of escalation"""
        user_msg_lower = analysis.get('user_message', '').lower()
        
        if any(keyword in user_msg_lower for keyword in ['human', 'agent', 'transfer', 'person']):
            return 'explicit'
        elif analysis.get('frustration_level', 0) >= 8:
            return 'sentiment'
        elif analysis.get('complexity_level') == 'high':
            return 'technical'
        elif state.get('message_count', 0) >= 10:
            return 'performance'
        else:
            return 'general'

    def _calculate_escalation_confidence(self, analysis: Dict[str, Any], state: Dict[str, Any]) -> float:
        """Calculate confidence score for escalation decision"""
        confidence = 0.5  # Base confidence
        
        # Boost confidence for explicit requests
        if 'explicit' in analysis.get('escalation_indicators', []):
            confidence += 0.4
            
        # Boost for high frustration
        frustration = analysis.get('frustration_level', 0)
        if frustration >= 8:
            confidence += 0.3
        elif frustration >= 6:
            confidence += 0.1
            
        # Boost for consistent negative sentiment
        recent_sentiments = state.get('sentiment_history', [])[-3:]
        negative_count = sum(1 for s in recent_sentiments if s in ['negative', 'frustrated', 'angry'])
        if len(recent_sentiments) >= 3 and negative_count >= 2:
            confidence += 0.2
            
        # Boost for long conversations
        message_count = state.get('message_count', 0)
        if message_count >= 12:
            confidence += 0.2
        elif message_count >= 8:
            confidence += 0.1
            
        return min(1.0, confidence)

    def _store_escalation_event(self, escalation: EscalationSignal):
        """Store escalation event in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO escalation_events 
                (conversation_id, timestamp, escalation_type, urgency_level, reason, confidence_score)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (escalation.conversation_id, escalation.timestamp, escalation.escalation_type, 
                  escalation.urgency_level, escalation.escalation_reason, escalation.confidence_score))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"PMA: Error storing escalation event: {e}")

    def _update_conversation_analytics(self, event: ConversationEvent, analysis: Dict[str, Any]):
        """Update conversation analytics with latest data"""
        try:
            conv_id = event.conversation_id
            state = self.conversation_states.get(conv_id, {})
            
            # Calculate conversation metrics
            start_time = state.get('start_time', event.timestamp)
            duration_minutes = (event.timestamp - start_time).total_seconds() / 60
            
            analytics = ConversationAnalytics(
                conversation_id=conv_id,
                duration_minutes=duration_minutes,
                message_count=state.get('message_count', 0),
                avg_response_time=event.response_time_ms or 0,
                sentiment_trend=state.get('sentiment_history', []),
                topics_discussed=self._extract_topics(event.user_message),
                resolution_status='active' if conv_id not in self.escalation_history else 'escalated'
            )
            
            self.conversation_analytics[conv_id] = analytics
            
            # Store in database periodically
            if state.get('message_count', 0) % 5 == 0:  # Every 5 messages
                self._store_conversation_metrics(analytics)
                
        except Exception as e:
            print(f"PMA: Error updating conversation analytics: {e}")

    def _extract_topics(self, message: str) -> List[str]:
        """Extract topics from user message using keyword matching"""
        topics = []
        insurance_keywords = {
            'cyber': ['cyber', 'data breach', 'hacking', 'ransomware'],
            'epli': ['epli', 'employment', 'harassment', 'discrimination'],
            'do': ['directors', 'officers', 'd&o', 'board'],
            'general_liability': ['general liability', 'slip and fall', 'property damage'],
            'professional': ['professional liability', 'errors', 'omissions', 'e&o'],
            'quote': ['quote', 'pricing', 'cost', 'premium'],
            'claim': ['claim', 'file claim', 'coverage'],
            'policy': ['policy', 'terms', 'conditions', 'limits']
        }
        
        message_lower = message.lower()
        for topic, keywords in insurance_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                topics.append(topic)
                
        return topics

    def _store_conversation_metrics(self, analytics: ConversationAnalytics):
        """Store conversation metrics in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Calculate sentiment score
            sentiment_score = self._calculate_sentiment_score(analytics.sentiment_trend)
            
            cursor.execute('''
                INSERT OR REPLACE INTO conversation_metrics 
                (conversation_id, timestamp, message_count, avg_response_time, sentiment_score, escalated, resolution_status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (analytics.conversation_id, datetime.now(), analytics.message_count, 
                  analytics.avg_response_time, sentiment_score, 
                  analytics.resolution_status == 'escalated', analytics.resolution_status))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"PMA: Error storing conversation metrics: {e}")

    def _calculate_sentiment_score(self, sentiment_trend: List[str]) -> float:
        """Calculate numeric sentiment score from sentiment history"""
        if not sentiment_trend:
            return 0.5
            
        sentiment_values = {
            'positive': 1.0,
            'neutral': 0.5,
            'negative': 0.2,
            'frustrated': 0.1,
            'angry': 0.0
        }
        
        scores = [sentiment_values.get(s, 0.5) for s in sentiment_trend]
        return statistics.mean(scores)

    def _get_escalation_recommendation(self, analysis: Dict[str, Any], state: Dict[str, Any]) -> str:
        """Generate specific recommendation for handling the escalation"""
        
        urgency = analysis.get('urgency', 'medium')
        frustration = analysis.get('frustration_level', 0)
        complexity = analysis.get('complexity_level', 'medium')
        
        if urgency == 'critical':
            return "Immediate escalation to senior specialist required"
        elif frustration >= 7:
            return "Customer is frustrated - prioritize empathetic response"
        elif complexity == 'high':
            return "Complex technical query - route to subject matter expert"
        elif state.get('message_count', 0) >= 8:
            return "Long conversation - consider fresh perspective from human agent"
        else:
            return "Standard escalation to available specialist"

    def get_escalation_signals(self) -> List[EscalationSignal]:
        """Get all pending escalation signals (non-blocking)"""
        signals = []
        try:
            while True:
                signal = self.escalation_signals.get_nowait()
                signals.append(signal)
        except Empty:
            pass
        return signals

    def get_conversation_status(self, conversation_id: str) -> Dict[str, Any]:
        """Get current monitoring status for a conversation"""
        state = self.conversation_states.get(conversation_id, {})
        return {
            'conversation_id': conversation_id,
            'message_count': state.get('message_count', 0),
            'last_sentiment': state.get('sentiment_history', ['neutral'])[-1],
            'escalated': conversation_id in self.escalation_history,
            'monitoring_active': True
        }

    def _init_analytics_db(self):
        """Initialize SQLite database for persistent analytics"""
        try:
            self.db_path = 'monitoring_analytics.db'
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables for analytics
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversation_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT,
                    timestamp DATETIME,
                    message_count INTEGER,
                    avg_response_time REAL,
                    sentiment_score REAL,
                    escalated BOOLEAN,
                    resolution_status TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME,
                    active_conversations INTEGER,
                    avg_response_time REAL,
                    escalation_rate REAL,
                    error_rate REAL,
                    events_processed INTEGER
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS escalation_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT,
                    timestamp DATETIME,
                    escalation_type TEXT,
                    urgency_level TEXT,
                    reason TEXT,
                    confidence_score REAL
                )
            ''')
            
            conn.commit()
            conn.close()
            print("PMA: Analytics database initialized")
            
        except Exception as e:
            print(f"PMA: Error initializing analytics database: {e}")

    def _analytics_loop(self):
        """Background analytics processing loop"""
        while self.monitoring_active:
            try:
                time.sleep(30)  # Run analytics every 30 seconds
                self._capture_performance_snapshot()
                self._cleanup_old_data()
            except Exception as e:
                print(f"PMA: Error in analytics loop: {e}")
                time.sleep(5)

    def _capture_performance_snapshot(self):
        """Capture current performance metrics"""
        try:
            now = datetime.now()
            
            # Calculate metrics
            avg_response_time = statistics.mean(self.response_times) if self.response_times else 0
            escalation_rate = len(self.escalation_history) / max(len(self.conversation_states), 1)
            error_rate = self.error_count / max(self.total_events_processed, 1)
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO performance_snapshots 
                (timestamp, active_conversations, avg_response_time, escalation_rate, error_rate, events_processed)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (now, len(self.active_conversations), avg_response_time, escalation_rate, error_rate, self.total_events_processed))
            
            conn.commit()
            conn.close()
            
            # Store in memory for quick access
            metrics = PerformanceMetrics(
                avg_response_time=avg_response_time,
                total_conversations=len(self.conversation_states),
                escalation_rate=escalation_rate,
                user_satisfaction_score=self._calculate_satisfaction_score(),
                error_rate=error_rate,
                peak_concurrent_users=len(self.active_conversations),
                timestamp=now
            )
            self.performance_metrics.append(metrics)
            
        except Exception as e:
            print(f"PMA: Error capturing performance snapshot: {e}")

    def _calculate_satisfaction_score(self) -> float:
        """Calculate user satisfaction score based on sentiment and escalations"""
        try:
            if not self.conversation_states:
                return 0.0
                
            positive_sentiments = 0
            total_sentiments = 0
            
            for state in self.conversation_states.values():
                sentiments = state.get('sentiment_history', [])
                for sentiment in sentiments:
                    total_sentiments += 1
                    if sentiment in ['positive', 'neutral']:
                        positive_sentiments += 1
                        
            if total_sentiments == 0:
                return 0.5  # Neutral baseline
                
            base_score = positive_sentiments / total_sentiments
            
            # Penalize for escalations
            escalation_penalty = min(0.3, len(self.escalation_history) * 0.1)
            
            return max(0.0, min(1.0, base_score - escalation_penalty))
            
        except Exception:
            return 0.5

    def _cleanup_old_data(self):
        """Clean up old data to prevent memory leaks"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            # Clean conversation states for conversations older than 24 hours
            old_conversations = []
            for conv_id, state in self.conversation_states.items():
                if state.get('last_activity', datetime.now()) < cutoff_time:
                    old_conversations.append(conv_id)
                    
            for conv_id in old_conversations:
                if conv_id in self.conversation_states:
                    del self.conversation_states[conv_id]
                if conv_id in self.active_conversations:
                    self.active_conversations.remove(conv_id)
                    
            # Clean database records older than 7 days
            week_ago = datetime.now() - timedelta(days=7)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM performance_snapshots WHERE timestamp < ?', (week_ago,))
            cursor.execute('DELETE FROM conversation_metrics WHERE timestamp < ?', (week_ago,))
            cursor.execute('DELETE FROM escalation_events WHERE timestamp < ?', (week_ago,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"PMA: Error cleaning up old data: {e}")

    def get_analytics_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive analytics dashboard data"""
        try:
            now = datetime.now()
            
            # Recent performance metrics
            recent_metrics = list(self.performance_metrics)[-10:] if self.performance_metrics else []
            
            # Real-time stats
            current_stats = {
                'active_conversations': len(self.active_conversations),
                'total_conversations_today': self._get_conversations_today(),
                'escalations_today': self._get_escalations_today(),
                'avg_response_time': statistics.mean(self.response_times) if self.response_times else 0,
                'current_satisfaction_score': self._calculate_satisfaction_score(),
                'uptime_hours': (now - self.start_time).total_seconds() / 3600,
                'events_processed': self.total_events_processed,
                'error_rate': self.error_count / max(self.total_events_processed, 1)
            }
            
            # Trend data
            trend_data = {
                'hourly_conversations': self._get_hourly_trends(),
                'response_time_trend': [m.avg_response_time for m in recent_metrics],
                'satisfaction_trend': [m.user_satisfaction_score for m in recent_metrics],
                'escalation_trend': [m.escalation_rate for m in recent_metrics]
            }
            
            # Top conversation insights
            insights = self._generate_insights()
            
            return {
                'timestamp': now.isoformat(),
                'status': 'active' if self.monitoring_active else 'inactive',
                'current_stats': current_stats,
                'recent_metrics': [asdict(m) for m in recent_metrics],
                'trend_data': trend_data,
                'insights': insights,
                'version': '2.0'
            }
            
        except Exception as e:
            print(f"PMA: Error generating dashboard: {e}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}

    def _get_conversations_today(self) -> int:
        """Get number of conversations started today"""
        try:
            today = datetime.now().date()
            count = 0
            for state in self.conversation_states.values():
                if state.get('start_time', datetime.now()).date() == today:
                    count += 1
            return count
        except Exception:
            return 0

    def _get_escalations_today(self) -> int:
        """Get number of escalations today"""
        try:
            today = datetime.now().date()
            count = 0
            for escalation_time in self.escalation_history.values():
                if escalation_time.date() == today:
                    count += 1
            return count
        except Exception:
            return 0

    def _get_hourly_trends(self) -> List[Dict[str, Any]]:
        """Get hourly conversation trends for the last 24 hours"""
        try:
            trends = []
            now = datetime.now()
            
            for i in range(24):
                hour = now - timedelta(hours=i)
                hour_key = hour.strftime('%Y-%m-%d %H')
                
                trends.append({
                    'hour': hour.strftime('%H:00'),
                    'conversations': self.hourly_stats[hour_key]['conversations'],
                    'escalations': self.hourly_stats[hour_key]['escalations'],
                    'avg_response_time': self.hourly_stats[hour_key]['avg_response_time']
                })
                
            return list(reversed(trends))
        except Exception:
            return []

    def _generate_insights(self) -> List[str]:
        """Generate actionable insights from monitoring data"""
        insights = []
        
        try:
            # Response time insights
            if self.response_times:
                avg_time = statistics.mean(self.response_times)
                if avg_time > 5000:  # > 5 seconds
                    insights.append(f"High response times detected (avg: {avg_time:.0f}ms)")
                elif avg_time < 2000:  # < 2 seconds
                    insights.append(f"Excellent response times (avg: {avg_time:.0f}ms)")
            
            # Escalation insights
            escalation_rate = len(self.escalation_history) / max(len(self.conversation_states), 1)
            if escalation_rate > 0.2:  # > 20%
                insights.append(f"High escalation rate: {escalation_rate:.1%}")
            elif escalation_rate < 0.05:  # < 5%
                insights.append(f"Low escalation rate: {escalation_rate:.1%}")
            
            # Satisfaction insights
            satisfaction = self._calculate_satisfaction_score()
            if satisfaction > 0.8:
                insights.append(f"High user satisfaction: {satisfaction:.1%}")
            elif satisfaction < 0.6:
                insights.append(f"Low user satisfaction: {satisfaction:.1%}")
            
            # Activity insights
            if len(self.active_conversations) > 10:
                insights.append(f"High activity: {len(self.active_conversations)} active conversations")
            
            if not insights:
                insights.append("All metrics within normal ranges")
                
        except Exception as e:
            insights.append(f"Error generating insights: {str(e)}")
            
        return insights

    def stop_monitoring(self):
        """Stop the monitoring agent"""
        print("PMA: Shutting down enhanced monitoring...")
        self.monitoring_active = False
        
        if self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=2)
        if self.analytics_thread.is_alive():
            self.analytics_thread.join(timeout=2)
            
        print("PMA: Enhanced monitoring stopped")

# Global monitoring agent instance
_monitoring_agent = None

def get_monitoring_agent() -> ParallelMonitoringAgent:
    """Get or create the global monitoring agent instance"""
    global _monitoring_agent
    if _monitoring_agent is None:
        _monitoring_agent = ParallelMonitoringAgent()
    return _monitoring_agent

def monitor_conversation(conversation_id: str, user_message: str, assistant_response: str, 
                        response_time_ms: Optional[float] = None, ai_confidence: Optional[float] = None,
                        session_metadata: Optional[Dict[str, Any]] = None):
    """Add conversation event to enhanced monitoring (async, non-blocking)"""
    agent = get_monitoring_agent()
    agent.add_conversation_event(conversation_id, user_message, assistant_response, 
                                response_time_ms, ai_confidence, session_metadata)

def check_escalation_signals() -> List[EscalationSignal]:
    """Check for pending escalation signals"""
    agent = get_monitoring_agent()
    return agent.get_escalation_signals()

def get_conversation_monitoring_status(conversation_id: str) -> Dict[str, Any]:
    """Get monitoring status for a specific conversation"""
    agent = get_monitoring_agent()
    return agent.get_conversation_status(conversation_id)