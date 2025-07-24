"""
Web Search Integration for Insurance Chatbot
Provides real-time web search capabilities using OpenAI's web search tool
"""

import os
import logging
import openai
from typing import Dict, List, Any, Optional
import concurrent.futures

class WebSearchAgent:
    """Web search agent for real-time information retrieval"""
    
    def __init__(self):
        """Initialize web search agent"""
        # Use same API key as main agent (POC_OPENAI_API) with fallback
        api_key = os.getenv("POC_OPENAI_API") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not found (neither POC_OPENAI_API nor OPENAI_API_KEY)")
        self.client = openai.OpenAI(api_key=api_key)
        logging.info("[WebSearch] Web search agent initialized")
    
    def search_web(self, query: str, context_size: str = "medium", user_location: Optional[Dict] = None) -> str:
        """
        Search the web for real-time information
        
        Args:
            query: Search query
            context_size: "low", "medium", or "high" - controls cost vs quality
            user_location: Optional location context for geographical relevance
            
        Returns:
            Search results with citations
        """
        try:
            logging.info(f"[WebSearch] Starting web search for: {query}")
            
            # Configure web search tool
            tools = [{
                "type": "web_search_preview",
                "search_context_size": context_size
            }]
            
            # Add user location if provided
            if user_location:
                tools[0]["user_location"] = user_location
            
            def call_web_search():
                response = self.client.responses.create(
                    model="gpt-4.1",
                    tools=tools,
                    input=query,
                    text={
                        "format": {
                            "type": "text"
                        }
                    }
                )
                return response
            
            # Execute with timeout
            response = None
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(call_web_search)
                    response = future.result(timeout=10)  # 10 second timeout for web search
            except concurrent.futures.TimeoutError:
                logging.error("[WebSearch] Web search timed out after 10 seconds")
                return "Web search timed out. Please try again with a more specific query."
            except Exception as e:
                logging.error(f"[WebSearch] Web search failed: {str(e)}")
                return f"Web search encountered an error: {str(e)}"
            
            # Extract results from response
            if response and hasattr(response, 'output') and response.output:
                for output_item in response.output:
                    if hasattr(output_item, 'type') and output_item.type == "message":
                        if hasattr(output_item, 'content') and output_item.content:
                            for content_item in output_item.content:
                                if hasattr(content_item, 'text'):
                                    # Include citation information
                                    result = content_item.text
                                    if hasattr(content_item, 'annotations') and content_item.annotations:
                                        result += "\n\nSources:"
                                        for annotation in content_item.annotations:
                                            if hasattr(annotation, 'url') and hasattr(annotation, 'title'):
                                                result += f"\n- {annotation.title}: {annotation.url}"
                                    return result
            
            return "No web search results found for your query."
            
        except Exception as e:
            logging.error(f"[WebSearch] Error in web search: {str(e)}", exc_info=True)
            return f"Web search error: {str(e)}"
    
    def should_use_web_search(self, query: str) -> bool:
        """
        Determine if a query should use web search based on content analysis
        
        Args:
            query: User query to analyze
            
        Returns:
            True if web search is recommended
        """
        # Keywords that suggest need for real-time information
        real_time_keywords = [
            "latest", "recent", "current", "today", "news", "update", "now",
            "2025", "this year", "trending", "breaking", "new", "announce"
        ]
        
        # Industry-specific real-time queries
        insurance_real_time = [
            "market trends", "regulatory changes", "new laws", "industry news",
            "company acquisition", "merger", "regulatory update", "compliance change"
        ]
        
        query_lower = query.lower()
        
        # Check for real-time indicators
        for keyword in real_time_keywords + insurance_real_time:
            if keyword in query_lower:
                return True
        
        # Check for specific date references
        if any(term in query_lower for term in ["2025", "this month", "this week"]):
            return True
            
        return False
    
    def search_insurance_news(self, topic: str = "insurance industry") -> str:
        """
        Search for latest insurance industry news and updates
        
        Args:
            topic: Specific insurance topic to search for
            
        Returns:
            Latest news results
        """
        query = f"latest {topic} news 2025 updates regulatory changes"
        return self.search_web(query, context_size="medium")
    
    def search_company_news(self, company_name: str) -> str:
        """
        Search for latest news about a specific company
        
        Args:
            company_name: Name of the company to search for
            
        Returns:
            Company news results
        """
        query = f"{company_name} company news 2025 latest updates financial insurance"
        return self.search_web(query, context_size="low")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get web search system status"""
        return {
            "web_search_available": True,
            "api_key_configured": bool(os.getenv("POC_OPENAI_API") or os.getenv("OPENAI_API_KEY")),
            "default_context_size": "medium",
            "timeout_seconds": 10
        }

# Global web search agent instance
web_search_agent = None

def get_web_search_agent():
    """Get or create the global web search agent instance"""
    global web_search_agent
    if web_search_agent is None:
        web_search_agent = WebSearchAgent()
    return web_search_agent

def search_web_information(query: str, context_size: str = "medium") -> str:
    """
    Main entry point for web search functionality
    
    Args:
        query: Search query
        context_size: Search context size (low/medium/high)
        
    Returns:
        Web search results
    """
    agent = get_web_search_agent()
    return agent.search_web(query, context_size)

def should_use_web_search(query: str) -> bool:
    """Check if query should use web search"""
    agent = get_web_search_agent()
    return agent.should_use_web_search(query)