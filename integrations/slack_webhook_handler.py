# slack_webhook_handler.py
from flask import Blueprint, request, jsonify
import json
import hmac
import hashlib
import os
import time
from integrations.slack_routing import SlackRouter

slack_bp = Blueprint('slack', __name__)

# Initialize Slack router
slack_router = SlackRouter()

def verify_slack_signature(request_body, timestamp, signature):
    """Verify that the request came from Slack."""
    slack_signing_secret = os.environ.get('SLACK_SIGNING_SECRET', '')
    if not slack_signing_secret:
        return True  # Skip verification if no secret is set
    
    # Create the signature base string
    sig_basestring = f"v0:{timestamp}:{request_body}"
    
    # Create the expected signature
    expected_signature = 'v0=' + hmac.new(
        slack_signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)

@slack_bp.route('/slack/events', methods=['POST'])
def handle_slack_events():
    """Handle Slack events and interactive messages."""
    print(f"[SLACK_WEBHOOK] Received Slack event")
    
    # Get headers
    timestamp = request.headers.get('X-Slack-Request-Timestamp', '')
    signature = request.headers.get('X-Slack-Signature', '')
    
    # Get request body
    request_body = request.get_data(as_text=True)
    print(f"[SLACK_WEBHOOK] Request body: {request_body[:200]}...")
    
    # Verify signature
    if not verify_slack_signature(request_body, timestamp, signature):
        print(f"[SLACK_WEBHOOK] Invalid signature")
        return jsonify({'error': 'Invalid signature'}), 401
    
    try:
        # Check if it's form-encoded payload (button clicks)
        if request_body.startswith('payload='):
            # Extract and decode the payload
            import urllib.parse
            payload_data = urllib.parse.parse_qs(request_body)['payload'][0]
            payload = json.loads(payload_data)
            print(f"[SLACK_WEBHOOK] Interactive component payload: {payload}")
            return handle_interactive_component(payload)
        
        # Otherwise treat as JSON
        data = json.loads(request_body)
        print(f"[SLACK_WEBHOOK] JSON data: {data}")
        
        # Handle URL verification challenge
        if data.get('type') == 'url_verification':
            print(f"[SLACK_WEBHOOK] URL verification challenge")
            return jsonify({'challenge': data.get('challenge')})
        
        # Handle regular events
        if data.get('type') == 'event_callback':
            event = data.get('event', {})
            return handle_slack_event(event)
        
        return jsonify({'status': 'ok'})
        
    except json.JSONDecodeError as e:
        print(f"[SLACK_WEBHOOK] JSON decode error: {e}")
        return jsonify({'error': 'Invalid JSON'}), 400
    except Exception as e:
        print(f"[SLACK_WEBHOOK] Error handling Slack event: {e}")
        return jsonify({'error': 'Internal error'}), 500

def handle_interactive_component(payload):
    """Handle button clicks and other interactive components."""
    try:
        print(f"[SLACK_WEBHOOK] Processing interactive component: {payload.get('type')}")
        actions = payload.get('actions', [])
        
        for action in actions:
            action_id = action.get('action_id', '')
            action_value = action.get('value', '')
            
            print(f"[SLACK_WEBHOOK] Action ID: {action_id}, Value: {action_value}")
            
            # Handle by action_id (proper Slack pattern)
            if action_id == 'join_conversation':
                conversation_id = action_value.replace('join_', '')
                print(f"[SLACK_WEBHOOK] Handling join_conversation for {conversation_id}")
                return handle_join_conversation(payload, conversation_id)
            
            elif action_id == 'resolve_conversation':
                conversation_id = action_value.replace('resolve_', '')
                print(f"[SLACK_WEBHOOK] Handling resolve_conversation for {conversation_id}")
                return handle_resolve_conversation(payload, conversation_id)
            
            # Fallback: Handle by value prefix (legacy support)
            elif action_value.startswith('join_'):
                conversation_id = action_value.replace('join_', '')
                print(f"[SLACK_WEBHOOK] Fallback handling join for {conversation_id}")
                return handle_join_conversation(payload, conversation_id)
            
            elif action_value.startswith('resolve_'):
                conversation_id = action_value.replace('resolve_', '')
                print(f"[SLACK_WEBHOOK] Fallback handling resolve for {conversation_id}")
                return handle_resolve_conversation(payload, conversation_id)
        
        print(f"[SLACK_WEBHOOK] No matching action found")
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        print(f"[SLACK_WEBHOOK] Error handling interactive component: {e}")
        return jsonify({'status': 'error', 'error': str(e)})

