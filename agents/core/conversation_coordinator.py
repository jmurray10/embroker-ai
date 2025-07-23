"""
Conversation Coordinator Agent
Ensures proper synchronization between chatbot sessions and Slack threads
"""
import json
import time
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class ConversationSession:
    """Represents a conversation session with mapping details"""
    conversation_id: str
    slack_thread_ts: Optional[str] = None
    slack_channel: Optional[str] = None
    created_at: float = None
    last_activity: float = None
    status: str = "active"  # active, escalated, resolved
    escalation_data: Optional[Dict[str, Any]] = None
    message_history: List[Dict[str, Any]] = None
    resolved_by: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        if self.last_activity is None:
            self.last_activity = time.time()
        if self.message_history is None:
            self.message_history = []

class ConversationCoordinator:
    """
    Agent responsible for coordinating chatbot sessions with Slack threads
    Ensures proper session continuity and message delivery
    """
    
    def __init__(self):
        self.sessions: Dict[str, ConversationSession] = {}
        self.thread_to_session: Dict[str, str] = {}  # thread_ts -> conversation_id
        self.pending_messages: Dict[str, List[Dict[str, Any]]] = {}
        self.persistence_file = '.conversation_sessions.json'
        self._load_sessions()
    
    def create_session(self, conversation_id: str = None) -> ConversationSession:
        """Create a new conversation session"""
        if conversation_id is None:
            conversation_id = f"chat_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
        
        session = ConversationSession(conversation_id=conversation_id)
        self.sessions[conversation_id] = session
        self._save_sessions()
        
        logger.info(f"[COORDINATOR] Created session: {conversation_id}")
        return session
    
    def escalate_session(self, conversation_id: str, slack_thread_ts: str, 
                        slack_channel: str, escalation_data: Dict[str, Any]) -> bool:
        """Escalate a session to Slack and create bidirectional mapping"""
        if conversation_id not in self.sessions:
            # Create session if it doesn't exist
            self.create_session(conversation_id)
        
        session = self.sessions[conversation_id]
        session.slack_thread_ts = slack_thread_ts
        session.slack_channel = slack_channel
        session.status = "escalated"
        session.escalation_data = escalation_data
        session.last_activity = time.time()
        
        # Create bidirectional mapping
        self.thread_to_session[slack_thread_ts] = conversation_id
        
        self._save_sessions()
        
        logger.info(f"[COORDINATOR] Escalated session {conversation_id} to Slack thread {slack_thread_ts}")
        return True
    
    def get_session_by_id(self, conversation_id: str) -> Optional[ConversationSession]:
        """Get session by conversation ID"""
        return self.sessions.get(conversation_id)
    
    def get_session_by_thread(self, thread_ts: str) -> Optional[ConversationSession]:
        """Get session by Slack thread timestamp"""
        conversation_id = self.thread_to_session.get(thread_ts)
        if conversation_id:
            return self.sessions.get(conversation_id)
        return None
    
    def queue_slack_message(self, thread_ts: str, message: str, 
                           sender_name: str, timestamp: float = None) -> bool:
        """Queue a message from Slack for delivery to chatbot"""
        session = self.get_session_by_thread(thread_ts)
        if not session:
            logger.warning(f"[COORDINATOR] No session found for thread {thread_ts}")
            # Debug: Show all available thread mappings
            logger.warning(f"[COORDINATOR] Available threads: {list(self.thread_to_session.keys())}")
            return False
        
        if timestamp is None:
            timestamp = time.time()
        
        # Check if this is a join notification to mark specialist as active
        conversation_id = session.conversation_id
        is_join_notification = "joined the conversation" in message.lower()
        if is_join_notification:
            session.status = "specialist_active"
            logger.info(f"[COORDINATOR] Specialist joined conversation {conversation_id} - AI will now step back")
        
        message_data = {
            'message': message,
            'sender': sender_name,
            'timestamp': timestamp,
            'type': 'system_notification' if is_join_notification else 'slack_reply',
            'delivered': False,
            'is_persistent': is_join_notification  # Join notifications persist in chat
        }
        
        # Add to pending messages
        conversation_id = session.conversation_id
        if conversation_id not in self.pending_messages:
            self.pending_messages[conversation_id] = []
        
        self.pending_messages[conversation_id].append(message_data)
        
        # Update session activity
        session.last_activity = time.time()
        session.message_history.append({
            'role': 'specialist',
            'content': message,
            'timestamp': timestamp,
            'sender': sender_name
        })
        
        # Force immediate save to persist messages
        self._save_sessions()
        
        logger.info(f"[COORDINATOR] Queued message '{message}' from {sender_name} for conversation {conversation_id}")
        logger.info(f"[COORDINATOR] Pending queue now has {len(self.pending_messages[conversation_id])} messages")
        return True
    
    def inject_summary_to_main_chat(self, conversation_id: str, summary: str) -> bool:
        """Inject specialist consultation summary back into main chat as AI response"""
        session = self.get_session_by_id(conversation_id)
        if not session:
            logger.warning(f"[COORDINATOR] No session found for {conversation_id}")
            return False
        
        # Add summary to conversation history as AI response
        if not session.conversation_history:
            session.conversation_history = []
        
        summary_message = f"Based on the specialist consultation: {summary}"
        
        session.conversation_history.append({
            'role': 'assistant',
            'content': summary_message,
            'timestamp': time.time()
        })
        
        # Also add to pending messages for immediate display
        if conversation_id not in self.pending_messages:
            self.pending_messages[conversation_id] = []
        
        self.pending_messages[conversation_id].append({
            'message': summary_message,
            'sender': 'AI Assistant',
            'timestamp': time.time(),
            'type': 'ai_summary',
            'delivered': False,
            'is_persistent': True
        })
        
        # Mark session as having specialist consultation completed
        session.status = "consultation_completed"
        self._save_sessions()
        
        logger.info(f"[COORDINATOR] Injected summary to main chat for {conversation_id}")
        return True
    
    def get_pending_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get pending messages for a conversation"""
        if conversation_id not in self.pending_messages:
            return []
        
        # Get undelivered messages
        pending = self.pending_messages[conversation_id]
        undelivered = [msg for msg in pending if not msg.get('delivered', False)]
        
        # Return copy without marking as delivered (defer marking until confirmation)
        if undelivered:
            logger.info(f"[COORDINATOR] Retrieved {len(undelivered)} pending messages for session {conversation_id}")
        
        return [msg.copy() for msg in undelivered]
    
    def mark_messages_delivered(self, conversation_id: str):
        """Mark all pending messages as delivered for a conversation"""
        if conversation_id not in self.pending_messages:
            return
        
        pending = self.pending_messages[conversation_id]
        delivered_count = 0
        
        # Mark all undelivered messages as delivered
        for msg in pending:
            if not msg.get('delivered', False):
                msg['delivered'] = True
                delivered_count += 1
        
        # Clean up old delivered messages
        current_time = time.time()
        self.pending_messages[conversation_id] = [
            msg for msg in pending 
            if not msg.get('delivered', False) or (current_time - msg['timestamp']) < 300
        ]
        
        self._save_sessions()
        
        if delivered_count > 0:
            logger.info(f"[COORDINATOR] Marked {delivered_count} messages as delivered for session {conversation_id}")
    
    def is_specialist_active(self, conversation_id: str) -> bool:
        """Check if a specialist is currently active for this conversation"""
        session = self.get_session_by_id(conversation_id)
        if not session:
            return False
        
        # Check if session is escalated and has active human specialist
        if session.status == "escalated" and session.slack_thread_ts is not None:
            # Check if any human specialists are currently active in the thread
            return self._check_slack_thread_active(session.slack_thread_ts)
        
        return False
    
    def mark_specialist_joined(self, conversation_id: str, specialist_user_id: str):
        """Mark that a human specialist has joined the conversation"""
        session = self.get_session_by_id(conversation_id)
        if session:
            if not hasattr(session, 'active_specialists'):
                session.active_specialists = set()
            session.active_specialists.add(specialist_user_id)
            session.status = "escalated"
            self._save_sessions()
            logger.info(f"[COORDINATOR] Specialist {specialist_user_id} joined conversation {conversation_id}")
    
    def mark_specialist_left(self, conversation_id: str, specialist_user_id: str):
        """Mark that a human specialist has left the conversation"""
        session = self.get_session_by_id(conversation_id)
        if session and hasattr(session, 'active_specialists'):
            session.active_specialists.discard(specialist_user_id)
            # If no specialists remain, conversation can be escalated again
            if not session.active_specialists:
                session.status = "active"
            self._save_sessions()
            logger.info(f"[COORDINATOR] Specialist {specialist_user_id} left conversation {conversation_id}")
    
    def _check_slack_thread_active(self, thread_ts: str) -> bool:
        """Check if the Slack thread has active human participants"""
        session = None
        for sess in self.sessions.values():
            if sess.slack_thread_ts == thread_ts:
                session = sess
                break
        
        if not session:
            return False
        
        # Check if any specialists are marked as active
        if hasattr(session, 'active_specialists') and session.active_specialists:
            return True
        
        return False
    
    def update_session_activity(self, conversation_id: str, 
                               user_message: str = None, ai_response: str = None):
        """Update session with new activity"""
        if conversation_id not in self.sessions:
            self.create_session(conversation_id)
        
        session = self.sessions[conversation_id]
        session.last_activity = time.time()
        
        if user_message:
            session.message_history.append({
                'role': 'user',
                'content': user_message,
                'timestamp': time.time()
            })
        
        if ai_response:
            session.message_history.append({
                'role': 'assistant',
                'content': ai_response,
                'timestamp': time.time()
            })
        
        self._save_sessions()
    
    def is_session_escalated(self, conversation_id: str) -> bool:
        """Check if a session is escalated to Slack"""
        session = self.get_session_by_id(conversation_id)
        return session and session.status == "escalated" and session.slack_thread_ts is not None
    
    def get_slack_thread_info(self, conversation_id: str) -> Optional[Dict[str, str]]:
        """Get Slack thread information for a session"""
        session = self.get_session_by_id(conversation_id)
        if session and session.slack_thread_ts:
            return {
                'thread_ts': session.slack_thread_ts,
                'channel': session.slack_channel
            }
        return None
    
    def resolve_session(self, conversation_id: str, resolution_reason: str = "completed"):
        """Mark a session as resolved"""
        if conversation_id in self.sessions:
            self.sessions[conversation_id].status = "resolved"
            self.sessions[conversation_id].resolved_by = resolution_reason
            self.sessions[conversation_id].last_activity = time.time()
            self._save_sessions()
            logger.info(f"[COORDINATOR] Resolved session {conversation_id}: {resolution_reason}")
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Clean up old inactive sessions"""
        current_time = time.time()
        cutoff_time = current_time - (max_age_hours * 3600)
        
        old_sessions = [
            conv_id for conv_id, session in self.sessions.items()
            if session.last_activity < cutoff_time and session.status == "resolved"
        ]
        
        for conv_id in old_sessions:
            session = self.sessions[conv_id]
            if session.slack_thread_ts:
                del self.thread_to_session[session.slack_thread_ts]
            del self.sessions[conv_id]
            if conv_id in self.pending_messages:
                del self.pending_messages[conv_id]
        
        if old_sessions:
            self._save_sessions()
            logger.info(f"[COORDINATOR] Cleaned up {len(old_sessions)} old sessions")
    
    def get_active_sessions(self) -> List[ConversationSession]:
        """Get all active conversation sessions for monitoring"""
        return [s for s in self.sessions.values() if s.status == "active"]
    
    def get_escalated_sessions(self) -> List[ConversationSession]:
        """Get all escalated conversation sessions"""
        return [s for s in self.sessions.values() if s.status == "escalated"]
    
    def get_resolved_sessions(self) -> List[ConversationSession]:
        """Get all resolved conversation sessions"""
        return [s for s in self.sessions.values() if s.status == "resolved"]

    def get_system_status(self) -> Dict[str, Any]:
        """Get coordinator system status"""
        resolved_sessions = self.get_resolved_sessions()
        return {
            'total_sessions': len(self.sessions),
            'escalated_sessions': len([s for s in self.sessions.values() if s.status == "escalated"]),
            'active_sessions': len([s for s in self.sessions.values() if s.status == "active"]),
            'resolved_sessions': len(resolved_sessions),
            'pending_message_queues': len(self.pending_messages),
            'thread_mappings': len(self.thread_to_session),
            'resolution_breakdown': {
                'slack_resolved': len([s for s in resolved_sessions if s.resolved_by and 'resolved by' in s.resolved_by]),
                'auto_resolved': len([s for s in resolved_sessions if s.resolved_by == 'completed']),
                'timeout_resolved': len([s for s in resolved_sessions if s.resolved_by and 'timeout' in s.resolved_by])
            }
        }
    
    def _save_sessions(self):
        """Save sessions to persistence file"""
        try:
            data = {
                'sessions': {
                    conv_id: {
                        'conversation_id': session.conversation_id,
                        'slack_thread_ts': session.slack_thread_ts,
                        'slack_channel': session.slack_channel,
                        'created_at': session.created_at,
                        'last_activity': session.last_activity,
                        'status': session.status,
                        'escalation_data': session.escalation_data,
                        'message_history': session.message_history[-50:],  # Keep last 50 messages
                        'resolved_by': session.resolved_by
                    }
                    for conv_id, session in self.sessions.items()
                },
                'thread_to_session': self.thread_to_session,
                'pending_messages': self.pending_messages
            }
            
            with open(self.persistence_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"[COORDINATOR] Error saving sessions: {e}")
    
    def _load_sessions(self):
        """Load sessions from persistence file"""
        try:
            with open(self.persistence_file, 'r') as f:
                data = json.load(f)
            
            # Restore sessions
            for conv_id, session_data in data.get('sessions', {}).items():
                session = ConversationSession(
                    conversation_id=session_data['conversation_id'],
                    slack_thread_ts=session_data.get('slack_thread_ts'),
                    slack_channel=session_data.get('slack_channel'),
                    created_at=session_data.get('created_at'),
                    last_activity=session_data.get('last_activity'),
                    status=session_data.get('status', 'active'),
                    escalation_data=session_data.get('escalation_data'),
                    message_history=session_data.get('message_history', []),
                    resolved_by=session_data.get('resolved_by')
                )
                self.sessions[conv_id] = session
            
            # Restore mappings
            self.thread_to_session = data.get('thread_to_session', {})
            self.pending_messages = data.get('pending_messages', {})
            
            logger.info(f"[COORDINATOR] Loaded {len(self.sessions)} sessions with {len(self.thread_to_session)} thread mappings")
            
        except FileNotFoundError:
            logger.info("[COORDINATOR] No existing sessions found, starting fresh")
        except Exception as e:
            logger.error(f"[COORDINATOR] Error loading sessions: {e}")

# Global coordinator instance
conversation_coordinator = ConversationCoordinator()