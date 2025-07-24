# app.py - Simplified Insurance Chatbot Application
from flask import Flask, render_template, request, jsonify, session, redirect
import uuid
import os
import sys
# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import asyncio
from dotenv import load_dotenv
from src.models import db, User, Conversation, Message

# Load environment variables
load_dotenv()

# Core imports
from agents.core.agents_insurance_chatbot import process_insurance_query, get_agent_status
from agents.monitoring.parallel_monitoring_agent import monitor_conversation, check_escalation_signals, get_conversation_monitoring_status
from agents.monitoring.abuse_prevention_agent import get_abuse_prevention_agent

from agents.analysis.background_agent import get_company_agent
from integrations.slack_routing import SlackRouter
from integrations.slack_webhook_handler import slack_bp
from agents.core.conversation_coordinator import conversation_coordinator
from src.logger import log_chat, log_error, log_system, chat_logger

import re
from flask_socketio import SocketIO, emit, join_room, leave_room
import threading
import atexit
import json
from openai import OpenAI

app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'),
            static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'))
app.secret_key = os.environ.get("SESSION_SECRET", os.urandom(24))

# Session configuration for persistence
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours

# Database configuration
database_url = os.environ.get("DATABASE_URL")
if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    # Create tables
    with app.app_context():
        db.create_all()

# Initialize SocketIO for real-time updates
socketio = SocketIO(app, cors_allowed_origins="*")

# Register blueprints
app.register_blueprint(slack_bp)

# Initialize chatbot components
# OpenAI Vector Store removed - system uses direct file_search API instead
slack_router = SlackRouter()

# Initialize Socket Mode handler for Slack buttons
socket_handler = None
socket_thread = None

# Initialize OpenAI client for escalation analysis
openai_client = OpenAI(api_key=os.getenv("POC_OPENAI_API"))

def start_socket_mode():
    """Initialize and start Socket Mode handler in background thread"""
    global socket_handler, socket_thread
    
    try:
        from integrations.slack_socket_handler import SlackSocketHandler
        
        if os.environ.get("SLACK_APP_TOKEN") and os.environ.get("SLACK_BOT_TOKEN"):
            socket_handler = SlackSocketHandler()
            
            def run_socket_mode():
                try:
                    socket_handler.start()
                except Exception as e:
                    print(f"Socket Mode error: {e}")
            
            socket_thread = threading.Thread(target=run_socket_mode, daemon=True)
            socket_thread.start()
            print("Socket Mode handler started for Slack button interactions")
        else:
            print("Slack tokens not configured, skipping Socket Mode")
    except ImportError:
        print("Slack Socket Mode handler not available")
    except Exception as e:
        print(f"Error starting Socket Mode: {e}")

def stop_socket_mode():
    """Stop Socket Mode handler"""
    global socket_handler
    if socket_handler:
        try:
            socket_handler.close()
        except Exception as e:
            print(f"Error stopping Socket Mode: {e}")

# Start Socket Mode on application startup
start_socket_mode()

# Register cleanup function
atexit.register(stop_socket_mode)

def extract_company_name(user_message):
    """Extract company name from user message using heuristics."""
    # Simple heuristic-based extraction
    keywords = ['company', 'business', 'named', 'for', 'about', 'corporation', 'corp']
    words = user_message.split()
    
    for i, word in enumerate(words):
        if word.lower() in keywords and i + 1 < len(words):
            # Look for capitalized words after keywords
            for j in range(i + 1, min(i + 4, len(words))):
                if words[j][0].isupper() and len(words[j]) > 2:
                    return words[j]
    
    return None

def should_use_vector_store(user_message):
    """Intelligent detection for insurance queries requiring vector store knowledge retrieval."""
    insurance_keywords = [
        'policy', 'coverage', 'premium', 'deductible', 'claim', 'underwriting',
        'liability', 'property', 'workers comp', 'cyber', 'insurance', 'quote',
        'application', 'bind', 'renew', 'cancel', 'exclusion', 'limit'
    ]
    
    return any(keyword in user_message.lower() for keyword in insurance_keywords)

def format_risk_report_html(report_text):
    """Convert plain text risk report to enhanced HTML format"""
    import re
    
    # Split report into sections
    sections = report_text.split('\n\n')
    html_parts = []
    
    current_section = None
    coverage_items = []
    
    for section in sections:
        section = section.strip()
        if not section:
            continue
            
        # Executive Summary
        if 'EXECUTIVE SUMMARY' in section:
            current_section = 'executive'
            html_parts.append('<div class="executive-summary">')
            html_parts.append('<h2>Executive Summary</h2>')
        elif 'RISK MANAGER\'S ANALYSIS' in section:
            current_section = 'risk'
            if coverage_items:
                html_parts.append('</div>')  # Close previous section
            html_parts.append('<div class="risk-analysis">')
            html_parts.append('<h2>Risk Manager\'s Analysis</h2>')
        elif 'COVERAGE RECOMMENDATIONS' in section:
            current_section = 'coverage'
            if html_parts and html_parts[-1] != '</div>':
                html_parts.append('</div>')  # Close previous section
            html_parts.append('<h2 style="margin-top: 2rem;">Coverage Recommendations</h2>')
            html_parts.append('<div class="coverage-grid">')
        elif 'ORIGINAL CLASSIFICATION API RESPONSE' in section:
            if coverage_items:
                html_parts.append('</div>')  # Close coverage grid
            if html_parts and html_parts[-1] != '</div>':
                html_parts.append('</div>')  # Close any open section
            html_parts.append('<div class="api-response-section">')
            html_parts.append('<h3>Original Classification Data</h3>')
            current_section = 'api'
        else:
            # Process content based on current section
            if current_section == 'coverage' and section.startswith('•'):
                # Start of a new coverage item
                if coverage_items:
                    # Process previous coverage item
                    html_parts.append(format_coverage_card(coverage_items))
                    coverage_items = []
                coverage_items.append(section)
            elif current_section == 'coverage' and coverage_items:
                # Continue current coverage item
                coverage_items.append(section)
            elif current_section == 'api':
                # Format API response
                html_parts.append(f'<pre>{section}</pre>')
            else:
                # Regular paragraph
                formatted = section.replace('**', '<strong>').replace('**', '</strong>')
                formatted = re.sub(r'\$([0-9,]+)', r'<span class="limit-amount">$\1</span>', formatted)
                
                # Handle bullet points
                if section.startswith('•'):
                    if not html_parts or '<ul class="coverage-points">' not in html_parts[-1]:
                        html_parts.append('<ul class="coverage-points">')
                    html_parts.append(f'<li>{formatted[1:].strip()}</li>')
                elif html_parts and '<ul class="coverage-points">' in html_parts[-1]:
                    html_parts.append('</ul>')
                    html_parts.append(f'<p>{formatted}</p>')
                else:
                    html_parts.append(f'<p>{formatted}</p>')
    
    # Process any remaining coverage items
    if coverage_items:
        html_parts.append(format_coverage_card(coverage_items))
    
    # Close any open divs
    if current_section:
        html_parts.append('</div>')
    
    return '\n'.join(html_parts)