def handle_join_conversation(payload, conversation_id):
    """Handle underwriter joining a conversation."""
    user_id = payload.get('user', {}).get('id')
    user_name = payload.get('user', {}).get('name', 'Underwriter')
    
    print(f"[SLACK_WEBHOOK] {user_name} joining conversation {conversation_id}")
    
    # Acknowledge the interaction immediately (equivalent to ack() in Bolt)
    response_data = {'status': 'ok'}
    
    # Update the escalation status
    if conversation_id in slack_router.active_escalations:
        slack_router.active_escalations[conversation_id]['status'] = 'underwriter_joined'
        slack_router.active_escalations[conversation_id]['underwriter_id'] = user_id
        slack_router.active_escalations[conversation_id]['underwriter_name'] = user_name
        
        # Post confirmation message in thread
        try:
            escalation = slack_router.active_escalations[conversation_id]
            if slack_router.client:
                slack_router.client.chat_postMessage(
                    channel=escalation['channel'],
                    thread_ts=escalation['thread_ts'],
                    text=f"👤 {user_name} has joined the conversation and will assist with this case."
                )
                print(f"[SLACK_WEBHOOK] Posted join confirmation for {user_name}")
        except Exception as e:
            print(f"[SLACK_WEBHOOK] Error posting join confirmation: {e}")
    else:
        print(f"[SLACK_WEBHOOK] No active escalation found for {conversation_id}")
    
    # Update the original message to show someone joined
    try:
        # Create updated blocks with join confirmation
        updated_blocks = [{
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"✅ *{user_name}* is now handling this conversation"
            }
        }]
        
        # Try to get original blocks if available
        original_blocks = payload.get('message', {}).get('blocks', [])
        if original_blocks:
            # Keep original blocks except the last action block, add confirmation
            updated_blocks = original_blocks[:-1] + updated_blocks
        
        if slack_router.client:
            result = slack_router.client.chat_update(
                channel=payload['channel']['id'],
                ts=payload['message']['ts'],
                text="🚨 Customer Conversation Escalation - In Progress",
                blocks=updated_blocks
            )
            print(f"[SLACK_WEBHOOK] Updated escalation message: {result.get('ok', False)}")
            
    except Exception as e:
        print(f"[SLACK_WEBHOOK] Error updating escalation message: {e}")
    
    return jsonify(response_data)

def handle_resolve_conversation(payload, conversation_id):
    """Handle marking a conversation as resolved."""
    user_name = payload.get('user', {}).get('name', 'Underwriter')
    
    # Close the escalation
    slack_router.close_escalation(conversation_id, f"Resolved by {user_name}")
    
    # Update the original message
    try:
        slack_router.client.chat_update(
            channel=payload['channel']['id'],
            ts=payload['message']['ts'],
            text="✅ Customer Conversation Escalation - Resolved",
            blocks=[{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"✅ This conversation has been resolved by *{user_name}*"
                }
            }]
        )
    except Exception as e:
        print(f"Error updating resolved message: {e}")
    
    return jsonify({'status': 'ok'})

def handle_slack_event(event):
    """Handle regular Slack events like messages."""
    event_type = event.get('type')
    
    if event_type == 'message':
        return handle_message_event(event)
    
    return jsonify({'status': 'ok'})

