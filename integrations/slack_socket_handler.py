"""
Slack Socket Mode Handler for Interactive Components
Handles button clicks when Socket Mode is enabled
"""

import os
import asyncio
import logging
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.web import WebClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from integrations.slack_routing import SlackRouter

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SlackSocketHandler:
    def __init__(self):
        self.app_token = os.environ.get("SLACK_APP_TOKEN")
        self.bot_token = os.environ.get("SLACK_BOT_TOKEN")
        
        if not self.app_token or not self.bot_token:
            logger.error("Missing SLACK_APP_TOKEN or SLACK_BOT_TOKEN")
            return
            
        self.web_client = WebClient(token=self.bot_token)
        self.socket_client = SocketModeClient(
            app_token=self.app_token,
            web_client=self.web_client
        )
        
        self.slack_router = SlackRouter()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Set up Socket Mode event handlers"""
        
        @self.socket_client.socket_mode_request_listeners.append
        def handle_socket_mode_request(client: SocketModeClient, req: SocketModeRequest):
            """Handle all Socket Mode requests"""
            logger.info(f"Received Socket Mode request: {req.type}")
            
            if req.type == "interactive":
                # Handle button clicks and interactive components
                self.handle_interactive_component(client, req)
            elif req.type == "events_api":
                # Handle message events from Slack
                self.handle_events_api(client, req)
            else:
                # Acknowledge other types
                response = SocketModeResponse(envelope_id=req.envelope_id)
                client.send_socket_mode_response(response)
    
    def handle_interactive_component(self, client: SocketModeClient, req: SocketModeRequest):
        """Handle interactive component events (button clicks)"""
        try:
            payload = req.payload
            logger.info(f"Interactive component payload: {payload}")
            
            # Acknowledge the request immediately
            response = SocketModeResponse(envelope_id=req.envelope_id)
            client.send_socket_mode_response(response)
            
            # Process the interaction
            if payload.get("type") == "block_actions":
                actions = payload.get("actions", [])
                
                for action in actions:
                    action_id = action.get("action_id", "")
                    action_value = action.get("value", "")
                    
                    logger.info(f"Processing action: {action_id} with value: {action_value}")
                    
                    if action_id == "join_conversation":
                        conversation_id = action_value.replace("join_", "")
                        self.handle_join_conversation(payload, conversation_id)
                    
                    elif action_id == "resolve_conversation":
                        conversation_id = action_value.replace("resolve_", "")
                        self.handle_resolve_conversation(payload, conversation_id)
                    elif action_id == "end_conversation":
                        conversation_id = action_value.replace("end_", "")
                        self.handle_end_conversation(payload, conversation_id)
                        
        except Exception as e:
            logger.error(f"Error handling interactive component: {e}")
            # Still acknowledge to prevent timeout
            response = SocketModeResponse(envelope_id=req.envelope_id)
            client.send_socket_mode_response(response)
    
    def handle_events_api(self, client: SocketModeClient, req: SocketModeRequest):
        """Handle Events API requests (messages, etc.)"""
        try:
            payload = req.payload
            event = payload.get("event", {})
            
            # Log all events for debugging
            logger.info(f"Events API payload type: {payload.get('type')}")
            logger.info(f"Event type: {event.get('type')}, subtype: {event.get('subtype')}, channel: {event.get('channel')}, thread_ts: {event.get('thread_ts')}")
            
            # Acknowledge the request immediately
            response = SocketModeResponse(envelope_id=req.envelope_id)
            client.send_socket_mode_response(response)
            
            # Process message events - including thread replies
            if event.get("type") == "message" and not event.get("bot_id"):
                logger.info(f"Processing human message event: {event}")
                self.handle_message_event(event)
                
        except Exception as e:
            logger.error(f"Error handling events API: {e}")
            # Still acknowledge to prevent timeout
            response = SocketModeResponse(envelope_id=req.envelope_id)
            client.send_socket_mode_response(response)
    
    def handle_message_event(self, event):
        """Handle incoming message events from Slack"""
        try:
            # Skip bot messages to avoid loops
            if event.get("bot_id") or event.get("subtype") == "bot_message":
                return
                
            # Only process messages in threads (replies to escalations)
            thread_ts = event.get("thread_ts")
            if not thread_ts:
                return
                
            channel_id = event.get("channel")
            message_text = event.get("text", "")
            user_id = event.get("user")
            timestamp = event.get("ts")
            
            logger.info(f"Processing thread message from {user_id} in {channel_id}: {message_text[:100]}")
            
            # Find the conversation associated with this thread
            conversation_id = self.find_conversation_by_thread(thread_ts)
            if not conversation_id:
                logger.warning(f"No conversation found for thread {thread_ts}")
                # Debug: Log all active escalations and thread mappings
                logger.info(f"Active escalations: {list(self.slack_router.active_escalations.keys())}")
                for conv_id, esc in self.slack_router.active_escalations.items():
                    logger.info(f"  {conv_id}: thread_ts={esc.get('thread_ts')}")
                
                if hasattr(self.slack_router, 'thread_to_conversation'):
                    logger.info(f"Thread mappings: {self.slack_router.thread_to_conversation}")
                else:
                    logger.warning("No thread_to_conversation mapping found!")
                return
            
            # Get user info
            try:
                user_info = self.web_client.users_info(user=user_id)
                user_name = user_info["user"]["real_name"] or user_info["user"]["name"]
            except:
                user_name = "Underwriter"
            
            # Mark specialist as active when they send a message
            from agents.core.conversation_coordinator import conversation_coordinator
            conversation_coordinator.mark_specialist_joined(conversation_id, user_id)
            
            # Queue the message using conversation coordinator
            conversation_coordinator.queue_slack_message(
                thread_ts=thread_ts,
                message=message_text,
                sender_name=user_name,
                timestamp=float(timestamp)
            )
            
        except Exception as e:
            logger.error(f"Error handling message event: {e}")
    
    def find_conversation_by_thread(self, thread_ts):
        """Find conversation ID by thread timestamp using coordinator"""
        from agents.core.conversation_coordinator import conversation_coordinator
        
        # Use coordinator to find session by thread
        session = conversation_coordinator.get_session_by_thread(thread_ts)
        if session:
            logger.info(f"[COORDINATOR] Found session {session.conversation_id} for thread {thread_ts}")
            return session.conversation_id
        
        # Fallback to old method for backwards compatibility
        if hasattr(self.slack_router, 'thread_to_conversation'):
            if thread_ts in self.slack_router.thread_to_conversation:
                return self.slack_router.thread_to_conversation[thread_ts]
        
        return None
    
    def queue_underwriter_message(self, conversation_id, message, user_name, timestamp):
        """Queue underwriter message for delivery to chatbot"""
        if not hasattr(self.slack_router, 'pending_responses'):
            self.slack_router.pending_responses = {}
        
        if conversation_id not in self.slack_router.pending_responses:
            self.slack_router.pending_responses[conversation_id] = []
        
        self.slack_router.pending_responses[conversation_id].append({
            'message': message,
            'underwriter_name': user_name,
            'timestamp': float(timestamp),
            'delivered': False,
            'type': 'underwriter_response'
        })
        
        logger.info(f"Queued message from {user_name} for conversation {conversation_id}")
        
        # Update escalation status
        if conversation_id in self.slack_router.active_escalations:
            self.slack_router.active_escalations[conversation_id]['last_underwriter_response'] = message
            self.slack_router.active_escalations[conversation_id]['last_underwriter_name'] = user_name
            self.slack_router.active_escalations[conversation_id]['status'] = 'underwriter_responded'
            self.slack_router.active_escalations[conversation_id]['response_timestamp'] = float(timestamp)
    
    def handle_join_conversation(self, payload, conversation_id):
        """Handle underwriter joining a conversation"""
        from agents.core.conversation_coordinator import conversation_coordinator
        import time
        
        user = payload.get("user", {})
        user_id = user.get("id")
        user_name = user.get("name", "Underwriter")
        
        logger.info(f"{user_name} joining conversation {conversation_id}")
        
        # Mark specialist as joined in conversation coordinator
        conversation_coordinator.mark_specialist_joined(conversation_id, user_id)
        
        # Update conversation coordinator
        session = conversation_coordinator.get_session_by_id(conversation_id)
        if session and session.slack_thread_ts:
            # Update escalation data
            if not hasattr(session, 'escalation_data') or not session.escalation_data:
                session.escalation_data = {}
            session.escalation_data['status'] = 'underwriter_joined'
            session.escalation_data['underwriter_name'] = user_name
            session.escalation_data['underwriter_id'] = user_id
            
            # Save updated session state
            conversation_coordinator._save_sessions()
            
            # Queue a join notification message for the chatbot
            success = conversation_coordinator.queue_slack_message(
                thread_ts=session.slack_thread_ts,
                message=f"{user_name} joined the conversation and will assist with this case",
                sender_name="System",
                timestamp=time.time()
            )
            logger.info(f"Queued join notification for {conversation_id}: {success}")
            
            # Update session activity
            conversation_coordinator.update_session_activity(
                conversation_id,
                ai_response=f"Specialist {user_name} joined the conversation"
            )
        
        # Update escalation status
        if conversation_id in self.slack_router.active_escalations:
            self.slack_router.active_escalations[conversation_id]['status'] = 'underwriter_joined'
            self.slack_router.active_escalations[conversation_id]['underwriter_id'] = user_id
            self.slack_router.active_escalations[conversation_id]['underwriter_name'] = user_name
            
            # Post confirmation message in thread
            try:
                escalation = self.slack_router.active_escalations[conversation_id]
                self.web_client.chat_postMessage(
                    channel=escalation['channel'],
                    thread_ts=escalation['thread_ts'],
                    text=f"👤 {user_name} has joined the conversation and will assist with this case.\n\n💬 You can now reply in this thread to communicate directly with the customer. When you're finished, use the buttons below to either provide a summary or end the conversation."
                )
                logger.info(f"Posted join confirmation for {user_name}")
            except Exception as e:
                logger.error(f"Error posting join confirmation: {e}")
        
        # Update the original message with end conversation option
        try:
            updated_blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"✅ *{user_name}* is now handling this conversation"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "action_id": "resolve_conversation",
                            "text": {
                                "type": "plain_text",
                                "text": "Mark Complete",
                                "emoji": True
                            },
                            "style": "primary",
                            "value": f"resolve_{conversation_id}"
                        },
                        {
                            "type": "button",
                            "action_id": "end_conversation",
                            "text": {
                                "type": "plain_text",
                                "text": "End Conversation",
                                "emoji": True
                            },
                            "style": "danger",
                            "value": f"end_{conversation_id}"
                        }
                    ]
                }
            ]
            
            # Keep original blocks except the last action block
            original_blocks = payload.get("message", {}).get("blocks", [])
            if original_blocks:
                updated_blocks = original_blocks[:-1] + updated_blocks
            
            self.web_client.chat_update(
                channel=payload["channel"]["id"],
                ts=payload["message"]["ts"],
                text="🚨 Customer Conversation Escalation - In Progress",
                blocks=updated_blocks
            )
            logger.info("Updated escalation message")
            
        except Exception as e:
            logger.error(f"Error updating escalation message: {e}")
    
    def handle_end_conversation(self, payload, conversation_id):
        """Handle ending a conversation completely without summary injection"""
        from agents.core.conversation_coordinator import conversation_coordinator
        import time
        
        user = payload.get("user", {})
        user_name = user.get("name", "Underwriter")
        
        logger.info(f"{user_name} ending conversation {conversation_id}")
        
        # Get specialist conversation history before ending
        specialist_history = self.get_specialist_conversation_summary(conversation_id)
        
        # Update conversation coordinator - mark as ended
        session = conversation_coordinator.get_session_by_id(conversation_id)
        if session and session.slack_thread_ts:
            # Create end message with conversation context
            end_message = f"This conversation has been ended by {user_name}."
            if specialist_history:
                end_message += f"\n\n**Specialist Consultation Summary:**\n{specialist_history}"
            end_message += "\n\nIf you need further assistance, please start a new conversation."
            
            # Queue an end notification message for the chatbot with conversation history
            conversation_coordinator.queue_slack_message(
                thread_ts=session.slack_thread_ts,
                message=end_message,
                sender_name="System",
                timestamp=time.time()
            )
            
            # Signal to close side panel
            conversation_coordinator.queue_slack_message(
                thread_ts=session.slack_thread_ts,
                message="CLOSE_SIDE_PANEL",
                sender_name="System_Control",
                timestamp=time.time()
            )
            
            # Mark specialist as left and session as ended in coordinator
            conversation_coordinator.mark_specialist_left(conversation_id, user.get("id"))
            conversation_coordinator.resolve_session(
                conversation_id, 
                resolution_reason=f"ended by {user_name}"
            )
        
        # Update escalation status
        if conversation_id in self.slack_router.active_escalations:
            self.slack_router.active_escalations[conversation_id]['status'] = 'ended'
            self.slack_router.active_escalations[conversation_id]['ended_by'] = user_name
            self.slack_router.active_escalations[conversation_id]['ended_at'] = time.time()
        
        # Update the Slack message to show conversation was ended
        try:
            updated_blocks = [{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"❌ *{user_name}* ended this conversation"
                }
            }]
            
            # Keep original blocks except the last action block
            original_blocks = payload.get("message", {}).get("blocks", [])
            if original_blocks:
                updated_blocks = original_blocks[:-1] + updated_blocks
            
            self.web_client.chat_update(
                channel=payload["channel"]["id"],
                ts=payload["message"]["ts"],
                text="🚨 Customer Conversation - Ended",
                blocks=updated_blocks
            )
            logger.info("Updated escalation message to show ended status")
            
        except Exception as e:
            logger.error(f"Error updating escalation message: {e}")
    
    def get_specialist_conversation_summary(self, conversation_id):
        """Get summary of specialist conversation from Slack thread"""
        try:
            # Get conversation info from coordinator
            from agents.core.conversation_coordinator import conversation_coordinator
            session = conversation_coordinator.get_session_by_id(conversation_id)
            if not session or not session.slack_thread_ts:
                return None
            
            # Get escalation info
            if conversation_id not in self.slack_router.active_escalations:
                return None
                
            escalation = self.slack_router.active_escalations[conversation_id]
            channel = escalation.get('channel')
            thread_ts = escalation.get('thread_ts')
            
            if not channel or not thread_ts:
                return None
            
            # Get thread messages with rate limiting
            import time
            for attempt in range(3):
                try:
                    response = self.web_client.conversations_replies(
                        channel=channel,
                        ts=thread_ts,
                        limit=50
                    )
                    break
                except Exception as e:
                    if "ratelimited" in str(e).lower() and attempt < 2:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    logger.error(f"Error getting thread messages for summary: {e}")
                    return None
            
            if not response.get("ok"):
                return None
            
            # Extract specialist messages
            messages = response.get("messages", [])
            specialist_messages = []
            
            for msg in messages[1:]:  # Skip the initial escalation message
                user_id = msg.get("user")
                text = msg.get("text", "")
                
                # Skip bot messages and system messages
                if not user_id or msg.get("bot_id") or not text.strip():
                    continue
                    
                # Get user info
                try:
                    user_info = self.web_client.users_info(user=user_id)
                    if user_info.get("ok"):
                        user_name = user_info["user"].get("real_name") or user_info["user"].get("name", "Specialist")
                    else:
                        user_name = "Specialist"
                except:
                    user_name = "Specialist"
                
                specialist_messages.append(f"{user_name}: {text}")
            
            if specialist_messages:
                return "\n".join(specialist_messages)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting specialist conversation summary: {e}")
            return None

    def handle_resolve_conversation(self, payload, conversation_id):
        """Handle marking a conversation as resolved and inject summary back to main chat"""
        from agents.core.conversation_coordinator import conversation_coordinator
        import time
        import requests
        
        user = payload.get("user", {})
        user_name = user.get("name", "Underwriter")
        
        logger.info(f"{user_name} resolving conversation {conversation_id}")
        
        # Get specialist conversation history before resolving
        specialist_history = self.get_specialist_conversation_summary(conversation_id)
        
        # Generate conversation summary and inject back into main chat
        try:
            # Get conversation summary from our endpoint
            summary_response = requests.get(f"http://localhost:8000/escalation-summary/{conversation_id}")
            
            if summary_response.status_code == 200:
                summary_data = summary_response.json()
                summary_text = summary_data.get('summary')
                
                if summary_text:
                    # Use the new injection method
                    conversation_coordinator.inject_summary_to_main_chat(conversation_id, summary_text)
                    logger.info(f"Injected summary back to main chat for {conversation_id}")
                
        except Exception as e:
            logger.error(f"Error generating summary for {conversation_id}: {e}")
        
        # Update conversation coordinator
        session = conversation_coordinator.get_session_by_id(conversation_id)
        if session and session.slack_thread_ts:
            # Create resolution message with conversation context
            resolution_message = f"Conversation has been resolved by {user_name}."
            if specialist_history:
                resolution_message += f"\n\n**Specialist Consultation Summary:**\n{specialist_history}"
            resolution_message += "\n\nThe AI will continue to assist you."
            
            # Queue a resolution notification message for the chatbot with conversation history
            conversation_coordinator.queue_slack_message(
                thread_ts=session.slack_thread_ts,
                message=resolution_message,
                sender_name="System",
                timestamp=time.time()
            )
            
            # Signal to close side panel
            conversation_coordinator.queue_slack_message(
                thread_ts=session.slack_thread_ts,
                message="CLOSE_SIDE_PANEL",
                sender_name="System_Control",
                timestamp=time.time()
            )
            
            # Mark specialist as left and session as resolved in coordinator
            conversation_coordinator.mark_specialist_left(conversation_id, user.get("id"))
            conversation_coordinator.resolve_session(
                conversation_id, 
                resolution_reason=f"resolved by {user_name}"
            )
        
        # Update escalation status
        if conversation_id in self.slack_router.active_escalations:
            self.slack_router.active_escalations[conversation_id]['status'] = 'resolved'
            self.slack_router.active_escalations[conversation_id]['resolved_by'] = user_name
            
            # Post resolution message
            try:
                escalation = self.slack_router.active_escalations[conversation_id]
                self.web_client.chat_postMessage(
                    channel=escalation['channel'],
                    thread_ts=escalation['thread_ts'],
                    text=f"✅ Conversation marked as resolved by {user_name}"
                )
            except Exception as e:
                logger.error(f"Error posting resolution message: {e}")
        
        # Update the original message
        try:
            updated_blocks = [{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"✅ *Resolved* by {user_name}"
                }
            }]
            
            self.web_client.chat_update(
                channel=payload["channel"]["id"],
                ts=payload["message"]["ts"],
                text="🚨 Customer Conversation Escalation - Resolved",
                blocks=updated_blocks
            )
            logger.info("Updated escalation message to resolved")
            
        except Exception as e:
            logger.error(f"Error updating resolved message: {e}")
    
    def start(self):
        """Start the Socket Mode client"""
        if not self.app_token or not self.bot_token:
            logger.error("Cannot start Socket Mode client: missing tokens")
            return
            
        logger.info("Starting Slack Socket Mode client...")
        self.socket_client.connect()
    
    def stop(self):
        """Stop the Socket Mode client"""
        if hasattr(self, 'socket_client'):
            self.socket_client.disconnect()

# Global instance
socket_handler = None

def get_socket_handler():
    """Get or create the global socket handler"""
    global socket_handler
    if socket_handler is None:
        socket_handler = SlackSocketHandler()
    return socket_handler

def start_socket_mode():
    """Start Socket Mode handling"""
    handler = get_socket_handler()
    handler.start()

def stop_socket_mode():
    """Stop Socket Mode handling"""
    handler = get_socket_handler()
    handler.stop()