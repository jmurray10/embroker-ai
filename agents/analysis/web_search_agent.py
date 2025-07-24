# web_search_agent.py
"""
Web Search Analysis Agent - Handles real-time web search for current events and market trends
"""

import os
from typing import Optional, Dict, Any
from integrations.web_search import WebSearchAgent as WebSearchIntegration

class WebSearchAnalysisAgent:
    """
    Dedicated agent for web search operations within the analysis category.
    Provides real-time information retrieval for insurance market trends, 
    regulatory updates, and current events.
    """
    
    def __init__(self):
        """Initialize the web search analysis agent with API key."""
        self.api_key = os.environ.get('POC_OPENAI_API') or os.environ.get('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not found in environment variables")
        
        # Initialize the underlying web search integration
        self.search_client = WebSearchIntegration()
        
    def search_current_events(self, query: str) -> Dict[str, Any]:
        """
        Search for current events, news, and real-time information.
        
        Args:
            query: Search query for current events
            
        Returns:
            Dict containing search results with citations and sources
        """
        try:
            # Add context to ensure we get current information
            enhanced_query = f"{query} (current 2025)"
            results = self.search_client.search_web(enhanced_query)
            
            return {
                "success": True,
                "results": results,
                "query": query
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
    
    def search_insurance_trends(self, topic: str) -> Dict[str, Any]:
        """
        Search for insurance industry trends and market updates.
        
        Args:
            topic: Specific insurance topic to research
            
        Returns:
            Dict containing trend analysis and market insights
        """
        try:
            # Enhance query for insurance-specific context
            query = f"insurance industry {topic} trends 2025 market analysis"
            results = self.search_client.search_web(query)
            
            return {
                "success": True,
                "topic": topic,
                "trends": results,
                "timestamp": "2025"
            }
        except Exception as e:
            return {
                "success": False,
                "topic": topic,
                "error": str(e)
            }
    
    def search_regulatory_updates(self, regulation_type: str = "insurance") -> Dict[str, Any]:
        """
        Search for recent regulatory updates and compliance changes.
        
        Args:
            regulation_type: Type of regulations to search for
            
        Returns:
            Dict containing regulatory updates and compliance information
        """
        try:
            query = f"{regulation_type} regulatory updates compliance changes 2025"
            results = self.search_client.search_web(query)
            
            return {
                "success": True,
                "regulation_type": regulation_type,
                "updates": results,
                "compliance_required": True
            }
        except Exception as e:
            return {
                "success": False,
                "regulation_type": regulation_type,
                "error": str(e)
            }
    
    def search_company_news(self, company_name: str) -> Dict[str, Any]:
        """
        Search for recent news and updates about a specific company.
        
        Args:
            company_name: Name of the company to research
            
        Returns:
            Dict containing company news and recent developments
        """
        try:
            query = f"{company_name} news announcements developments 2025"
            results = self.search_client.search_web(query)
            
            return {
                "success": True,
                "company": company_name,
                "news": results,
                "recent": True
            }
        except Exception as e:
            return {
                "success": False,
                "company": company_name,
                "error": str(e)
            }

# Singleton instance for easy access
_web_search_agent = None

def get_web_search_agent() -> WebSearchAnalysisAgent:
    """Get or create the singleton web search analysis agent."""
    global _web_search_agent
    if _web_search_agent is None:
        _web_search_agent = WebSearchAnalysisAgent()
    return _web_search_agent