def format_coverage_card(items):
    """Format a coverage recommendation as a card"""
    if not items:
        return ''
    
    # Extract title (first bullet point)
    title_match = re.search(r'• (.+?):', items[0])
    title = title_match.group(1) if title_match else 'Coverage'
    
    card_html = f'<div class="coverage-card">\n<h3>{title}</h3>\n'
    
    # Process content
    for item in items:
        if 'Recommended Limit:' in item:
            match = re.search(r'Recommended Limit: (.+)', item)
            if match:
                card_html += f'<div class="limit-box"><span class="limit-label">Recommended Limit:</span><span class="limit-amount">{match.group(1)}</span></div>\n'
        elif 'Claim Example:' in item:
            card_html += '<div class="claim-example">\n'
            card_html += f'<strong>Real Claim Example:</strong>\n'
            card_html += f'{item.replace("Claim Example:", "").strip()}\n'
            card_html += '</div>\n'
        elif item.startswith('•'):
            # Skip the title line
            if items.index(item) > 0:
                card_html += f'<p>{item[1:].strip()}</p>\n'
        else:
            card_html += f'<p>{item}</p>\n'
    
    card_html += '</div>\n'
    return card_html

def check_should_prompt_registration():
    """Check if user should be prompted to register based on interaction criteria"""
    if session.get('user_registered', False):
        return False
    
    message_count = session.get('message_count', 0)
    
    # Progressive registration triggers
    triggers = {
        'after_messages': message_count >= 3,  # After 3 messages
        'quote_requested': session.get('quote_requested', False),  # When asking for quotes
        'risk_assessment_requested': session.get('risk_assessment_requested', False),  # When asking for risk assessment
        'application_started': session.get('application_started', False),  # When starting an application
        'advanced_feature': session.get('advanced_feature_requested', False)  # When using advanced features
    }
    
    # Return trigger info and whether to prompt
    should_prompt = any(triggers.values())
    
    return {
        'should_prompt': should_prompt,
        'triggers': triggers,
        'message_count': message_count
    }

@app.route('/')
def index():
    # Check if user is already registered in this session
    is_registered = session.get('user_registered', False)
    return render_template('index.html', is_registered=is_registered)

@app.route('/api/session-info', methods=['GET'])
def get_session_info():
    """Get current session information including conversation ID"""
    return jsonify({
        'success': True,
        'conversation_id': session.get('conversation_id'),
        'user_name': session.get('user_name'),
        'company_name': session.get('company_name'),
        'registered': session.get('user_registered', False),
        'message_count': session.get('message_count', 0)
    })

