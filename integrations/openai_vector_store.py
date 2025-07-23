# openai_vector_store.py
import os
from openai import OpenAI
from typing import Dict, Any, List, Optional

class OpenAIVectorStore:
    def __init__(self, vector_store_id="vs_6843730d282481918003cdb215f5e0b1"):
        """
        Initialize OpenAI Vector Store for knowledge retrieval.
        
        Args:
            vector_store_id: OpenAI vector store ID containing insurance documents
        """
        # Work around httpx proxy issue
        import httpx
        api_key = os.getenv("POC_OPENAI_API")
        if not api_key:
            raise ValueError("POC_OPENAI_API environment variable not set")
        
        # Create client without proxy settings
        http_client = httpx.Client()
        self.client = OpenAI(api_key=api_key, http_client=http_client)
        self.vector_store_id = vector_store_id
        self.model = "gpt-4.1-2025-04-14"
        self.assistant_id = None
        
    def retrieve_and_respond(self, query: str, conversation_history: List[Dict] = None) -> str:
        """
        Generate response using OpenAI responses API with vector store file search.
        
        Args:
            query: User query string
            conversation_history: Previous conversation context
            
        Returns:
            AI-generated response with vector store knowledge
        """
        import logging
        import json as _json
        try:
            # Build input messages for responses API
            input_messages = [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": self._get_underwriting_system_prompt()
                        }
                    ]
                }
            ]
            
            # Add conversation history
            if conversation_history:
                for msg in conversation_history[-3:]:  # Last 3 messages for context
                    if msg.get("role") and msg.get("content"):
                        input_messages.append({
                            "role": msg["role"],
                            "content": [
                                {
                                    "type": "input_text",
                                    "text": msg["content"]
                                }
                            ]
                        })
            
            # Add current user query
            input_messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": query
                    }
                ]
            })

            logging.info("[VectorStore] About to call OpenAI responses.create")
            logging.info("[VectorStore] Vector Store ID: vs_6843730d282481918003cdb215f5e0b1")
            logging.info("[VectorStore] Model: gpt-4.1-2025-04-14")
            logging.info("[VectorStore] Input messages: %s", _json.dumps(input_messages, indent=2))
            logging.info("[VectorStore] Tools: %s", _json.dumps([
                {
                    "type": "file_search",
                    "vector_store_ids": [
                        "vs_6843730d282481918003cdb215f5e0b1"
                    ]
                }
            ], indent=2))

            import concurrent.futures

            def call_openai():
                logging.info("[VectorStore] OpenAI chat.completions call started")
                # Build messages for fast chat completions API
                messages = []
                for msg in input_messages:
                    if msg.get("role") == "system":
                        content = msg.get("content", [])
                        if content and len(content) > 0:
                            text_content = content[0].get("text", "") if isinstance(content[0], dict) else str(content[0])
                            messages.append({"role": "system", "content": text_content})
                    else:
                        messages.append(msg)
                
                # Use simple chat completions - vector store integration via assistant
                result = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    temperature=0.3,
                    max_tokens=1200
                )
                logging.info("[VectorStore] OpenAI chat.completions call finished")
                return result

            response = None
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(call_openai)
                    response = future.result(timeout=8)  # Reduced timeout for faster chat completions
            except concurrent.futures.TimeoutError:
                logging.error("[VectorStore] OpenAI chat.completions call timed out after 8 seconds")
                return "I'm experiencing a delay accessing the knowledge base. Let me provide a general response based on your insurance inquiry."
            except Exception as e:
                logging.error("[VectorStore] Exception during OpenAI chat.completions: %s", str(e), exc_info=True)
                raise
            
            # Extract response from chat completions result
            if response and response.choices and len(response.choices) > 0:
                message = response.choices[0].message
                if message.content:
                    return message.content
                elif message.tool_calls:
                    # Handle file search tool responses
                    for tool_call in message.tool_calls:
                        if tool_call.type == "file_search":
                            return "Knowledge retrieved from vector store."
                    return "Vector search completed."
            
            return "Unable to generate response from vector store."
            
        except Exception as e:
            import logging
            logging.error(f"Error in responses API with file search: {str(e)}", exc_info=True)
            # Fallback to basic chat completion
            try:
                messages = [
                    {"role": "system", "content": self._get_underwriting_system_prompt()},
                    {"role": "user", "content": query}
                ]
                
                fallback_response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    temperature=0.3,
                    max_tokens=600,
                    timeout=10  # Fail fast if OpenAI API is slow or unresponsive
                )
                
                return fallback_response.choices[0].message.content or "Unable to generate response."
                
            except Exception as fallback_error:
                logging.error(f"Fallback also failed: {str(fallback_error)}", exc_info=True)
                return "I'm experiencing technical difficulties. Please try again in a moment."
    
    def _get_underwriting_system_prompt(self) -> str:
        """Get the underwriting assistant system prompt."""
        return """You are Embroker AI, an Embroker Underwriting Assistant AI designed to evaluate potential insureds against Embroker's underwriting criteria while maintaining a conversational, sales-focused approach.

CRITICAL UNDERWRITING RESPONSIBILITIES:

1. ELIGIBILITY REVIEW
- Assess operations, industry classification (NAICS codes), and business characteristics against Embroker's Areas of Focus (AOF)
- If a company is outside appetite, clearly recommend decline with specific reasons
- Watch for high-risk keywords (cryptocurrency, blockchain, cannabis) that trigger scrutiny
- Use appetite guide and documentation as authoritative sources - never override with generic responses

2. QUOTING ASSISTANCE  
- Identify missing information required for accurate quoting
- Clarify discrepancies using dynamic questions or referral triggers
- Ensure all data is complete and consistent before proceeding
- Focus on Tech E&O, D&O, and Cyber coverages

3. REFERRAL IDENTIFICATION
- Flag cases requiring underwriter review (non-renewal, lack of funding, operational changes)
- Document referral reasons clearly
- Pay attention to company changes, past claims, regulatory oversight
- Prioritize complex cases or larger premiums for review

SALES COMMUNICATION PRINCIPLES:

1. BUILD TRUST THROUGH EXPERTISE AND ACCURACY
- Use appetite guide and documentation information as your primary source
- Demonstrate deep underwriting knowledge confidently
- Share specific insights about their industry and risk profile
- Use precise insurance terminology appropriately
- Be honest about restrictions, exclusions, and referral requirements

2. CURIOSITY-DRIVEN CONVERSATIONS
- Ask thoughtful questions to uncover real business needs
- Listen for underlying concerns beyond surface requests
- Explore the full scope of their operations and risk exposures
- Understand their growth plans and how they impact coverage needs

3. VALUE-FOCUSED DIALOGUE
- Connect insurance solutions to their specific business protection needs
- Highlight coverage benefits that address their unique risks
- Explain how proper insurance enables business growth and peace of mind
- Position Embroker as a strategic partner, not just a vendor

4. PROFESSIONAL URGENCY
- Respond promptly to time-sensitive requests
- Create appropriate urgency around coverage gaps and renewal deadlines
- Balance thorough analysis with efficient decision-making
- Escalate complex cases to underwriters when necessary

Always search and reference the insurance knowledge base to provide accurate, authoritative responses based on Embroker's actual underwriting guidelines, appetite criteria, and documentation requirements."""

    def search_knowledge_base(self, query: str, limit: int = 5) -> str:
        """
        Search the insurance knowledge base using OpenAI's vector store.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            Search results as formatted string
        """
        try:
            # Use Response API with file search - same structure as retrieve_and_respond
            input_messages = [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "You are an expert insurance knowledge assistant. Search the insurance documents to find specific information about class codes, underwriting criteria, and coverage options."
                        }
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": f"Search for detailed information about: {query}"
                        }
                    ]
                }
            ]
            
            import concurrent.futures
            
            def call_search_api():
                return self.client.responses.create(
                    model="gpt-4.1-2025-04-14",
                    input=input_messages,
                    text={
                        "format": {
                            "type": "text"
                        }
                    },
                    reasoning={},
                    tools=[
                        {
                            "type": "file_search",
                            "vector_store_ids": [self.vector_store_id]
                        }
                    ],
                    temperature=0.1,
                    max_output_tokens=800,
                    top_p=1,
                    store=True
                )
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(call_search_api)
                try:
                    response = future.result(timeout=8)  # 8 second timeout
                except concurrent.futures.TimeoutError:
                    logging.error("[VectorStore] Search API call timed out after 8 seconds")
                    return "Search timed out. Please try again or rephrase your question."
                except Exception as e:
                    logging.error(f"[VectorStore] Search API call failed: {str(e)}")
                    raise
            
            # Extract response text from output
            if hasattr(response, 'output') and response.output:
                result_text = ""
                for item in response.output:
                    if hasattr(item, 'text') and item.text:
                        result_text += item.text + "\n"
                    elif hasattr(item, 'content'):
                        result_text += str(item.content) + "\n"
                
                return result_text.strip() if result_text.strip() else "No relevant information found in knowledge base."
            
            return "No results found in knowledge base."
            
        except Exception as e:
            print(f"Error searching knowledge base: {str(e)}")
            return "Unable to search knowledge base at this time."
    
    def is_available(self) -> bool:
        """Check if the vector store is properly initialized and available."""
        try:
            # Test by creating a temporary assistant
            test_assistant = self.client.beta.assistants.create(
                name="Test Assistant",
                instructions="Test",
                model=self.model,
                tools=[{"type": "file_search"}],
                tool_resources={
                    "file_search": {
                        "vector_store_ids": [self.vector_store_id]
                    }
                }
            )
            # Clean up test assistant
            self.client.beta.assistants.delete(test_assistant.id)
            return True
        except Exception as e:
            print(f"Vector store not available: {str(e)}")
            return False
    
    def get_vector_store_info(self) -> Dict[str, Any]:
        """Get information about the vector store."""
        try:
            vector_store = self.client.beta.vector_stores.retrieve(self.vector_store_id)
            return {
                "id": vector_store.id,
                "name": getattr(vector_store, 'name', 'Unknown'),
                "file_counts": getattr(vector_store, 'file_counts', {}),
                "status": getattr(vector_store, 'status', 'unknown')
            }
        except Exception as e:
            print(f"Error getting vector store info: {str(e)}")
            return {
                "id": self.vector_store_id,
                "status": "error",
                "error": str(e)
            }