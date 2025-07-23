"""
Abuse Prevention System for AI Insurance Chatbot
Focuses on maintaining good UX while preventing off-topic usage
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from openai import OpenAI
import logging

logger = logging.getLogger(__name__)

class AbusePreventionAgent:
    """
    Intelligent abuse prevention that guides users back to insurance topics
    rather than blocking them harshly
    """
    
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("POC_OPENAI_API"))
        self.model = "gpt-4o-mini-2024-07-18"  # Fast, cost-effective for monitoring
        
        # Tracking dictionaries
        self.user_warnings = defaultdict(int)  # user_id -> warning count
        self.user_last_warning = {}  # user_id -> timestamp
        self.conversation_topics = defaultdict(list)  # conversation_id -> [topics]
        self.user_daily_messages = defaultdict(lambda: defaultdict(int))  # user_id -> date -> count
        
        # Soft limits - more generous than typical rate limiting
        self.config = {
            'off_topic_warnings_before_limit': 3,  # Warnings before rate limit
            'warning_reset_hours': 24,  # Reset warnings after 24 hours
            'max_messages_per_hour': 50,  # Very generous for legitimate use
            'max_messages_per_day': 200,  # Plenty for insurance discussions
            'min_message_interval_seconds': 2,  # Prevent rapid-fire abuse
            'topic_relevance_threshold': 0.3,  # 30% insurance-related minimum
        }
        
        # Insurance-related keywords for quick filtering
        self.insurance_keywords = {
            'insurance', 'policy', 'coverage', 'claim', 'premium', 'deductible',
            'liability', 'risk', 'underwriting', 'embroker', 'broker', 'agent',
            'cyber', 'epli', 'e&o', 'errors', 'omissions', 'd&o', 'directors',
            'officers', 'general liability', 'professional', 'indemnity', 'loss',
            'exposure', 'compliance', 'regulatory', 'tech e&o', 'technology',
            'business', 'company', 'startup', 'enterprise', 'sme', 'quote'
        }

    def check_message(self, user_id: str, message: str, conversation_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a message should be allowed
        Returns: (allowed, warning_message)
        """
        # Check rate limits first (non-blocking)
        rate_limit_check = self._check_rate_limits(user_id)
        if not rate_limit_check[0]:
            return rate_limit_check
        
        # Quick keyword check for obviously insurance-related messages
        if self._quick_insurance_check(message):
            self._update_topic_tracking(conversation_id, "insurance", 1.0)
            return (True, None)
        
        # AI-powered topic analysis for ambiguous messages
        topic_analysis = self._analyze_message_topic(message)
        
        # Update topic tracking
        self._update_topic_tracking(conversation_id, topic_analysis['topic'], topic_analysis['confidence'])
        
        # Check if message is off-topic
        if not topic_analysis['is_insurance_related']:
            return self._handle_off_topic_message(user_id, conversation_id, topic_analysis)
        
        return (True, None)

    def _quick_insurance_check(self, message: str) -> bool:
        """Quick keyword-based check for insurance topics"""
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in self.insurance_keywords)

    def _analyze_message_topic(self, message: str) -> Dict:
        """Use AI to analyze if message is insurance-related"""
        try:
            prompt = f"""Analyze if this message is related to insurance, risk management, or business coverage.
            
Message: "{message}"

Consider these as ON-TOPIC:
- Insurance questions (any type of business insurance)
- Risk management and assessment
- Business operations that relate to insurance needs
- Embroker services and products
- Coverage recommendations
- Claims scenarios
- Compliance and regulatory questions
- Company information needed for insurance

Consider these as OFF-TOPIC:
- Programming/coding requests
- Homework help (non-insurance)
- General knowledge questions
- Entertainment
- Personal advice (non-business)
- Math problems (unless insurance calculations)
- Creative writing
- Technical support (non-insurance systems)

Respond with JSON:
{{
    "is_insurance_related": true/false,
    "topic": "brief topic description",
    "confidence": 0.0-1.0,
    "suggestion": "helpful redirect if off-topic"
}}"""

            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Error analyzing message topic: {e}")
            # Default to allowing the message if analysis fails
            return {
                "is_insurance_related": True,
                "topic": "unknown",
                "confidence": 0.5,
                "suggestion": ""
            }

    def _handle_off_topic_message(self, user_id: str, conversation_id: str, analysis: Dict) -> Tuple[bool, Optional[str]]:
        """Handle off-topic messages with progressive warnings"""
        
        # Check if user has been warned recently
        last_warning = self.user_last_warning.get(user_id, 0)
        hours_since_warning = (time.time() - last_warning) / 3600
        
        # Reset warnings if enough time has passed
        if hours_since_warning > self.config['warning_reset_hours']:
            self.user_warnings[user_id] = 0
        
        # Increment warning count
        self.user_warnings[user_id] += 1
        self.user_last_warning[user_id] = time.time()
        
        warning_count = self.user_warnings[user_id]
        
        # Progressive warning messages
        if warning_count == 1:
            message = self._get_friendly_redirect(analysis)
        elif warning_count == 2:
            message = self._get_firm_redirect(analysis)
        elif warning_count >= self.config['off_topic_warnings_before_limit']:
            # Check conversation topic ratio
            topic_ratio = self._calculate_topic_ratio(conversation_id)
            if topic_ratio < self.config['topic_relevance_threshold']:
                return (False, self._get_limit_message())
            else:
                # If they've been mostly on-topic, give them another chance
                message = self._get_final_warning(analysis)
        
        return (True, message)  # Still allow the message but with warning

    def _get_friendly_redirect(self, analysis: Dict) -> str:
        """First warning - friendly and helpful"""
        suggestion = analysis.get('suggestion', 'insurance and risk management questions')
        return f"""I notice you're asking about {analysis['topic']}. I'm specifically designed to help with insurance and risk management questions for businesses. 

How can I help you with:
• Business insurance coverage recommendations
• Risk assessment for your company
• Understanding different policy types
• Embroker products and services
• Claims scenarios and examples

What insurance or risk management topic can I assist you with today?"""

    def _get_firm_redirect(self, analysis: Dict) -> str:
        """Second warning - more direct"""
        return f"""I need to focus on insurance-related topics. I'm an expert in:

• Tech E&O, Cyber, D&O, and General Liability insurance
• Risk assessment for startups and enterprises
• Underwriting and claims processes
• Compliance and regulatory requirements

Please ask me about business insurance, risk management, or Embroker services. What specific insurance question do you have?"""

    def _get_final_warning(self, analysis: Dict) -> str:
        """Final warning before rate limiting"""
        return f"""⚠️ **Final Notice**: To ensure I can help everyone with insurance needs, I must limit off-topic discussions. 

I'm here specifically for:
✓ Business insurance guidance
✓ Risk management advice
✓ Coverage recommendations
✓ Embroker product information

Please keep our conversation focused on these topics. What insurance question can I answer for you?"""

    def _get_limit_message(self) -> str:
        """Rate limit message"""
        return f"""I appreciate your interest, but I need to maintain focus on insurance and risk management topics to best serve all users.

**Why this limit?**
This ensures I can provide quality insurance guidance to businesses that need it.

**What you can do:**
• Return with insurance or risk management questions
• Learn about Embroker's products and services
• Get help with business coverage needs

I'll be happy to help with any insurance-related questions when you return!"""

    def _check_rate_limits(self, user_id: str) -> Tuple[bool, Optional[str]]:
        """Check basic rate limits"""
        now = datetime.now()
        today = now.date().isoformat()
        
        # Check daily limit
        daily_count = self.user_daily_messages[user_id][today]
        if daily_count >= self.config['max_messages_per_day']:
            return (False, "You've reached the daily message limit. Please return tomorrow for more insurance guidance!")
        
        # Update count
        self.user_daily_messages[user_id][today] += 1
        
        return (True, None)

    def _update_topic_tracking(self, conversation_id: str, topic: str, confidence: float):
        """Track topics discussed in conversation"""
        self.conversation_topics[conversation_id].append({
            'topic': topic,
            'confidence': confidence,
            'timestamp': time.time()
        })

    def _calculate_topic_ratio(self, conversation_id: str) -> float:
        """Calculate ratio of insurance-related topics in conversation"""
        topics = self.conversation_topics.get(conversation_id, [])
        if not topics:
            return 1.0  # Assume good faith for new conversations
        
        # Only look at recent topics (last 20 messages)
        recent_topics = topics[-20:]
        insurance_topics = sum(1 for t in recent_topics if 'insurance' in t['topic'].lower() or t['confidence'] > 0.7)
        
        return insurance_topics / len(recent_topics) if recent_topics else 1.0

    def get_user_status(self, user_id: str) -> Dict:
        """Get current status for a user"""
        today = datetime.now().date().isoformat()
        daily_count = self.user_daily_messages[user_id][today]
        
        return {
            'warnings': self.user_warnings.get(user_id, 0),
            'daily_messages': daily_count,
            'daily_limit': self.config['max_messages_per_day'],
            'can_send': daily_count < self.config['max_messages_per_day']
        }

    def reset_user_warnings(self, user_id: str):
        """Reset warnings for a user (admin function)"""
        self.user_warnings[user_id] = 0
        self.user_last_warning.pop(user_id, None)

# Global instance
abuse_prevention = AbusePreventionAgent()

def check_message_allowed(user_id: str, message: str, conversation_id: str) -> Tuple[bool, Optional[str]]:
    """
    Main entry point for abuse prevention
    Returns: (allowed, warning_message)
    """
    return abuse_prevention.check_message(user_id, message, conversation_id)

def get_user_status(user_id: str) -> Dict:
    """Get user's current status"""
    return abuse_prevention.get_user_status(user_id)