@app.route('/register', methods=['POST'])
def register_user():
    """Register a new user and create conversation session"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        company_name = data.get('company_name', '').strip()
        company_email = data.get('company_email', '').strip()
        
        # Validate required fields
        if not all([name, company_name, company_email]):
            return jsonify({'error': 'All fields are required'}), 400
        
        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, company_email):
            return jsonify({'error': 'Please enter a valid email address'}), 400
        
        # Create user in database if database is available
        user_id = None
        if database_url:
            try:
                # Check if user already exists
                existing_user = User.query.filter_by(company_email=company_email).first()
                
                if existing_user:
                    user_id = existing_user.id
                else:
                    # Create new user
                    new_user = User(
                        name=name,
                        company_name=company_name,
                        company_email=company_email
                    )
                    db.session.add(new_user)
                    db.session.commit()
                    user_id = new_user.id
            except Exception as e:
                print(f"Database error during registration: {e}")
        
        # Store user info in session
        session.permanent = True  # Make session persist
        session['user_registered'] = True
        session['user_id'] = user_id
        session['user_name'] = name
        session['company_name'] = company_name
        session['company_email'] = company_email
        
        # Create new conversation for registered user
        conversation_id = str(uuid.uuid4())
        session['conversation_id'] = conversation_id
        session['conversation_history'] = []
        
        # Create conversation record in database for persistence
        try:
            # Create new conversation
            new_conversation = Conversation(
                id=conversation_id,
                user_id=user_id
            )
            db.session.add(new_conversation)
            db.session.commit()
            print(f"Conversation record created: {conversation_id}")
        except Exception as e:
            print(f"Database error with conversation: {e}")
        
        # Start background company analysis using NAIC API with user notifications
        try:
            company_agent = get_company_agent()
            company_agent.start_background_analysis(company_name, company_email, session['conversation_id'])
            log_system("background_analysis_started", {
                "company_name": company_name,
                "company_email": company_email,
                "conversation_id": session['conversation_id']
            })
            print(f"Background analysis started for {company_name} - conversation {session['conversation_id']}")
        except Exception as e:
            print(f"Background analysis failed: {e}")
            log_error(session['conversation_id'], e, {"context": "background_analysis_startup"}, "low")
        
        return jsonify({
            'success': True,
            'message': 'Registration successful',
            'conversation_id': session['conversation_id']
        })
        
    except Exception as e:
        print(f"Registration error: {e}")
        return jsonify({'error': 'Registration failed'}), 500



@app.route('/conversation/<conversation_id>')
def get_conversation(conversation_id):
    """Get conversation messages for loading history"""
    try:
        from models import Message
        messages = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.timestamp).all()
        
        message_list = []
        for msg in messages:
            message_list.append({
                'role': msg.role,
                'content': msg.content,
                'timestamp': msg.timestamp.isoformat()
            })
        
        return jsonify({
            'success': True,
            'messages': message_list
        })
    except Exception as e:
        print(f"Error loading conversation: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/view-conversation/<conversation_id>')
def view_conversation(conversation_id):
    """Access a specific conversation, useful for escalated conversations from Slack"""
    # Set conversation ID in session for continuity
    session['conversation_id'] = conversation_id
    return render_template('chat.html', conversation_id=conversation_id)

@app.route('/load_user_data/<conversation_id>')
def load_user_data(conversation_id):
    """Load existing user data for persistent registration"""
    try:
        conversation = Conversation.query.get(conversation_id)
        if conversation and conversation.user:
            user_data = {
                'name': conversation.user.name,
                'company_name': conversation.user.company_name,
                'company_email': conversation.user.company_email,
                'has_existing_data': True
            }
            return jsonify(user_data)
        else:
            return jsonify({'has_existing_data': False})
    except Exception as e:
        print(f"Error loading user data: {e}")
        return jsonify({'has_existing_data': False, 'error': str(e)})



@app.route('/chat/<conversation_id>')
def chat_page(conversation_id):
    """Direct chat page access with conversation ID"""
    # Set conversation ID in session for continuity
    session['conversation_id'] = conversation_id
    return render_template('chat.html', conversation_id=conversation_id)

@app.route('/chat')
def chat_interface():
    """Display the chat interface"""
    print(f"[DEBUG] /chat GET accessed, session: {dict(session)}")
    
    # Check if user is registered
    if not session.get('user_registered'):
        print("[DEBUG] User not registered, redirecting to home")
        return redirect('/')
    
    print(f"[DEBUG] Displaying chat interface for conversation: {session['conversation_id']}")
    return render_template('chat.html', 
                         conversation_id=session['conversation_id'],
                         is_anonymous=False)

@app.route('/chat', methods=['POST'])
def chat():
    start_time = time.time()
    conversation_id = session.get('conversation_id', str(uuid.uuid4()))
    
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            log_error(conversation_id, ValueError("Empty message received"), 
                     {"request_data": data, "session_id": session.get('conversation_id')}, "low")
            return jsonify({'error': 'Message is required'}), 400
        
        # Get abuse prevention agent
        abuse_prevention = get_abuse_prevention_agent()
        
        # Get IP address (handle proxies)
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ',' in ip_address:
            ip_address = ip_address.split(',')[0].strip()
        
        # Check if request is allowed
        allowed, block_reason = abuse_prevention.check_request_allowed(ip_address, conversation_id)
        if not allowed:
            log_error(conversation_id, ValueError("Request blocked by abuse prevention"), 
                     {"ip_address": ip_address, "reason": block_reason}, "high")
            return jsonify({
                'error': block_reason,
                'blocked': True
            }), 429
        
        # Track request in background (non-blocking)
        abuse_prevention.add_request(
            conversation_id=conversation_id,
            user_id=session.get('user_id'),
            ip_address=ip_address,
            user_agent=request.headers.get('User-Agent', ''),
            message=user_message,
            metadata={
                'session_id': session.get('session_id'),
                'company_name': session.get('company_name')
            }
        )
        
        # Check for registration triggers based on message content
        if "quote" in user_message.lower() or "pricing" in user_message.lower():
            session['quote_requested'] = True
        if "risk assessment" in user_message.lower() or "risk report" in user_message.lower():
            session['risk_assessment_requested'] = True
        if "application" in user_message.lower() or "apply" in user_message.lower():
            session['application_started'] = True
            
        # Log incoming user message
        log_chat(conversation_id, "user", user_message, 
                user_id=session.get('user_id'),
                metadata={
                    "ip_address": ip_address, 
                    "user_agent": request.headers.get('User-Agent'),
                    "session_data": {
                        "user_name": session.get('user_name'),
                        "company_name": session.get('company_name')
                    }
                })
        
        # Check if specialist is active for this conversation
        if conversation_coordinator.is_specialist_active(conversation_id):
            return jsonify({
                "response": "A specialist is currently handling your conversation. Please wait for their response.",
                "specialist_active": True,
                "conversation_id": conversation_id
            })
        
        # Get conversation history from session
        conversation_history = session.get('conversation_history', [])
        
        # Use LLM to determine if escalation is needed instead of simple keyword matching
        needs_immediate_escalation = _should_escalate_with_llm(user_message, conversation_history)
        
        if needs_immediate_escalation:
            # Escalate immediately using Slack router
            escalation_result = slack_router.escalate_conversation(
                conversation_id=conversation_id,
                user_message=user_message,
                routing_analysis={"escalation_reason": "User requested human assistance"},
                conversation_history=conversation_history,
                session_summary=dict(session)
            )
            
            if escalation_result.get('success'):
                return jsonify({
                    "response": "I'm connecting you with a specialist right away. They'll respond shortly via this chat.",
                    "escalated": True,
                    "conversation_id": conversation_id,
                    "specialist_active": True
                })
        
        # Use the full insurance agent with all tools including risk assessment
        ai_start_time = time.time()
        try:
            from agents.core.agents_insurance_chatbot import InsuranceKnowledgeAgent
            # Create agent with conversation context
            agent = InsuranceKnowledgeAgent()
            # Process the message through the full agent asynchronously
            ai_reply = asyncio.run(agent.process_message(
                user_message, 
                conversation_history=conversation_history,
                conversation_id=conversation_id,
                company_name=session.get('company_name', '')
            ))
        except Exception as e:
            print(f"Error with InsuranceKnowledgeAgent: {e}")
            # Fallback to the simple chatbot
            try:
                from embroker_insurance_chatbot import get_embroker_chatbot
                chatbot = get_embroker_chatbot()
                ai_reply = chatbot.chat(user_message)
            except Exception as fallback_e:
                print(f"Fallback also failed: {fallback_e}")
                ai_reply = "I apologize, but I'm having technical difficulties. Please try again in a moment."
        ai_response_time = (time.time() - ai_start_time) * 1000  # Convert to milliseconds
        
        # Log AI response with performance metrics
        log_chat(conversation_id, "assistant", ai_reply,
                user_id=session.get('user_id'),
                response_time_ms=ai_response_time,
                model_used="gpt-4.1-2025-04-14",
                metadata={"conversation_length": len(conversation_history)})
        
        # Add to conversation history
        conversation_history.append({"role": "user", "content": user_message})
        conversation_history.append({"role": "assistant", "content": ai_reply})
        
        # Keep entire conversation history like ChatGPT/Claude/Gemini
        # Only limit if conversation gets extremely long (e.g., over 100 messages)
        if len(conversation_history) > 100:
            # Keep the first message for context and the most recent 98 messages
            session['conversation_history'] = conversation_history[:1] + conversation_history[-98:]
        else:
            session['conversation_history'] = conversation_history  # Keep entire history
        
        # Send conversation to Parallel Monitoring Agent (async, non-blocking)
        monitor_conversation(conversation_id, user_message, ai_reply)
        
        # Store in database if available
        if database_url and session.get('user_id'):
            try:
                # Store conversation
                conv = Conversation.query.filter_by(id=conversation_id).first()
                if not conv:
                    conv = Conversation(
                        id=conversation_id,
                        user_id=session['user_id']
                    )
                    db.session.add(conv)
                
                # Store messages
                user_msg = Message(
                    conversation_id=conversation_id,
                    role='user',
                    content=user_message
                )
                assistant_msg = Message(
                    conversation_id=conversation_id,
                    role='assistant',
                    content=ai_reply
                )
                db.session.add(user_msg)
                db.session.add(assistant_msg)
                db.session.commit()
            except Exception as e:
                log_error(conversation_id, e, 
                         {"operation": "database_storage", "user_id": session.get('user_id')}, "medium")
        
        # Calculate total response time
        total_response_time = (time.time() - start_time) * 1000
        
        # Log successful completion
        log_system("chat_completion", {
            "conversation_id": conversation_id,
            "total_response_time_ms": total_response_time,
            "ai_response_time_ms": ai_response_time,
            "message_length": len(user_message),
            "response_length": len(ai_reply)
        })
        
        # Check if we should prompt for registration
        registration_check = check_should_prompt_registration()
        
        response_data = {
            "response": ai_reply,
            "conversation_id": conversation_id,
            "specialist_active": False,
            "should_prompt_registration": registration_check
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        # Log critical chat errors with full context
        log_error(conversation_id, e, {
            "operation": "chat_processing",
            "user_message": user_message[:100] if 'user_message' in locals() else "unknown",
            "session_data": {
                "user_name": session.get('user_name'),
                "company_name": session.get('company_name'),
                "conversation_length": len(session.get('conversation_history', []))
            },
            "request_data": request.get_json() if request.is_json else {}
        }, "high")
        
        return jsonify({'error': 'Failed to process message'}), 500

@app.route('/new_chat', methods=['POST'])
def new_chat():
    session['conversation_history'] = []
    session['conversation_id'] = str(uuid.uuid4())
    return jsonify({
        'success': True,
        'conversation_id': session['conversation_id']
    })

@app.route('/check-messages/<conversation_id>')
def check_messages(conversation_id):
    """Check for new messages from underwriters via conversation coordinator."""
    try:
        # Check for escalation signals from Parallel Monitoring Agent
        escalation_signals = check_escalation_signals()
        
        # Process any escalation signals for this conversation
        for signal in escalation_signals:
            if signal.conversation_id == conversation_id:
                # Trigger escalation to Slack
                escalation_result = slack_router.escalate_conversation(
                    conversation_id=conversation_id,
                    user_message=f"PMA Escalation: {signal.escalation_reason}",
                    routing_analysis={
                        "escalation_reason": signal.escalation_reason,
                        "urgency": signal.urgency_level,
                        "indicators": signal.indicators,
                        "recommendation": signal.recommendation
                    },
                    conversation_history=session.get('conversation_history', []),
                    session_summary=dict(session)
                )
                
                if escalation_result.get('success'):
                    return jsonify({
                        'success': True,
                        'messages': [{
                            'type': 'escalation',
                            'content': f"Your conversation has been escalated to a specialist due to: {signal.escalation_reason}",
                            'timestamp': signal.timestamp.isoformat()
                        }],
                        'specialist_active': True,
                        'escalated': True
                    })
        
        # Get monitoring status
        monitoring_status = get_conversation_monitoring_status(conversation_id)
        
        # Check for analysis notifications
        import os
        import json
        messages = []
        
        notification_file = f".analysis_notification_{conversation_id}.json"
        if os.path.exists(notification_file):
            try:
                with open(notification_file, 'r') as f:
                    notification_data = json.load(f)
                
                messages.append({
                    "message": notification_data["message"],
                    "sender": "System",
                    "timestamp": notification_data["timestamp"],
                    "source": "analysis_notification"
                })
                
                # Remove notification file after reading
                os.remove(notification_file)
                
            except Exception as e:
                print(f"Error reading notification: {e}")
        
        return jsonify({
            'success': True,
            'has_new_messages': len(messages) > 0,
            'messages': messages,
            'specialist_active': monitoring_status.get('escalated', False),
            'monitoring_status': monitoring_status
        })
    except Exception as e:
        print(f"Error checking messages: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/monitoring/status')
def monitoring_status():
    """Get Parallel Monitoring Agent status"""
    try:
        from agents.monitoring.parallel_monitoring_agent import get_monitoring_agent
        agent = get_monitoring_agent()
        
        return jsonify({
            'monitoring_active': agent.monitoring_active,
            'event_queue_size': agent.event_queue.qsize(),
            'escalation_queue_size': agent.escalation_signals.qsize(),
            'active_conversations': len(agent.conversation_states),
            'total_escalations': len(agent.escalation_history),
            'timestamp': time.time()
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': time.time()
        }), 500

# Comprehensive Logging and Analytics Endpoints
@app.route('/logs/chat/<conversation_id>')
def get_conversation_logs(conversation_id):
    """Get all logs for a specific conversation"""
    try:
        logs = chat_logger.get_conversation_logs(conversation_id)
        return jsonify({
            'success': True,
            'conversation_id': conversation_id,
            'logs': logs,
            'total_messages': len(logs)
        })
    except Exception as e:
        log_error("system", e, {"endpoint": "get_conversation_logs", "conversation_id": conversation_id}, "medium")
        return jsonify({'error': 'Failed to retrieve conversation logs'}), 500

@app.route('/logs/errors')
def get_error_logs():
    """Get error logs with optional filtering"""
    try:
        conversation_id = request.args.get('conversation_id')
        severity = request.args.get('severity')
        resolved = request.args.get('resolved')
        limit = int(request.args.get('limit', 100))
        
        # Convert resolved parameter
        if resolved is not None:
            resolved = resolved.lower() == 'true'
        
        errors = chat_logger.get_error_logs(
            conversation_id=conversation_id,
            severity=severity,
            resolved=resolved,
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'errors': errors,
            'total_errors': len(errors),
            'filters': {
                'conversation_id': conversation_id,
                'severity': severity,
                'resolved': resolved,
                'limit': limit
            }
        })
    except Exception as e:
        log_error("system", e, {"endpoint": "get_error_logs", "query_params": dict(request.args)}, "medium")
        return jsonify({'error': 'Failed to retrieve error logs'}), 500

@app.route('/api/chat-analytics')
@app.route('/logs/analytics/chat')
def get_chat_analytics():
    """Get chat analytics and statistics"""
    try:
        days = int(request.args.get('days', 7))
        stats = chat_logger.get_chat_statistics(days)
        
        return jsonify({
            'success': True,
            'period_days': days,
            'statistics': stats,
            'conversations': stats.get('conversations', [])
        })
    except Exception as e:
        log_error("system", e, {"endpoint": "get_chat_analytics", "days": request.args.get('days')}, "medium")
        return jsonify({'error': 'Failed to retrieve chat analytics'}), 500

@app.route('/api/error-analytics')
def get_api_error_analytics():
    """Get error analytics for dashboard API"""
    try:
        days = int(request.args.get('days', 7))
        stats = chat_logger.get_error_statistics(days)
        
        return jsonify({
            'success': True,
            'period_days': days,
            'statistics': stats
        })
    except Exception as e:
        log_error("system", e, {"endpoint": "get_api_error_analytics"}, "medium")
        return jsonify({'error': 'Failed to retrieve error analytics'}), 500

@app.route('/api/conversation-logs')
def get_api_conversation_logs():
    """Get conversation logs for dashboard API"""
    try:
        conversation_id = request.args.get('conversation_id')
        limit = int(request.args.get('limit', 50))
        
        if conversation_id:
            logs = chat_logger.get_conversation_logs(conversation_id)
        else:
            # Get recent conversations across all users
            logs = []
            try:
                with chat_logger._get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT * FROM chat_logs 
                        WHERE message_type IN ('user', 'assistant') 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    """, (limit,))
                    rows = cursor.fetchall()
                    
                    columns = [desc[0] for desc in cursor.description]
                    logs = [dict(zip(columns, row)) for row in rows]
            except Exception as db_error:
                print(f"Database error in conversation logs: {db_error}")
        
        return jsonify({
            'success': True,
            'logs': logs,
            'count': len(logs)
        })
    except Exception as e:
        log_error("system", e, {"endpoint": "get_api_conversation_logs"}, "medium")
        return jsonify({'error': 'Failed to retrieve conversation logs'}), 500