def handle_message_event(event):
    """Handle message events in escalation threads."""
    print(f"DEBUG: Processing Slack message event: {event}")
    
    # Only process messages in threads (replies to escalations)
    thread_ts = event.get('thread_ts')
    if not thread_ts:
        print(f"DEBUG: No thread_ts found, skipping non-threaded message")
        return jsonify({'status': 'ok'})
    
    # Skip bot messages
    if event.get('subtype') == 'bot_message' or 'bot_id' in event:
        print(f"DEBUG: Skipping bot message")
        return jsonify({'status': 'ok'})
    
    print(f"DEBUG: Looking for thread_ts {thread_ts} in active escalations")
    print(f"DEBUG: Active escalations: {list(slack_router.active_escalations.keys())}")
    
    # Find which conversation this thread belongs to
    conversation_id = None
    for conv_id, escalation in slack_router.active_escalations.items():
        escalation_thread = escalation.get('thread_ts')
        print(f"DEBUG: Checking conversation {conv_id} with thread_ts {escalation_thread}")
        if escalation_thread == thread_ts:
            conversation_id = conv_id
            break
    
    if not conversation_id:
        print(f"DEBUG: No matching conversation found for thread_ts {thread_ts}")
        return jsonify({'status': 'ok'})
    
    print(f"DEBUG: Found matching conversation: {conversation_id}")
    
    # Store the underwriter response
    message_text = event.get('text', '')
    user_id = event.get('user')
    
    # Get underwriter name
    try:
        if slack_router.client:
            user_info = slack_router.client.users_info(user=user_id)
            underwriter_name = user_info['user']['real_name'] or user_info['user']['name']
        else:
            underwriter_name = "Insurance Specialist"
    except Exception as e:
        print(f"DEBUG: Error getting user info: {e}")
        underwriter_name = "Insurance Specialist"
    
    # Update the escalation with the response
    escalation = slack_router.active_escalations[conversation_id]
    escalation['last_underwriter_response'] = message_text
    escalation['last_underwriter_id'] = user_id
    escalation['underwriter_name'] = underwriter_name
    escalation['status'] = 'underwriter_responded'
    escalation['response_timestamp'] = time.time()
    
    # Store in conversation messages for real-time delivery
    if conversation_id not in slack_router.pending_responses:
        slack_router.pending_responses[conversation_id] = []
        
    slack_router.pending_responses[conversation_id].append({
        'message': message_text,
        'underwriter_name': underwriter_name,
        'timestamp': time.time(),
        'delivered': False
    })
    
    print(f"SUCCESS: Underwriter response queued for conversation {conversation_id}")
    print(f"DEBUG: Message: {message_text}")
    print(f"DEBUG: From: {underwriter_name}")
    
    return jsonify({'status': 'ok'})

@slack_bp.route('/slack/status', methods=['GET'])
def slack_status():
    """Get status of Slack integration and active escalations."""
    return jsonify({
        'slack_connected': slack_router.client is not None,
        'escalation_channel': slack_router.escalation_channel,
        'active_escalations': len(slack_router.active_escalations),
        'escalation_details': {
            conv_id: {
                'status': esc.get('status'),
                'escalated_at': esc.get('escalated_at'),
                'underwriter_name': esc.get('underwriter_name')
            }
            for conv_id, esc in slack_router.active_escalations.items()
        }
    })

@slack_bp.route('/slack/test-button', methods=['POST'])
def test_button_interaction():
    """Test Slack button interaction locally."""
    data = request.get_json()
    conversation_id = data.get('conversation_id', 'test_conversation_123')
    action = data.get('action', 'join')  # join or resolve
    
    # Simulate button click payload
    simulated_payload = {
        'type': 'interactive_message',
        'user': {
            'id': 'U12345',
            'name': 'Test User'
        },
        'channel': {
            'id': 'C12345'
        },
        'message': {
            'ts': '1234567890.123456'
        },
        'actions': [{
            'name': 'button',
            'type': 'button',
            'value': f"{action}_{conversation_id}"
        }]
    }
    
    print(f"[SLACK_TEST] Testing button interaction: {action} for {conversation_id}")
    
    try:
        result = handle_interactive_component(simulated_payload)
        return jsonify({
            'status': 'success',
            'test_result': 'Button interaction processed',
            'conversation_id': conversation_id,
            'action': action
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'conversation_id': conversation_id
        })