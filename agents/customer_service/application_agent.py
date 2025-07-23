"""
Embroker Application Agent
Specialized agent for handling all insurance application questions using vector store knowledge
"""

import logging
import os
from typing import Dict, Any, List
from openai import OpenAI

class ApplicationAgent:
    """Specialized agent for Embroker insurance application guidance"""
    
    def __init__(self):
        """Initialize the application agent"""
        self.client = OpenAI(api_key=os.getenv('POC_OPENAI_API'))
        self.vector_store_id = "vs_6843730d282481918003cdb215f5e0b1"
        self.model = "gpt-4o-mini-2024-07-18"  # Fast model for application guidance
        
    def can_handle_query(self, message: str) -> bool:
        """Determine if this agent should handle the query"""
        application_keywords = [
            'application', 'apply', 'form', 'questionnaire', 'questions',
            'submit', 'filing', 'paperwork', 'documentation', 'required',
            'what information', 'what do I need', 'how to apply',
            'application process', 'application form', 'fill out',
            'requirements', 'documents needed', 'information needed',
            'what do you need to quote', 'need to quote', 'quote fintech',
            'fintech application', 'fintech questions', 'tech e&o questions'
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in application_keywords)
    
    def process_application_query(self, message: str, conversation_history: List[Dict] = None) -> str:
        """Process application-related queries using vector store"""
        try:
            # Prepare conversation history
            messages = []
            if conversation_history:
                messages.extend(conversation_history)
            
            # Add system message with application-specific instructions
            system_message = {
                "role": "system",
                "content": self._get_application_instructions()
            }
            messages.insert(0, system_message)
            
            # Add user message
            messages.append({"role": "user", "content": message})
            
            # Create completion using Chat Completions API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logging.error(f"[ApplicationAgent] Error processing query: {str(e)}")
            return "I'm having trouble accessing the application information right now. Please try again or contact our support team for assistance with your application questions."
    
    def _get_application_instructions(self) -> str:
        """Get specialized application agent instructions"""
        return """You are an experienced Embroker Application Specialist who helps customers navigate the insurance application process with warmth and expertise.

CONVERSATION STYLE:
• Be friendly, encouraging, and patient - applying for insurance can feel overwhelming
• Use conversational language that puts customers at ease
• Break down complex processes into simple, manageable steps
• Acknowledge their specific business needs and show genuine interest
• Provide context for why certain information is needed

GUIDANCE APPROACH:
• Start by understanding their business and specific coverage needs
• Walk them through the application process step-by-step
• Explain what documents they'll need and why each is important
• Share tips to make the process smoother and faster
• Anticipate common questions and address them proactively
• Offer to clarify anything that seems confusing

RESPONSE FORMAT:
• Use bullet points for lists and step-by-step instructions
• Include brief explanations of why each step matters
• Provide practical tips and recommendations
• End with an encouraging note or next step

EMBROKER EXPERTISE:
• Highlight our streamlined digital application process
• Mention our expert support team availability
• Explain how our technology makes applications faster and easier
• Share relevant industry insights that help with their application

Remember: You're not just processing paperwork - you're helping protect their business dreams."""

    def get_agent_status(self) -> Dict[str, Any]:
        """Get application agent status"""
        return {
            "agent_type": "application_specialist",
            "model": self.model,
            "vector_store": self.vector_store_id,
            "specialization": "insurance_applications",
            "status": "active"
        }

def get_application_agent():
    """Get or create the application agent instance"""
    if not hasattr(get_application_agent, '_instance'):
        get_application_agent._instance = ApplicationAgent()
    return get_application_agent._instance

async def process_application_query(message: str, conversation_history: List[Dict] = None) -> str:
    """Main entry point for processing application queries"""
    agent = get_application_agent()
    return agent.process_application_query(message, conversation_history)