@app.route('/api/error-logs')
def get_api_error_logs():
    """Get error logs for dashboard API"""
    try:
        severity = request.args.get('severity')
        resolved = request.args.get('resolved')
        limit = int(request.args.get('limit', 50))
        
        resolved_filter = None
        if resolved == 'true':
            resolved_filter = True
        elif resolved == 'false':
            resolved_filter = False
        
        logs = chat_logger.get_error_logs(
            severity=severity,
            resolved=resolved_filter,
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'logs': logs,
            'count': len(logs)
        })
    except Exception as e:
        log_error("system", e, {"endpoint": "get_api_error_logs"}, "medium")
        return jsonify({'error': 'Failed to retrieve error logs'}), 500

@app.route('/logs/conversations')
def get_all_conversations():
    """Get all conversation logs"""
    try:
        limit = int(request.args.get('limit', 100))
        
        # Get conversation data from chat logs
        logs = []
        try:
            with chat_logger._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM chat_logs 
                    WHERE message_type IN ('user', 'assistant') 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (limit,))
                rows = cursor.fetchall()
                
                columns = [desc[0] for desc in cursor.description]
                logs = [dict(zip(columns, row)) for row in rows]
        except Exception as db_error:
            print(f"Database error: {db_error}")
            
        return jsonify({
            'success': True,
            'logs': logs,
            'count': len(logs)
        })
    except Exception as e:
        log_error("system", e, {"endpoint": "get_all_conversations"}, "medium")
        return jsonify({'error': 'Failed to retrieve conversation logs'}), 500

