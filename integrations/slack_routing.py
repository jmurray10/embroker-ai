# slack_routing.py
import os
import json
from typing import Dict, Any, Optional, List
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import threading
import time

class SlackRouter:
    def __init__(self):
        """Initialize Slack router for escalating conversations to underwriters."""
        self.slack_token = os.environ.get('SLACK_BOT_TOKEN')
        self.escalation_channel = os.environ.get('SLACK_ESCALATION_CHANNEL')
        
        if self.slack_token:
            self.client = WebClient(token=self.slack_token)
        else:
            self.client = None
            print("Warning: SLACK_BOT_TOKEN not found. Slack routing disabled.")
        
        # Track active escalations and pending responses
        self.active_escalations = {}  # conversation_id -> escalation_info
        self.thread_to_conversation = {}  # thread_ts -> conversation_id (for Events API lookup)
        self.pending_responses = {}  # conversation_id -> list of pending messages
        
        # Rate limiting
        self.last_api_call = 0
        self.min_api_interval = 1.0  # Minimum 1 second between API calls
        
        # Load persisted thread mappings
        self._load_thread_mappings()
    
    def _rate_limited_api_call(self, api_call_func, *args, **kwargs):
        """Execute Slack API call with rate limiting"""
        import time
        
        current_time = time.time()
        time_since_last_call = current_time - self.last_api_call
        
        if time_since_last_call < self.min_api_interval:
            sleep_time = self.min_api_interval - time_since_last_call
            time.sleep(sleep_time)
        
        try:
            result = api_call_func(*args, **kwargs)
            self.last_api_call = time.time()
            return result
        except Exception as e:
            if "ratelimited" in str(e).lower():
                print(f"Rate limited, waiting 5 seconds before retry...")
                time.sleep(5)
                try:
                    result = api_call_func(*args, **kwargs)
                    self.last_api_call = time.time()
                    return result
                except Exception as retry_e:
                    print(f"Retry failed: {retry_e}")
                    raise retry_e
            else:
                raise e
    
    def _load_thread_mappings(self):
        """Load persisted thread mappings from file"""
        try:
            with open('.thread_mappings.json', 'r') as f:
                data = json.load(f)
                self.thread_to_conversation = data.get('thread_to_conversation', {})
                self.active_escalations = data.get('active_escalations', {})
                print(f"[DEBUG] Loaded {len(self.thread_to_conversation)} thread mappings")
        except FileNotFoundError:
            print("[DEBUG] No persisted thread mappings found, starting fresh")
        except Exception as e:
            print(f"[DEBUG] Error loading thread mappings: {e}")
    
    def _save_thread_mappings(self):
        """Save thread mappings to file"""
        try:
            data = {
                'thread_to_conversation': self.thread_to_conversation,
                'active_escalations': self.active_escalations
            }
            with open('.thread_mappings.json', 'w') as f:
                json.dump(data, f)
            print(f"[DEBUG] Saved {len(self.thread_to_conversation)} thread mappings")
        except Exception as e:
            print(f"[DEBUG] Error saving thread mappings: {e}")
        
    def escalate_conversation(self, conversation_id: str, routing_analysis: Dict[str, Any],
                            user_message: str, conversation_history: list, session_summary: dict = None) -> Dict[str, Any]:
        """
        Escalate conversation to Slack channel for underwriter assistance.
        
        Args:
            conversation_id: Unique conversation identifier
            routing_analysis: Analysis from intelligent routing
            user_message: Latest user message
            conversation_history: Full conversation context
            session_summary: Session participants and state (optional)
            
        Returns:
            Escalation result with Slack thread info
        """
        if not self.client or not self.escalation_channel:
            return {
                'success': False,
                'error': 'Slack integration not configured',
                'fallback_message': 'This inquiry requires specialist attention. Please contact our support team directly.'
            }
        
        try:
            # Create escalation summary
            escalation_summary = self._create_escalation_summary(
                conversation_id, routing_analysis, user_message, conversation_history
            )
            if session_summary:
                escalation_summary["session"] = session_summary
            
            # Post to Slack channel
            response = self.client.chat_postMessage(
                channel=self.escalation_channel,
                text="🚨 Customer Conversation Escalation Required",
                blocks=self._create_escalation_blocks(escalation_summary),
                metadata={
                    "event_type": "conversation_escalation",
                    "event_payload": {
                        "conversation_id": conversation_id,
                        "urgency": routing_analysis.get('urgency', {}).get('level', 'medium'),
                        "complexity": routing_analysis.get('complexity', {}).get('level', 'medium')
                    }
                }
            )
            
            if response['ok']:
                thread_ts = response['ts']
                
                # Store escalation info
                escalation_data = {
                    'thread_ts': thread_ts,
                    'channel': self.escalation_channel,
                    'escalated_at': time.time(),
                    'status': 'waiting_for_underwriter',
                    'routing_analysis': routing_analysis,
                    'success': True
                }
                
                self.active_escalations[conversation_id] = escalation_data
                
                # Create bidirectional mapping for Events API
                self.thread_to_conversation[thread_ts] = conversation_id
                
                # Register with conversation coordinator
                from agents.core.conversation_coordinator import conversation_coordinator
                conversation_coordinator.escalate_session(
                    conversation_id=conversation_id,
                    slack_thread_ts=thread_ts,
                    slack_channel=self.escalation_channel,
                    escalation_data=escalation_data
                )
                
                # Persist thread mappings
                self._save_thread_mappings()
                
                # Debug logging
                print(f"[DEBUG] Created escalation for {conversation_id} with thread_ts: {thread_ts}")
                print(f"[DEBUG] Thread mapping: {thread_ts} -> {conversation_id}")
                print(f"[DEBUG] Active escalations count: {len(self.active_escalations)}")
                
                # Post conversation context in thread
                self._post_conversation_context(thread_ts, conversation_history)
                
                return {
                    'success': True,
                    'thread_ts': thread_ts,
                    'channel': self.escalation_channel,
                    'escalation_message': self._get_escalation_response_message(routing_analysis)
                }
            else:
                return {
                    'success': False,
                    'error': f"Slack API error: {response.get('error', 'Unknown error')}",
                    'fallback_message': 'Unable to connect to specialist team. Please try again or contact support directly.'
                }
                
        except SlackApiError as e:
            print(f"Slack API error during escalation: {e}")
            return {
                'success': False,
                'error': str(e),
                'fallback_message': 'Specialist escalation temporarily unavailable. Please contact support directly.'
            }
        except Exception as e:
            print(f"Unexpected error during escalation: {e}")
            return {
                'success': False,
                'error': str(e),
                'fallback_message': 'Technical issue with escalation system. Please contact support directly.'
            }
    
    def post_ai_response_to_thread(self, conversation_id: str, ai_response: str) -> bool:
        """Post AI response to existing Slack thread for context."""
        if conversation_id not in self.active_escalations:
            return False
        
        escalation = self.active_escalations[conversation_id]
        
        try:
            self.client.chat_postMessage(
                channel=escalation['channel'],
                thread_ts=escalation['thread_ts'],
                text="🤖 AI Response:",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*AI Response:*\n{ai_response}"
                        }
                    }
                ]
            )
            return True
        except Exception as e:
            print(f"Error posting AI response to Slack: {e}")
            return False
    
    def post_user_message_to_thread(self, conversation_id: str, user_message: str) -> bool:
        """Post new user message to existing Slack thread."""
        if conversation_id not in self.active_escalations:
            return False
        
        escalation = self.active_escalations[conversation_id]
        
        try:
            self.client.chat_postMessage(
                channel=escalation['channel'],
                thread_ts=escalation['thread_ts'],
                text="👤 Customer Message:",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Customer:*\n{user_message}"
                        }
                    }
                ]
            )
            return True
        except Exception as e:
            print(f"Error posting user message to Slack: {e}")
            return False
    
    def check_underwriter_response(self, conversation_id: str) -> Optional[str]:
        """Check if underwriter has responded in the Slack thread."""
        if conversation_id not in self.active_escalations:
            return None
        
        escalation = self.active_escalations[conversation_id]
        
        try:
            # Get thread messages with rate limiting
            response = self._rate_limited_api_call(
                self.client.conversations_replies,
                channel=escalation['channel'],
                ts=escalation['thread_ts'],
                oldest=str(escalation['escalated_at'])
            )
            
            if response['ok']:
                messages = response['messages']
                
                # Look for underwriter responses (not from bot)
                for message in reversed(messages):  # Check newest first
                    if (message.get('user') and 
                        message.get('user') != self.client.auth_test()['user_id'] and
                        'subtype' not in message):
                        
                        # Found underwriter response
                        underwriter_response = message['text']
                        
                        # Update escalation status
                        self.active_escalations[conversation_id]['status'] = 'underwriter_responded'
                        self.active_escalations[conversation_id]['last_underwriter_response'] = underwriter_response
                        
                        return underwriter_response
            
            return None
            
        except Exception as e:
            print(f"Error checking underwriter response: {e}")
            return None
    
    def close_escalation(self, conversation_id: str, resolution_summary: str = None) -> bool:
        """Close an active escalation."""
        if conversation_id not in self.active_escalations:
            return False
        
        escalation = self.active_escalations[conversation_id]
        
        try:
            # Post closure message to thread
            closure_text = "✅ Conversation Resolved"
            if resolution_summary:
                closure_text += f"\n*Resolution:* {resolution_summary}"
            
            self.client.chat_postMessage(
                channel=escalation['channel'],
                thread_ts=escalation['thread_ts'],
                text=closure_text,
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": closure_text
                        }
                    }
                ]
            )
            
            # Remove from active escalations
            del self.active_escalations[conversation_id]
            return True
            
        except Exception as e:
            print(f"Error closing escalation: {e}")
            return False
    
    def _create_escalation_summary(self, conversation_id: str, routing_analysis: Dict[str, Any],
                                 user_message: str, conversation_history: list) -> Dict[str, Any]:
        """Create escalation summary with key information."""
        complexity = routing_analysis.get('complexity', {})
        urgency = routing_analysis.get('urgency', {})
        topics = routing_analysis.get('topics', {})
        routing = routing_analysis.get('routing', {})
        risk_factors = routing_analysis.get('risk_factors', {})
        
        return {
            'conversation_id': conversation_id,
            'current_message': user_message,
            'message_count': len(conversation_history),
            'complexity_level': complexity.get('level', 'medium'),
            'complexity_reasoning': complexity.get('reasoning', ''),
            'urgency_level': urgency.get('level', 'medium'),
            'primary_topic': topics.get('primary', 'general_inquiry'),
            'specialist_type': routing.get('specialist_type', 'underwriter'),
            'estimated_resolution_time': routing.get('estimated_resolution_time', 'unknown'),
            'risk_factors': risk_factors,
            'escalation_reason': routing.get('reasoning', 'Complex inquiry requiring specialist attention')
        }
    
    def _create_escalation_blocks(self, summary: Dict[str, Any]) -> list:
        """Create Slack blocks for escalation message."""
        urgency_emoji = {
            'low': '🟢',
            'medium': '🟡',
            'high': '🟠',
            'critical': '🔴'
        }
        
        complexity_emoji = {
            'low': '⚪',
            'medium': '🟡',
            'high': '🔴'
        }
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🚨 Customer Conversation Escalation"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Conversation ID:*\n`{summary['conversation_id'][:8]}...`"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Specialist Needed:*\n{summary['specialist_type'].title()}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Urgency:* {urgency_emoji.get(summary['urgency_level'], '⚪')} {summary['urgency_level'].title()}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Complexity:* {complexity_emoji.get(summary['complexity_level'], '⚪')} {summary['complexity_level'].title()}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Topic:* {summary['primary_topic']}\n*Messages:* {summary['message_count']}\n*Est. Resolution:* {summary['estimated_resolution_time']}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Latest Customer Message:*\n> {summary['current_message']}"
                }
            }
        ]
        # Add session participants if available
        session = summary.get("session")
        if session:
            participant_lines = [
                f"{'👤' if p['is_human'] else '🤖'} *{p['role'].title()}*: {p['name']}"
                for p in session.get("participants", [])
            ]
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Session Participants:*\n" + "\n".join(participant_lines)
                }
            })
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Session State:* {session.get('state', 'unknown').replace('_', ' ').title()}"
                    }
                ]
            })
        
        # Add risk factors if any
        risk_factors = summary.get('risk_factors', {})
        active_risks = [k.replace('_', ' ').title() for k, v in risk_factors.items() if v]
        if active_risks:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*⚠️ Risk Factors:* {', '.join(active_risks)}"
                }
            })
        
        # Add reasoning
        if summary.get('escalation_reason'):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Escalation Reason:*\n{summary['escalation_reason']}"
                }
            })
        
        # Add action buttons with proper action_id
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Join Conversation"
                    },
                    "style": "primary",
                    "action_id": "join_conversation",
                    "value": f"join_{summary['conversation_id']}"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Mark Complete"
                    },
                    "style": "primary",
                    "action_id": "resolve_conversation",
                    "value": f"resolve_{summary['conversation_id']}"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "End Conversation"
                    },
                    "style": "danger",
                    "action_id": "end_conversation",
                    "value": f"end_{summary['conversation_id']}"
                }
            ]
        })
        
        return blocks
    
    def _post_conversation_context(self, thread_ts: str, conversation_history: list):
        """Post conversation history to Slack thread for context."""
        if not conversation_history:
            return
        
        # Format recent conversation history
        context_messages = []
        for msg in conversation_history[-6:]:  # Last 6 messages
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            
            if role == 'user':
                context_messages.append(f"👤 *Customer:* {content}")
            elif role == 'assistant':
                context_messages.append(f"🤖 *AI:* {content}")
        
        if context_messages:
            try:
                self.client.chat_postMessage(
                    channel=self.escalation_channel,
                    thread_ts=thread_ts,
                    text="📝 Recent Conversation Context:",
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "📝 *Recent Conversation Context:*\n\n" + "\n\n".join(context_messages)
                            }
                        }
                    ]
                )
            except Exception as e:
                print(f"Error posting conversation context: {e}")
    
    def _get_escalation_response_message(self, routing_analysis: Dict[str, Any]) -> str:
        """Generate appropriate response message for escalated conversation."""
        specialist_type = routing_analysis.get('routing', {}).get('specialist_type', 'specialist')
        urgency = routing_analysis.get('urgency', {}).get('level', 'medium')
        estimated_time = routing_analysis.get('routing', {}).get('estimated_resolution_time', '1-2 hours')
        
        if urgency == 'critical':
            return f"I've immediately escalated your inquiry to our {specialist_type} team due to the urgent nature of your request. They will respond as soon as possible, typically within 15-30 minutes."
        elif urgency == 'high':
            return f"I've prioritized your inquiry with our {specialist_type} team. Given the complexity of your question, they will provide you with detailed assistance within {estimated_time}."
        else:
            return f"I've connected you with our {specialist_type} team who can provide specialized assistance with your inquiry. You can expect a response within {estimated_time}."
    
    def post_message_to_thread(self, thread_ts: str, message: str, channel: str = None) -> bool:
        """Post a message to an existing Slack thread"""
        try:
            if not self.client:
                print("Slack client not available")
                return False
            
            channel = channel or self.escalation_channel
            if not channel:
                print("No Slack channel configured")
                return False
            
            response = self.client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text=message
            )
            
            return response.get('ok', False)
            
        except Exception as e:
            print(f"Error posting message to Slack thread: {e}")
            return False
    
    def get_thread_messages(self, thread_ts: str, channel: str = None) -> List[Dict]:
        """Get messages from a Slack thread"""
        try:
            if not self.client:
                print("Slack client not available")
                return []
            
            channel = channel or self.escalation_channel
            if not channel:
                print("No Slack channel configured")
                return []
            
            response = self._rate_limited_api_call(
                self.client.conversations_replies,
                channel=channel,
                ts=thread_ts,
                limit=100
            )
            
            if not response.get('ok'):
                print(f"Failed to get thread messages: {response.get('error')}")
                return []
            
            messages = []
            for msg in response.get('messages', []):
                # Skip the original escalation message
                if msg.get('ts') == thread_ts:
                    continue
                
                # Get user info for display name
                user_id = msg.get('user')
                sender_name = 'Specialist'
                if user_id:
                    try:
                        user_info = self.client.users_info(user=user_id)
                        if user_info.get('ok'):
                            sender_name = user_info.get('user', {}).get('real_name', 'Specialist')
                    except:
                        pass
                
                messages.append({
                    'text': msg.get('text', ''),
                    'ts': msg.get('ts'),
                    'user': user_id,
                    'sender_name': sender_name,
                    'timestamp': float(msg.get('ts', 0))
                })
            
            return messages
            
        except Exception as e:
            print(f"Error getting thread messages: {e}")
            return []
    
    def get_active_escalations(self) -> Dict[str, Dict]:
        """Get all active escalations for monitoring."""
        return self.active_escalations.copy()
    
    def is_conversation_escalated(self, conversation_id: str) -> bool:
        """Check if a conversation is currently escalated."""
        return conversation_id in self.active_escalations