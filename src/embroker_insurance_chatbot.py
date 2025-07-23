#!/usr/bin/env python3
"""
Complete RAG chatbot for Embroker insurance queries
Based on the working EmbrokerInsuranceChatbot implementation
"""

import os
from openai import OpenAI
from typing import List, Dict, Any
from integrations.embroker_knowledge_base import EmbrokerKnowledgeBase


class EmbrokerInsuranceChatbot:
    """Complete RAG chatbot for Embroker insurance queries"""
    
    def __init__(self):
        """Initialize the Embroker insurance chatbot"""
        self.openai_client = OpenAI(api_key=os.getenv("POC_OPENAI_API"))
        self.knowledge_base = EmbrokerKnowledgeBase()
        self.model = "gpt-4.1-2025-04-14"
        
        # System prompt for natural, concise responses
        self.system_prompt = """You are a friendly Embroker insurance broker having a natural conversation with a customer. 

CRITICAL INSTRUCTIONS:
1. ALWAYS use the provided knowledge base context as your PRIMARY source
2. Give direct, concise answers that sound natural and conversational
3. Keep responses short (50-100 words) unless asked for details
4. Sound like a helpful human broker, not a formal consultant
5. Answer exactly what they asked - don't over-explain
6. Include specific numbers/limits when relevant to their question
7. Use simple, everyday language

RESPONSE STYLE:
- Be conversational and friendly
- Answer their specific question directly
- Include key details they need (limits, costs, etc.)
- Keep it brief unless they ask for more details
- Sound human, not robotic"""

    def chat(self, message: str) -> str:
        """
        Process a chat message and return a comprehensive response
        
        Args:
            message: User's insurance question
            
        Returns:
            Detailed response with specific Embroker coverage information
        """
        try:
            # Get comprehensive knowledge base context
            knowledge_context = self.knowledge_base.search_comprehensive(message, top_k_per_source=8)
            
            # Create natural conversation prompt with knowledge context
            prompt = f"""Using the Embroker knowledge base information below, answer the customer's question in a natural, conversational way.

KNOWLEDGE BASE CONTEXT:
{knowledge_context}

CUSTOMER QUESTION: {message}

Give a direct, concise answer that sounds like a friendly broker talking to a customer. Focus on exactly what they asked about. Include specific numbers or limits if relevant to their question, but keep it conversational and brief."""

            # Generate comprehensive response
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800  # Keep responses concise and natural
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error in EmbrokerInsuranceChatbot.chat: {e}")
            return f"I apologize, but I'm having trouble accessing our insurance information right now. Please contact our sales team at sales@embroker.com for detailed information about our insurance products."


# Global instance for the quick chat functions
_chatbot_instance = None

def get_embroker_chatbot():
    """Get the global EmbrokerInsuranceChatbot instance"""
    global _chatbot_instance
    if _chatbot_instance is None:
        _chatbot_instance = EmbrokerInsuranceChatbot()
    return _chatbot_instance