@app.route('/logs/analytics/errors')
def get_error_analytics():
    """Get error analytics and statistics"""
    try:
        days = int(request.args.get('days', 7))
        stats = chat_logger.get_error_statistics(days)
        
        return jsonify({
            'success': True,
            'period_days': days,
            'statistics': stats
        })
    except Exception as e:
        log_error("system", e, {"endpoint": "get_error_analytics", "days": request.args.get('days')}, "medium")
        return jsonify({'error': 'Failed to retrieve error analytics'}), 500

@app.route('/logs/resolve-error/<int:error_id>', methods=['POST'])
def resolve_error(error_id):
    """Mark an error as resolved"""
    try:
        data = request.get_json()
        resolution_notes = data.get('resolution_notes', '')
        
        if not resolution_notes:
            return jsonify({'error': 'Resolution notes are required'}), 400
        
        chat_logger.resolve_error(error_id, resolution_notes)
        
        log_system("error_resolved", {
            "error_id": error_id,
            "resolution_notes": resolution_notes,
            "resolved_by": session.get('user_name', 'unknown')
        })
        
        return jsonify({
            'success': True,
            'message': 'Error marked as resolved',
            'error_id': error_id
        })
    except Exception as e:
        log_error("system", e, {"endpoint": "resolve_error", "error_id": error_id}, "medium")
        return jsonify({'error': 'Failed to resolve error'}), 500

