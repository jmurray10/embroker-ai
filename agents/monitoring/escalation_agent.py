# escalation_agent.py
"""
Escalation Agent for managing human handoffs and Slack notifications
Handles complex cases that require human underwriter intervention
"""

import json
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
from openai import OpenAI
import time

class EscalationType(Enum):
    """Types of escalations"""
    UNDERWRITING_REVIEW = "underwriting_review"
    COMPLEX_QUOTE = "complex_quote"
    COMPLIANCE_ISSUE = "compliance_issue"
    CUSTOMER_COMPLAINT = "customer_complaint"
    TECHNICAL_ISSUE = "technical_issue"
    HIGH_VALUE_ACCOUNT = "high_value_account"

class EscalationPriority(Enum):
    """Escalation priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

@dataclass
class EscalationRequest:
    """Represents an escalation request"""
    escalation_type: EscalationType
    priority: EscalationPriority
    conversation_id: str
    customer_message: str
    context: Dict[str, Any]
    reason: str
    suggested_actions: List[str]
    timestamp: float
    assigned_to: Optional[str] = None

class EscalationAgent:
    """Manages escalations to human underwriters and specialists"""
    
    def __init__(self):
        """Initialize escalation agent"""
        self.openai_client = OpenAI(api_key=os.getenv("POC_OPENAI_API"))
        self.model = "gpt-4.1-2025-04-14"
        
        # Track active escalations
        self.active_escalations = {}
        self.escalation_history = {}
        
        # Slack integration for notifications
        self.slack_channel = os.getenv("SLACK_ESCALATION_CHANNEL", "#underwriting-escalations")
        
        # Escalation routing rules
        self.routing_rules = {
            EscalationType.UNDERWRITING_REVIEW: "underwriting_team",
            EscalationType.COMPLEX_QUOTE: "senior_underwriter",
            EscalationType.COMPLIANCE_ISSUE: "compliance_team",
            EscalationType.CUSTOMER_COMPLAINT: "customer_success",
            EscalationType.TECHNICAL_ISSUE: "technical_support",
            EscalationType.HIGH_VALUE_ACCOUNT: "senior_underwriter"
        }
    
    async def create_escalation(self, conversation_id: str, reason: str, 
                              context: Dict[str, Any], customer_message: str = "") -> Dict[str, Any]:
        """
        Create a new escalation request
        
        Args:
            conversation_id: Unique conversation identifier
            reason: Reason for escalation
            context: Conversation context and analysis
            customer_message: Original customer message
            
        Returns:
            Escalation details and next steps
        """
        
        # Analyze escalation type and priority
        escalation_analysis = await self._analyze_escalation_need(reason, context, customer_message)
        
        # Create escalation request
        escalation = EscalationRequest(
            escalation_type=escalation_analysis["type"],
            priority=escalation_analysis["priority"],
            conversation_id=conversation_id,
            customer_message=customer_message,
            context=context,
            reason=reason,
            suggested_actions=escalation_analysis["suggested_actions"],
            timestamp=time.time()
        )
        
        # Store escalation
        self.active_escalations[conversation_id] = escalation
        
        # Send Slack notification
        slack_response = await self._send_slack_notification(escalation)
        
        # Generate customer-facing response
        customer_response = await self._generate_customer_response(escalation)
        
        # Log escalation
        self._log_escalation(escalation)
        
        return {
            "escalation_id": conversation_id,
            "customer_response": customer_response,
            "internal_notification": slack_response,
            "priority": escalation.priority.value,
            "estimated_response_time": self._get_estimated_response_time(escalation.priority)
        }
    
    async def _analyze_escalation_need(self, reason: str, context: Dict[str, Any], 
                                     customer_message: str) -> Dict[str, Any]:
        """Analyze the type and priority of escalation needed"""
        
        analysis_prompt = f"""
        Analyze this escalation request and categorize it:
        
        Escalation Reason: {reason}
        Customer Message: {customer_message}
        Context: {json.dumps(context, indent=2)}
        
        Determine:
        1. Escalation type (underwriting_review, complex_quote, compliance_issue, customer_complaint, technical_issue, high_value_account)
        2. Priority level (low, medium, high, urgent)
        3. Suggested actions for the human agent
        
        Consider these factors:
        - Complexity of the request
        - Customer sentiment
        - Revenue potential
        - Risk factors
        - Time sensitivity
        
        Respond with JSON format:
        {{
            "type": "escalation_type",
            "priority": "priority_level",
            "reasoning": "explanation of categorization",
            "suggested_actions": ["action1", "action2", "action3"],
            "estimated_complexity": "low|medium|high",
            "requires_specialist": true/false
        }}
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert escalation analyst for insurance operations."},
                    {"role": "user", "content": analysis_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=600
            )
            
            analysis = json.loads(response.choices[0].message.content)
            
            # Convert string values to enums
            escalation_type = EscalationType(analysis.get("type", "underwriting_review"))
            priority = EscalationPriority(analysis.get("priority", "medium"))
            
            return {
                "type": escalation_type,
                "priority": priority,
                "reasoning": analysis.get("reasoning", ""),
                "suggested_actions": analysis.get("suggested_actions", []),
                "estimated_complexity": analysis.get("estimated_complexity", "medium"),
                "requires_specialist": analysis.get("requires_specialist", False)
            }
            
        except Exception as e:
            # Fallback categorization
            return {
                "type": EscalationType.UNDERWRITING_REVIEW,
                "priority": EscalationPriority.MEDIUM,
                "reasoning": f"Automatic categorization due to analysis error: {str(e)}",
                "suggested_actions": ["Review customer request", "Provide detailed response"],
                "estimated_complexity": "medium",
                "requires_specialist": False
            }
    
    async def _send_slack_notification(self, escalation: EscalationRequest) -> Dict[str, Any]:
        """Send Slack notification about the escalation"""
        
        # Import slack SDK if available
        try:
            from slack_sdk import WebClient
            slack_token = os.getenv('SLACK_BOT_TOKEN')
            
            if not slack_token:
                return {"status": "no_slack_token", "message": "Slack notifications not configured"}
            
            client = WebClient(token=slack_token)
            
            # Format escalation message
            priority_emoji = {
                EscalationPriority.LOW: "[LOW]",
                EscalationPriority.MEDIUM: "[MEDIUM]", 
                EscalationPriority.HIGH: "[HIGH]",
                EscalationPriority.URGENT: "[URGENT]"
            }
            
            message = f"""
{priority_emoji.get(escalation.priority, "[UNKNOWN]")} *New Escalation - {escalation.priority.value.upper()}*

*Type:* {escalation.escalation_type.value.replace('_', ' ').title()}
*Conversation ID:* {escalation.conversation_id}
*Reason:* {escalation.reason}

*Customer Message:*
> {escalation.customer_message[:500]}{'...' if len(escalation.customer_message) > 500 else ''}

*Suggested Actions:*
{chr(10).join(f"• {action}" for action in escalation.suggested_actions)}

*Assigned to:* {self.routing_rules.get(escalation.escalation_type, 'General Queue')}
            """
            
            response = client.chat_postMessage(
                channel=self.slack_channel,
                text=message,
                unfurl_links=False,
                unfurl_media=False
            )
            
            return {
                "status": "sent",
                "slack_ts": response["ts"],
                "channel": self.slack_channel
            }
            
        except ImportError:
            return {"status": "slack_not_available", "message": "Slack SDK not installed"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to send Slack notification: {str(e)}"}
    
    async def _generate_customer_response(self, escalation: EscalationRequest) -> str:
        """Generate appropriate customer-facing response for escalation"""
        
        response_prompt = f"""
        Generate a professional, empathetic customer response for this escalation:
        
        Escalation Type: {escalation.escalation_type.value}
        Priority: {escalation.priority.value}
        Reason: {escalation.reason}
        
        The response should:
        1. Acknowledge their request professionally
        2. Explain that a specialist will review their case
        3. Provide estimated response timeframe
        4. Reassure them of our commitment to help
        5. Maintain Embroker's conversational, helpful tone
        
        Keep it concise but warm and professional.
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are Embroker AI, Embroker's professional and empathetic customer service assistant."},
                    {"role": "user", "content": response_prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            # Fallback response
            estimated_time = self._get_estimated_response_time(escalation.priority)
            return f"Thank you for your inquiry. I've forwarded your request to our specialized team for detailed review. You can expect a response within {estimated_time}. We appreciate your patience and look forward to assisting you."
    
    def _get_estimated_response_time(self, priority: EscalationPriority) -> str:
        """Get estimated response time based on priority"""
        
        time_estimates = {
            EscalationPriority.URGENT: "2-4 hours",
            EscalationPriority.HIGH: "4-8 hours", 
            EscalationPriority.MEDIUM: "1-2 business days",
            EscalationPriority.LOW: "2-3 business days"
        }
        
        return time_estimates.get(priority, "1-2 business days")
    
    def _log_escalation(self, escalation: EscalationRequest):
        """Log escalation for tracking and analytics"""
        
        log_entry = {
            "timestamp": escalation.timestamp,
            "conversation_id": escalation.conversation_id,
            "type": escalation.escalation_type.value,
            "priority": escalation.priority.value,
            "reason": escalation.reason,
            "assigned_to": self.routing_rules.get(escalation.escalation_type, "general")
        }
        
        # Store in escalation history
        if escalation.conversation_id not in self.escalation_history:
            self.escalation_history[escalation.conversation_id] = []
        
        self.escalation_history[escalation.conversation_id].append(log_entry)
    
    def get_active_escalations(self) -> Dict[str, Any]:
        """Get all active escalations"""
        
        return {
            conversation_id: {
                "type": escalation.escalation_type.value,
                "priority": escalation.priority.value,
                "reason": escalation.reason,
                "timestamp": escalation.timestamp,
                "age_hours": (time.time() - escalation.timestamp) / 3600
            }
            for conversation_id, escalation in self.active_escalations.items()
        }
    
    def resolve_escalation(self, conversation_id: str, resolution: str, resolved_by: str) -> Dict[str, Any]:
        """Mark an escalation as resolved"""
        
        if conversation_id in self.active_escalations:
            escalation = self.active_escalations[conversation_id]
            
            # Log resolution
            resolution_entry = {
                "timestamp": time.time(),
                "conversation_id": conversation_id,
                "resolution": resolution,
                "resolved_by": resolved_by,
                "resolution_time_hours": (time.time() - escalation.timestamp) / 3600
            }
            
            # Move to history
            if conversation_id not in self.escalation_history:
                self.escalation_history[conversation_id] = []
            
            self.escalation_history[conversation_id].append(resolution_entry)
            
            # Remove from active
            del self.active_escalations[conversation_id]
            
            return {
                "status": "resolved",
                "resolution_time": resolution_entry["resolution_time_hours"]
            }
        
        return {"status": "not_found"}
    
    def get_escalation_analytics(self) -> Dict[str, Any]:
        """Get escalation analytics and metrics"""
        
        active_count = len(self.active_escalations)
        total_escalations = len(self.escalation_history)
        
        # Calculate average resolution time (simplified)
        resolution_times = []
        for history in self.escalation_history.values():
            for entry in history:
                if "resolution_time_hours" in entry:
                    resolution_times.append(entry["resolution_time_hours"])
        
        avg_resolution_time = sum(resolution_times) / len(resolution_times) if resolution_times else 0
        
        # Count by type and priority
        type_counts = {}
        priority_counts = {}
        
        for escalation in self.active_escalations.values():
            type_key = escalation.escalation_type.value
            priority_key = escalation.priority.value
            
            type_counts[type_key] = type_counts.get(type_key, 0) + 1
            priority_counts[priority_key] = priority_counts.get(priority_key, 0) + 1
        
        return {
            "active_escalations": active_count,
            "total_escalations": total_escalations,
            "average_resolution_hours": round(avg_resolution_time, 2),
            "escalations_by_type": type_counts,
            "escalations_by_priority": priority_counts,
            "slack_channel": self.slack_channel
        }

# Global escalation agent instance
_escalation_agent = None

def get_escalation_agent():
    """Get or create the global escalation agent instance"""
    global _escalation_agent
    if _escalation_agent is None:
        _escalation_agent = EscalationAgent()
    return _escalation_agent

async def create_escalation(conversation_id: str, reason: str, context: Dict[str, Any], 
                          customer_message: str = "") -> Dict[str, Any]:
    """Main entry point for creating escalations"""
    agent = get_escalation_agent()
    return await agent.create_escalation(conversation_id, reason, context, customer_message)