@app.route('/admin/logs')
def logs_dashboard():
    """Admin dashboard for viewing logs and analytics"""
    try:
        days = int(request.args.get('days', 7))
        
        # Get comprehensive statistics
        chat_stats = chat_logger.get_chat_statistics(days)
        error_stats = chat_logger.get_error_statistics(days)
        recent_errors = chat_logger.get_error_logs(resolved=False, limit=10)
        
        log_system("dashboard_access", {
            "user_name": session.get('user_name', 'User'),
            "days_filter": days,
            "ip_address": request.remote_addr
        })
        
        return render_template('logs_dashboard.html', 
                             chat_stats=chat_stats,
                             error_stats=error_stats,
                             recent_errors=recent_errors,
                             days=days)
    except Exception as e:
        log_error("system", e, {"endpoint": "logs_dashboard", "days": request.args.get('days')}, "high")
        return f"Dashboard error: {str(e)}", 500





@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        status = get_agent_status()
        
        # Include monitoring agent status
        monitoring_status_data = {}
        try:
            from agents.monitoring.parallel_monitoring_agent import get_monitoring_agent
            agent = get_monitoring_agent()
            monitoring_status_data = {
                'monitoring_active': agent.monitoring_active,
                'active_conversations': len(agent.conversation_states)
            }
        except Exception:
            monitoring_status_data = {'monitoring_active': False}
        
        return jsonify({
            'status': 'healthy',
            'agent_status': status,
            'monitoring_status': monitoring_status_data,
            'timestamp': time.time()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': time.time()
        }), 500

# SocketIO event handlers
@socketio.on('join_session')
def handle_join_session(data):
    conversation_id = data.get('conversation_id')
    if conversation_id:
        join_room(conversation_id)
        emit('session_joined', {'conversation_id': conversation_id})

@socketio.on('leave_session')  
def handle_leave_session(data):
    conversation_id = data.get('conversation_id')
    if conversation_id:
        leave_room(conversation_id)

@socketio.on('send_message')
def handle_send_message(data):
    conversation_id = data.get('conversation_id')
    message = data.get('message')
    
    if conversation_id and message:
        # Broadcast message to all clients in the room
        emit('new_message', {
            'conversation_id': conversation_id,
            'message': message,
            'timestamp': time.time()
        }, to=conversation_id)

@app.route('/api/chat-history')
def get_chat_history():
    """Get the user's chat history"""
    try:
        # Get current user from session
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'conversations': []})
        
        # Retrieve conversations from database
        conversations = []
        try:
            with app.app_context():
                # Get user's conversations ordered by last activity
                user_conversations = Conversation.query.filter_by(user_id=user_id).order_by(Conversation.created_at.desc()).limit(20).all()
                
                for conv in user_conversations:
                    # Get last message for preview
                    last_message = Message.query.filter_by(conversation_id=conv.id).order_by(Message.created_at.desc()).first()
                    
                    conversations.append({
                        'id': conv.id,
                        'created_at': conv.created_at.isoformat() if conv.created_at else '',
                        'last_message': last_message.content[:50] + '...' if last_message and len(last_message.content) > 50 else (last_message.content if last_message else 'New conversation'),
                        'is_current': conv.id == session.get('conversation_id', '')
                    })
        except Exception as e:
            # If database not available, return empty list
            pass
        
        return jsonify({
            'success': True,
            'conversations': conversations
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/load-conversation/<conversation_id>')
def load_conversation(conversation_id):
    """Load a specific conversation and its messages"""
    try:
        # Check if user has access to this conversation
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        # Get conversation and messages
        messages = []
        try:
            with app.app_context():
                conversation = Conversation.query.get(conversation_id)
                if not conversation or conversation.user_id != user_id:
                    return jsonify({'success': False, 'error': 'Conversation not found'}), 404
                
                # Get all messages for this conversation
                conv_messages = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.created_at.asc()).all()
                
                for msg in conv_messages:
                    messages.append({
                        'role': msg.role,
                        'content': msg.content,
                        'created_at': msg.created_at.isoformat() if msg.created_at else ''
                    })
                
                # Update session with new conversation ID
                session['conversation_id'] = conversation_id
                
        except Exception as e:
            # If database error, still allow switching conversation
            session['conversation_id'] = conversation_id
            pass
        
        return jsonify({
            'success': True,
            'conversation_id': conversation_id,
            'messages': messages
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/risk-assessment/<conversation_id>')
def get_risk_assessment(conversation_id):
    """Get risk assessment report for a conversation"""
    try:
        # Check for stored risk assessment reports in background agent
        from agents.analysis.background_agent import get_company_agent
        company_agent = get_company_agent()
        
        stored_report = company_agent.get_risk_assessment(conversation_id)
        print(f"[RISK API] Looking for conversation: {conversation_id}")
        print(f"[RISK API] Found report: {bool(stored_report)}")
        
        if stored_report:
            # Format the cached report using AI agent
            from agents.formatting.risk_formatter_agent import get_formatter_agent
            formatter = get_formatter_agent()
            formatted_report = formatter.format_risk_report(stored_report)
            return jsonify({
                'success': True,
                'report': formatted_report,
                'generated_at': time.time()
            })
        
        # Try to get classification data from background agent and generate risk assessment
        try:
            from agents.analysis.background_agent import get_company_agent
            from agents.analysis.risk_assessment_agent import RiskAssessmentAgent
            
            company_agent = get_company_agent()
            
            # Look for conversation in session or database
            conversation = None
            try:
                with app.app_context():
                    conversation = Conversation.query.get(conversation_id)
            except Exception as e:
                print(f"Database connection error: {e}")
                pass
            
            company_name = "Technology Company"  # Default
            company_email = None
            
            if conversation and conversation.user:
                company_name = conversation.user.company_name
                company_email = conversation.user.company_email
            elif session.get('company_name'):
                company_name = session.get('company_name')
                company_email = session.get('company_email')
            
            # Debug logging removed for clean production interface
            
            # Get analysis from background agent (should contain API response)
            background_analysis = company_agent.get_analysis(company_name)
            
            if background_analysis and len(background_analysis) > 100 and "being prepared" not in background_analysis:
                # Try to parse JSON data from background analysis
                import json
                try:
                    # Background analysis should contain JSON data from classification API
                    if background_analysis.startswith('{'):
                        analysis_data = json.loads(background_analysis)
                        classification_data = analysis_data.get('raw_classification_response', analysis_data)
                        
                        # Using API classification data for risk assessment
                        
                        # Generate risk assessment using API classification data
                        risk_agent = RiskAssessmentAgent()
                        risk_report = risk_agent.generate_risk_assessment_report(classification_data, company_name)
                        
                        # Store the report
                        if not hasattr(app, 'risk_reports'):
                            app.risk_reports = {}
                        app.risk_reports[conversation_id] = risk_report
                        print(f"[RISK STORE] Stored report for conversation: {conversation_id}")
                        print(f"[RISK STORE] Report length: {len(risk_report)}")
                        print(f"[RISK STORE] All stored conversations: {list(app.risk_reports.keys())}")
                        
                        # Risk assessment completed successfully
                        
                        # Format the report using AI agent
                        from agents.formatting.risk_formatter_agent import get_formatter_agent
                        formatter = get_formatter_agent()
                        formatted_report = formatter.format_risk_report(risk_report)
                        
                        return jsonify({
                            'success': True,
                            'report': formatted_report,
                            'generated_at': time.time()
                        })
                    else:
                        # Background analysis not in expected format, triggering new API call
                        pass
                        
                except json.JSONDecodeError:
                    # Failed to parse analysis data, triggering new API call
                    pass
            
            # If no valid analysis available, trigger background analysis with company email
            if company_email:
                # Starting background analysis for risk assessment
                company_agent.start_background_analysis(company_name, company_email, conversation_id)
            
        except Exception as e:
            # Error getting classification data - silently continue for clean interface
            pass
        
        return jsonify({
            'success': False,
            'message': 'Risk assessment not available yet'
        })
        
    except Exception as e:
        # Error getting risk assessment - return clean error message
        return jsonify({'success': False, 'message': 'Unable to generate risk assessment at this time'}), 500

@app.route('/api/generate-risk-assessment', methods=['POST'])
def generate_risk_assessment():
    """Generate risk assessment report in background"""
    try:
        data = request.get_json()
        conversation_id = data.get('conversation_id')
        
        if not conversation_id:
            return jsonify({'success': False, 'error': 'Missing conversation_id'}), 400
        
        # Start background generation
        def background_generate():
            try:
                from agents.analysis.background_agent import get_company_agent
                from agents.analysis.risk_assessment_agent import RiskAssessmentAgent
                
                # Get conversation details
                conversation = None
                company_name = "Technology Company"
                
                try:
                    with app.app_context():
                        conversation = Conversation.query.get(conversation_id)
                        if conversation and conversation.user:
                            company_name = conversation.user.company_name
                except Exception as e:
                    print(f"Database connection error in background: {e}")
                    pass
                
                # Wait for background analysis to complete (API can take 20+ seconds)
                max_attempts = 20  # 60 seconds total
                for attempt in range(max_attempts):
                    time.sleep(3)
                    
                    company_agent = get_company_agent()
                    background_analysis = company_agent.get_analysis(company_name)
                    print(f"[GENERATE RISK] Attempt {attempt+1}/{max_attempts} - Retrieved analysis for {company_name}, length: {len(background_analysis) if background_analysis else 0}")
                    
                    # Check if we have real JSON data (not the "being prepared" message)
                    if background_analysis and background_analysis.startswith('{'):
                        print(f"[GENERATE RISK] Got valid JSON data!")
                        break
                    elif background_analysis:
                        print(f"[GENERATE RISK] Still waiting, got: {background_analysis[:100]}...")
                
                if background_analysis and len(background_analysis) > 50:
                    # Parse JSON from background analysis if available
                    try:
                        import json
                        if background_analysis.startswith('{'):
                            analysis_json = json.loads(background_analysis)
                            classification_data = analysis_json.get('raw_classification_response', analysis_json)
                        else:
                            # No valid API response available - cannot generate risk assessment
                            print(f"Background analysis not in expected JSON format for {conversation_id}")
                            return
                    except Exception as parse_error:
                        print(f"JSON parse error: {parse_error}")
                        # No valid API response available - cannot generate risk assessment
                        print(f"Cannot parse classification data for {conversation_id}")
                        return
                    
                    # Generate comprehensive risk assessment
                    risk_agent = RiskAssessmentAgent()
                    
                    risk_report = risk_agent.generate_risk_assessment_report(classification_data, company_name)
                    
                    # Store the report in background agent cache instead of app state
                    # (app state doesn't persist across gunicorn workers)
                    company_agent.store_risk_assessment(conversation_id, risk_report)
                    
                    print(f"Background risk assessment stored for conversation {conversation_id}: {len(risk_report)} characters")
                    
                    print(f"Risk assessment generated for {conversation_id}")
                
            except Exception as e:
                print(f"Background risk generation error: {e}")
        
        # Start background thread
        thread = threading.Thread(target=background_generate)
        thread.daemon = True
        thread.start()
        
        return jsonify({'success': True, 'message': 'Risk assessment generation started'})
        
    except Exception as e:
        print(f"Error starting risk assessment generation: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def _should_escalate_with_llm(user_message: str, conversation_history: list) -> bool:
    """
    Use LLM to intelligently determine if a conversation should be escalated to human specialists.
    This replaces simple keyword matching with contextual understanding.
    """
    try:
        # Prepare conversation context
        context_messages = []
        for msg in conversation_history[-5:]:  # Last 5 messages for context
            role = "user" if msg.get('sender') == 'user' else "assistant"
            context_messages.append(f"{role}: {msg.get('message', '')}")
        
        conversation_context = "\n".join(context_messages) if context_messages else "No previous context"
        
        # LLM escalation analysis prompt
        escalation_prompt = f"""
You are an escalation decision system for an AI insurance chatbot. Analyze the following user message and conversation context to determine if this conversation should be escalated to a human specialist.

Current User Message: "{user_message}"

Recent Conversation Context:
{conversation_context}

ESCALATION CRITERIA - Only escalate if the user:
1. EXPLICITLY requests a human agent ("speak to someone", "human", "agent", "transfer me")
2. Wants to FILE AN ACTUAL CLAIM ("I need to file a claim", "how do I submit a claim")
3. Asks about STATUS of an existing claim ("what's the status of my claim", "my claim number is")
4. Expresses severe frustration or anger (multiple failed attempts)
5. Wants to cancel service or file a formal complaint

DO NOT ESCALATE for:
- Questions about claim EXAMPLES ("what are claim examples", "give me examples")
- Hypothetical scenarios ("what could happen if", "what might occur")
- Educational questions about coverage, limits, policies, processes
- General information requests about insurance concepts
- Questions about possibilities, risks, or potential issues
- Technical questions about coverage details, deductibles, limits
- Industry-specific questions ("as a tech company, what...")
- ANY question that starts with "what", "how", "why" about general topics

Respond with a JSON object:
{{
    "should_escalate": true/false,
    "reason": "brief explanation",
    "confidence": 0.0-1.0
}}
"""

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Fast model for escalation decisions
            messages=[
                {"role": "system", "content": "You are an expert escalation decision system. Provide accurate JSON analysis of whether conversations need human intervention."},
                {"role": "user", "content": escalation_prompt}
            ],
            temperature=0.1,
            max_tokens=150
        )
        
        # Parse response
        response_text = response.choices[0].message.content.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:-3]
        elif response_text.startswith("```"):
            response_text = response_text[3:-3]
            
        analysis = json.loads(response_text)
        
        # Log the escalation decision for monitoring
        log_system("llm_escalation_decision", {
            "user_message": user_message,
            "should_escalate": analysis.get("should_escalate", False),
            "reason": analysis.get("reason", ""),
            "confidence": analysis.get("confidence", 0.0),
            "context_length": len(context_messages)
        })
        
        return analysis.get("should_escalate", False)
        
    except Exception as e:
        # If LLM analysis fails, fall back to conservative escalation
        log_error("system", e, {"context": "llm_escalation_analysis", "user_message": user_message}, "medium")
        
        # Fallback: Check for explicit human requests only
        explicit_keywords = ['human', 'agent', 'speak to someone', 'talk to someone', 'transfer', 'representative']
        return any(keyword in user_message.lower() for keyword in explicit_keywords)

@app.route('/api/abuse-prevention-stats')
def get_abuse_prevention_stats():
    """Get abuse prevention statistics"""
    try:
        abuse_prevention = get_abuse_prevention_agent()
        stats = abuse_prevention.get_monitoring_stats()
        
        # Get recent abuse signals
        signals = abuse_prevention.get_abuse_signals()
        signal_data = []
        for signal in signals[-10:]:  # Last 10 signals
            signal_data.append({
                'conversation_id': signal.conversation_id,
                'abuse_type': signal.abuse_type,
                'severity': signal.severity,
                'confidence': signal.confidence,
                'action': signal.action,
                'ip_address': signal.ip_address,
                'timestamp': signal.timestamp.isoformat(),
                'indicators': signal.indicators
            })
        
        return jsonify({
            'success': True,
            'statistics': stats,
            'recent_signals': signal_data
        })
    except Exception as e:
        log_error("system", e, {"endpoint": "get_abuse_prevention_stats"}, "medium")
        return jsonify({'error': 'Failed to retrieve abuse prevention statistics'}), 500

@app.route('/api/clear-blocked-ips', methods=['POST'])
def clear_blocked_ips():
    """Clear blocked IPs (admin endpoint)"""
    try:
        # In production, add authentication here
        abuse_prevention = get_abuse_prevention_agent()
        
        # Clear specific IP or all
        data = request.get_json() or {}
        ip_address = data.get('ip_address')
        
        if ip_address:
            # Clear specific IP
            if ip_address in abuse_prevention.blocked_ips:
                abuse_prevention.blocked_ips.remove(ip_address)
                message = f"Unblocked IP: {ip_address}"
            else:
                message = f"IP {ip_address} was not blocked"
        else:
            # Clear all blocked IPs
            count = len(abuse_prevention.blocked_ips)
            abuse_prevention.blocked_ips.clear()
            message = f"Cleared {count} blocked IPs"
        
        log_system("abuse_prevention_admin", {
            "action": "clear_blocked_ips",
            "ip_address": ip_address,
            "message": message
        })
        
        return jsonify({
            'success': True,
            'message': message
        })
    except Exception as e:
        log_error("system", e, {"endpoint": "clear_blocked_ips"}, "high")
        return jsonify({'error': 'Failed to clear blocked IPs'}), 500

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=8000)