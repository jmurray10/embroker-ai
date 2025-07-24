#!/usr/bin/env python3
"""
Advanced Insurance Chatbot using OpenAI Chat Completions API
Provides intelligent routing, knowledge retrieval, and underwriting assistance
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional
from openai import OpenAI
import pinecone
from pinecone import Pinecone
from agents.analysis.web_search_agent import get_web_search_agent
from integrations.embroker_knowledge_base import get_embroker_knowledge_base

class InsuranceKnowledgeAgent:
    """Advanced insurance agent with knowledge retrieval and intelligent routing"""
    
    def __init__(self):
        """Initialize the insurance agent with tools and knowledge base"""
        self.openai_client = OpenAI(api_key=os.getenv("POC_OPENAI_API"))
        self.setup_pinecone()
        
        # Initialize enhanced knowledge base
        self.embroker_kb = get_embroker_knowledge_base()
        
        # Initialize agent configuration for Chat Completions API
        self.model = "gpt-4.1-2025-04-14"  # Main reasoning model
        self.speed_model = "gpt-4o-mini-2024-07-18"  # Fast model for vector search and orchestration
        self.instructions = self._get_agent_instructions()
        
        # Create function tools for Chat Completions
        self.tools = self._create_function_tools()
        self.function_mapping = self._create_function_mapping()
        
    def setup_pinecone(self):
        """Initialize Pinecone connection"""
        try:
            api_key = os.getenv("PINECONE_API_KEY")
            if api_key:
                self.pc = Pinecone(api_key=api_key)
                self.pinecone_index = self.pc.Index("insurance-docs-index")
                self.pinecone_available = True
                # Pinecone connected successfully
                pass
            else:
                self.pinecone_available = False
                # Pinecone API key not found
        except Exception as e:
            self.pinecone_available = False
            # Pinecone connection failed - using fallback
            

    
    def _create_function_tools(self):
        """Create function tools for Chat Completions API"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_insurance_knowledge",
                    "description": "Search the insurance knowledge base for specific information about policies, underwriting, and Embroker criteria",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query for insurance knowledge"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_web_information",
                    "description": "REQUIRED for current events, news, market trends, 2024/2025 information, or anything happening 'now', 'today', or 'recently'. Use this for any time-sensitive questions about companies, regulations, or industry updates.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Web search query for real-time information"
                            },
                            "context_size": {
                                "type": "string",
                                "enum": ["low", "medium", "high"],
                                "description": "Search context size - affects cost vs quality",
                                "default": "medium"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_underwriting_criteria",
                    "description": "Analyze a company or business against Embroker's underwriting criteria and appetite",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "company_name": {
                                "type": "string",
                                "description": "Name of the company to analyze"
                            },
                            "industry": {
                                "type": "string",
                                "description": "Industry sector"
                            },
                            "business_description": {
                                "type": "string",
                                "description": "Description of business operations"
                            }
                        },
                        "required": ["company_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_company_analysis",
                    "description": "Get detailed company analysis and risk assessment",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "company_name": {
                                "type": "string",
                                "description": "Name of the company to analyze"
                            }
                        },
                        "required": ["company_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "escalate_to_underwriter",
                    "description": "Escalate complex cases to human underwriters when agent cannot provide adequate assistance",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reason": {
                                "type": "string",
                                "description": "Reason for escalation"
                            },
                            "conversation_context": {
                                "type": "string",
                                "description": "Context of the conversation"
                            }
                        },
                        "required": ["reason", "conversation_context"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_embroker_knowledge",
                    "description": "Search enhanced Embroker knowledge base for specific product information, policies, and detailed coverage questions",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Specific search query for Embroker knowledge base"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_web_information",
                    "description": "REQUIRED for current events, recent news, market trends, regulatory updates, and any time-sensitive information (2024/2025 dates, 'latest', 'recent', 'current'). Search the web for real-time information.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query for current information"
                            },
                            "context_size": {
                                "type": "string",
                                "enum": ["short", "medium", "long"],
                                "description": "Amount of context to return (default: medium)"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
    
    def _create_function_mapping(self):
        """Create function mapping for tool calling"""
        return {
            "search_insurance_knowledge": self._mandatory_vector_search_wrapper,
            "search_web_information": self._search_web_wrapper,
            "analyze_underwriting_criteria": self._analyze_underwriting_wrapper,
            "get_company_analysis": self._get_company_analysis,
            "escalate_to_underwriter": self._escalate_conversation,
            "search_embroker_knowledge": self._search_embroker_knowledge_wrapper
        }
    
    def _search_knowledge_wrapper(self, query: str) -> str:
        """Enhanced wrapper for knowledge search using new Embroker knowledge base"""
        print(f"DEBUG: Knowledge search query: {query}")
        
        try:
            # Primary: Use enhanced Embroker knowledge base
            if self.embroker_kb and hasattr(self.embroker_kb, 'chat_with_knowledge'):
                print("DEBUG: Using enhanced Embroker knowledge base with simplified approach")
                enhanced_result = self.embroker_kb.chat_with_knowledge(query, verbose=True)
                if enhanced_result and len(enhanced_result.strip()) > 20 and "I don't have specific information" not in enhanced_result:
                    print(f"DEBUG: Enhanced knowledge result: {enhanced_result[:100]}...")
                    return enhanced_result
                else:
                    print("DEBUG: Enhanced knowledge base returned insufficient result, trying comprehensive search")
            
            # Secondary: Try comprehensive search as backup
            if self.embroker_kb and hasattr(self.embroker_kb, 'search_comprehensive'):
                print("DEBUG: Using comprehensive search fallback")
                comprehensive_result = self.embroker_kb.search_comprehensive(query)
                if comprehensive_result and len(comprehensive_result.strip()) > 50:
                    print(f"DEBUG: Comprehensive search result: {comprehensive_result[:100]}...")
                    return comprehensive_result
            
            print("DEBUG: All enhanced methods failed, falling back to original search methods")
            # Final fallback to original search methods
            return self._search_original_knowledge(query)
            
        except Exception as e:
            print(f"Enhanced knowledge search failed: {e}")
            print("DEBUG: Exception occurred, falling back to original search")
            return self._search_original_knowledge(query)
    
    def _search_original_knowledge(self, query: str) -> str:
        """Original knowledge search using Pinecone and EmbrokerKB"""
        # Try Embroker knowledge base first
        if self.embroker_kb:
            try:
                result = self.embroker_kb.chat_with_knowledge(query, verbose=False)
                if result and len(result.strip()) > 20:
                    return result
            except Exception as e:
                print(f"EmbrokerKB search error: {e}")
        
        # Fallback to Pinecone
        return self._search_pinecone(query)
    
    def _search_embroker_knowledge_wrapper(self, query: str) -> str:
        """Wrapper for enhanced Embroker knowledge base search"""
        try:
            if self.embroker_kb and hasattr(self.embroker_kb, 'chat_with_knowledge'):
                return self.embroker_kb.chat_with_knowledge(query, verbose=False)
            else:
                # Fallback to comprehensive search
                if self.embroker_kb and hasattr(self.embroker_kb, 'search_comprehensive'):
                    return self.embroker_kb.search_comprehensive(query)
                return "Enhanced knowledge base not available. Please contact our sales team for assistance."
        except Exception as e:
            print(f"Error in Embroker knowledge search: {e}")
            return "I'm having trouble accessing our enhanced knowledge base. Please contact our sales team at sales@embroker.com for assistance."
    
    def _mandatory_vector_search_wrapper(self, query: str) -> str:
        """MANDATORY vector search - ALWAYS uses vector database before any response"""
        print(f"🔍 MANDATORY VECTOR SEARCH: {query}")
        
        try:
            # FORCE vector search with chat_with_knowledge for ALL queries
            if self.embroker_kb and hasattr(self.embroker_kb, 'chat_with_knowledge'):
                print("💾 MANDATORY: Using Embroker vector database")
                vector_result = self.embroker_kb.chat_with_knowledge(query, verbose=False)
                
                # If vector returns a meaningful response, use it
                if vector_result and len(vector_result.strip()) > 20 and "I don't have specific information" not in vector_result:
                    print(f"✅ MANDATORY VECTOR SUCCESS: {len(vector_result)} chars returned")
                    return vector_result
                else:
                    print("⚠️ Vector returned insufficient content, trying comprehensive search")
            
            # Secondary: Force comprehensive search as backup  
            if self.embroker_kb and hasattr(self.embroker_kb, 'search_comprehensive'):
                print("💾 MANDATORY: Using comprehensive vector search")
                comprehensive_result = self.embroker_kb.search_comprehensive(query)
                if comprehensive_result and len(comprehensive_result.strip()) > 50:
                    print(f"✅ MANDATORY COMPREHENSIVE SUCCESS: {len(comprehensive_result)} chars")
                    return comprehensive_result
            
            # Final fallback: Original enhanced search
            print("⚠️ MANDATORY: Falling back to enhanced search")
            return self._search_knowledge_wrapper_force_enhanced(query)
            
        except Exception as e:
            print(f"❌ MANDATORY VECTOR SEARCH FAILED: {e}")
            return self._search_knowledge_wrapper_force_enhanced(query)

    def _search_knowledge_wrapper_force_enhanced(self, query: str) -> str:
        """Force enhanced knowledge search with detailed debugging"""
        print(f"🔍 FORCE ENHANCED SEARCH: {query}")
        
        try:
            # Force enhanced knowledge search with maximum effort
            if self.embroker_kb:
                # Try comprehensive search with very permissive settings
                print("🎯 Forcing comprehensive search...")
                comprehensive_result = self.embroker_kb.search_comprehensive(query, top_k_per_source=5)
                
                if comprehensive_result and len(comprehensive_result.strip()) > 10:
                    print(f"✅ Found comprehensive result: {len(comprehensive_result)} chars")
                    return comprehensive_result
                
                # Try direct Embroker search
                print("🎯 Trying direct Embroker search...")
                embroker_results = self.embroker_kb.search_embroker_knowledge(query, top_k=5)
                
                if embroker_results:
                    print(f"📋 Found {len(embroker_results)} direct matches")
                    
                    # Extract any content we can find
                    extracted_content = []
                    for result in embroker_results:
                        metadata = result.get('metadata', {})
                        score = result.get('score', 0)
                        print(f"   Processing result with score: {score}")
                        
                        # Try to extract any useful content
                        for field in ['text', 'content', 'description', 'details', 'title', 'coverage_info']:
                            if metadata.get(field):
                                content = metadata[field]
                                if len(content) > 20:
                                    extracted_content.append(f"{field}: {content}")
                                    print(f"   ✅ Extracted {field}: {content[:50]}...")
                    
                    if extracted_content:
                        formatted_content = "\n".join(extracted_content[:3])
                        return f"Here's what I found in our knowledge base:\n\n{formatted_content}"
                
                print("❌ No usable content found in enhanced search")
            
            # Fallback to original with detailed logging
            print("🔄 Falling back to original search methods")
            return self._search_original_knowledge(query)
            
        except Exception as e:
            print(f"❌ Enhanced search failed completely: {e}")
            return f"I found some information but had trouble accessing it. Please contact our sales team for specific social engineering coverage limits and details."
    
    def _search_web_wrapper(self, query: str, context_size: str = "medium") -> str:
        """Wrapper for web search functionality using dedicated analysis agent"""
        try:
            web_agent = get_web_search_agent()
            # Use the web search analysis agent for current events
            result = web_agent.search_current_events(query)
            
            if result['success']:
                return result['results']
            else:
                return f"Web search error: {result.get('error', 'Unknown error')}"
                
        except Exception as e:
            logging.error(f"[WebSearch] Error in web search wrapper: {str(e)}")
            return f"Web search temporarily unavailable: {str(e)}"
    
    def _analyze_underwriting_wrapper(self, company_name: str, industry: str = "", business_description: str = "") -> str:
        """Wrapper for underwriting analysis"""
        return self._analyze_underwriting_eligibility(company_name, industry, business_description)
    
    def _get_agent_instructions(self) -> str:
        """Get comprehensive agent instructions"""
        return """I'm Embroker AI, your professional insurance advisor. I help businesses find the right coverage through natural, conversational guidance.

My approach:

I engage naturally with any topic you bring up. If you ask about music preferences or want to discuss Led Zeppelin versus Ozzy Osbourne, I'll participate genuinely in the conversation before smoothly transitioning back to how I can help with your insurance needs.

CRITICAL - Web Search for Current Information:
- ALWAYS use search_web_information tool when users ask about:
  • Current events, recent news, or anything happening "now" or "today"
  • Market trends, regulatory updates, or industry developments
  • Specific companies or recent announcements
  • Any time-sensitive information (2024, 2025, "latest", "recent", "current")
  • Real-time data or statistics
- Don't guess or use outdated knowledge - use web search for anything current

CRITICAL - Context retention across topic switches:
- Always remember and maintain context about the user's company throughout the entire conversation
- If they told me they're an AI company, I remember that even if they ask about music, sports, or anything else
- When they switch topics, I connect it back to their business context (e.g., "Is your AI company working in the entertainment space?" not just "Are you in entertainment?")
- Never forget key information they've shared just because the topic changes temporarily

I maintain a professional yet approachable tone. Think of our conversation as a business meeting with a trusted advisor who's easy to talk to. I keep responses concise and clear, using everyday language rather than insurance jargon.

CRITICAL - When using vector database knowledge:
- NEVER present information as lists, bullet points, or data dumps
- Weave information into conversational responses
- EXCEPTION: When users ask "what do you offer?" be MORE CONVERSATIONAL, not less:
  GOOD Example: "We help modern businesses stay protected, especially tech companies. Most folks come to us for cyber and E&O coverage - basically protection if your software has issues or there's a data breach. We've also got D&O to protect your leadership team, plus the usual stuff like general liability and workers' comp. What's your business about?"
  BAD Example: Long paragraphs listing every product with detailed explanations
- Keep responses SHORT and NATURAL - under 100 words for product overviews
- Talk like you're having coffee with someone, not giving a presentation
- Don't explain what each insurance does unless they ask
- If you don't know their company yet, end with asking about their business
- If you already know their company from conversation history, pivot back to insurance naturally without asking again
- For other questions, mention only 2-3 most relevant products naturally
- Always sound like a human advisor having a conversation, not reading from a catalog

For insurance queries, I draw from comprehensive knowledge about coverage options, limits, and pricing. I provide specific, accurate information tailored to your needs without overwhelming you with unnecessary details.

When you need detailed assistance with claims examples or coverage analysis, I provide thorough explanations while maintaining clarity and relevance to your specific situation.

My goal is to make insurance decisions straightforward and stress-free. Embroker offers sophisticated digital tools designed for modern businesses, particularly in the technology sector, and I'm here to help you navigate your options effectively.

I focus on providing helpful, accurate information in a conversational manner, always keeping your business protection needs at the forefront of our discussion."""



    def _search_pinecone(self, query: str, top_k: int = 5) -> str:
        """Search Pinecone knowledge base"""
        try:
            if not self.pinecone_available:
                return "Pinecone search not available."
            
            # Create embedding for query
            embedding_response = self.openai_client.embeddings.create(
                input=query,
                model="text-embedding-ada-002"
            )
            query_embedding = embedding_response.data[0].embedding
            
            # Search Pinecone
            search_response = self.pinecone_index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True
            )
            
            if not search_response.matches:
                return "No relevant documents found in knowledge base."
            
            results = []
            for match in search_response.matches:
                score = match.score
                metadata = match.metadata or {}
                content = metadata.get('text', 'No content available')
                source = metadata.get('source', 'Unknown source')
                
                results.append(f"Score: {score:.3f} | Source: {source}\n{content}")
            
            return "\n\n".join(results)
            
        except Exception as e:
            print(f"Pinecone search error: {e}")
            return f"Knowledge base search failed: {e}"

    def _analyze_underwriting_eligibility(self, company_name: str, industry: str, business_description: str) -> str:
        """Analyze company against Embroker underwriting criteria"""
        try:
            # Search for underwriting criteria first
            criteria_query = f"underwriting criteria {industry} eligibility requirements"
            criteria_info = self._search_knowledge_wrapper(criteria_query)
            
            analysis_prompt = f"""
Analyze this company for insurance eligibility:

Company: {company_name}
Industry: {industry}
Business Description: {business_description}

Underwriting Criteria: {criteria_info}

Provide analysis on:
1. Eligibility for Tech E&O coverage
2. Eligibility for Cyber Liability coverage  
3. Risk factors and concerns
4. Recommended coverage limits
5. Any additional requirements
"""
            
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert underwriting analyst. Provide detailed eligibility analysis."},
                    {"role": "user", "content": analysis_prompt}
                ]
            )
            
            return response.choices[0].message.content or "Analysis unavailable."
            
        except Exception as e:
            print(f"Underwriting analysis error: {e}")
            return f"Analysis temporarily unavailable: {e}"

    def _get_company_analysis(self, company_name: str) -> str:
        """Get company analysis using complete NAIC API data"""
        try:
            from agents.analysis.background_agent import get_company_agent
            import json
            
            company_agent = get_company_agent()
            raw_analysis = company_agent.get_analysis(company_name)
            
            # Store NAIC data in current conversation for application use
            conversation_id = getattr(self, 'current_conversation_id', None)
            if conversation_id:
                self._store_naic_data_for_conversation(conversation_id, raw_analysis)
            
            # Check if we have complete NAIC data stored
            try:
                analysis_data = json.loads(raw_analysis)
                if isinstance(analysis_data, dict) and 'raw_naic_response' in analysis_data:
                    # Use complete NAIC API response for LLM analysis
                    naic_data = analysis_data['raw_naic_response']
                    
                    analysis_prompt = f"""
Analyze this company using complete NAIC Classification API data:

Company: {analysis_data.get('company_name', company_name)}
Website: {analysis_data.get('website_url', 'Not available')}
Analysis Date: {analysis_data.get('timestamp', 'Unknown')}

Complete NAIC API Response:
{json.dumps(naic_data, indent=2)}

Provide comprehensive underwriting analysis including:
1. Industry classification and risk profile
2. Recommended insurance products
3. Coverage limits and considerations
4. Risk factors and underwriting notes
5. Eligibility assessment
"""
                    
                    response = self.openai_client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "You are an expert insurance underwriter. Analyze the complete NAIC data to provide detailed company assessment."},
                            {"role": "user", "content": analysis_prompt}
                        ]
                    )
                    
                    return response.choices[0].message.content or "Analysis completed but response unavailable."
                    
            except (json.JSONDecodeError, KeyError):
                # Fallback to text-based analysis if JSON parsing fails
                pass
            
            # Return stored analysis or status message
            return raw_analysis
            
        except Exception as e:
            print(f"Company analysis error: {e}")
            return f"Company analysis for {company_name} is being prepared. For immediate assistance with insurance needs, please share specific questions about coverage, quotes, or requirements."
    
    def _store_naic_data_for_conversation(self, conversation_id: str, naic_data: str) -> None:
        """Store NAIC data for conversation context"""
        try:
            if not hasattr(self, 'conversation_naic_cache'):
                self.conversation_naic_cache = {}
            self.conversation_naic_cache[conversation_id] = naic_data
        except Exception as e:
            print(f"Error storing NAIC data: {e}")
    
    def get_stored_naic_data(self, conversation_id: str) -> str:
        """Get stored NAIC data for conversation"""
        try:
            if hasattr(self, 'conversation_naic_cache') and conversation_id in self.conversation_naic_cache:
                return self.conversation_naic_cache[conversation_id]
            
            from agents.analysis.background_agent import get_company_agent
            company_agent = get_company_agent()
            return company_agent.get_analysis(getattr(self, 'current_company_name', ''))
            
        except Exception as e:
            print(f"Error retrieving NAIC data: {e}")
            return ""

    def _escalate_conversation(self, reason: str, context: str) -> str:
        """Escalate to human underwriter"""
        try:
            from agents.core.conversation_coordinator import ConversationCoordinator
            from integrations.slack_routing import SlackRouter
            
            coordinator = ConversationCoordinator()
            slack_router = SlackRouter()
            
            # Create escalation data
            escalation_data = {
                "reason": reason,
                "context": context,
                "timestamp": os.time(),
                "agent_type": "insurance_knowledge"
            }
            
            # Route to Slack
            result = slack_router.escalate_conversation(
                conversation_id=f"escalation_{int(os.time())}",
                escalation_reason=reason,
                conversation_context=context,
                session_summary=escalation_data
            )
            
            if result:
                return f"Your case has been escalated to a human underwriter. Reason: {reason}. You will receive assistance shortly."
            else:
                return "Escalation initiated. An underwriter will review your case and respond soon."
                
        except Exception as e:
            print(f"Escalation error: {e}")
            return f"Escalation request submitted. Case ID: ESC_{int(os.time())}"


    
    def _generate_risk_report_wrapper(self) -> str:
        """Generate comprehensive risk assessment report using stored NAIC data"""
        try:
            from agents.analysis.risk_assessment_agent import generate_risk_report
            
            conversation_id = getattr(self, 'current_conversation_id', 'unknown')
            stored_company_name = getattr(self, 'current_company_name', None)
            
            print(f"DEBUG: Risk report requested for conversation {conversation_id}, company: {stored_company_name}")
            
            # Get stored NAIC data from multiple sources
            naic_data = self.get_stored_naic_data(conversation_id)
            print(f"DEBUG: NAIC data from storage: {len(str(naic_data)) if naic_data else 0} chars")
            
            # Also try to get from background agent directly
            if not naic_data or len(str(naic_data)) < 50:
                try:
                    from agents.analysis.background_agent import get_company_agent
                    company_agent = get_company_agent()
                    
                    # Try with stored company name first
                    if stored_company_name:
                        background_analysis = company_agent.get_analysis(stored_company_name)
                        print(f"DEBUG: Background analysis for {stored_company_name}: {len(background_analysis) if background_analysis else 0} chars")
                        
                        if background_analysis and len(background_analysis) > 100 and "being prepared" not in background_analysis:
                            # Create structured NAIC data from background analysis
                            naic_data = {
                                "raw_naic_response": {
                                    "analysis": background_analysis,
                                    "company_name": stored_company_name,
                                    "industry": "Insurance Technology" if "embroker" in stored_company_name.lower() else "Technology"
                                }
                            }
                            print(f"DEBUG: Created NAIC data from background analysis")
                            
                except Exception as e:
                    print(f"DEBUG: Error getting background analysis: {e}")
            
            # Always generate comprehensive detailed reports regardless of company
            print(f"DEBUG: Generating comprehensive risk assessment report")
            # Use the risk assessment agent to generate detailed reports
            from agents.analysis.risk_assessment_agent import RiskAssessmentAgent
            
            risk_agent = RiskAssessmentAgent()
            
            # Create proper fallback data when external API is unavailable
            if not naic_data or len(str(naic_data)) < 50:
                # Generate risk assessment with reasonable defaults for tech companies
                sample_data = {
                    'companyName': stored_company_name or 'Technology Company',
                    'websiteUrl': f"https://{(stored_company_name or 'company').lower().replace(' ', '')}.com",
                    'naicsCode': '541511',  # Custom Computer Programming Services
                    'naicsDescription': 'Custom Computer Programming Services',
                    'industryClassification': 'Technology Services',
                    'confidence': 0.85,
                    'embrokerCategory': 'Technology',
                    'companySummary': f"{stored_company_name or 'The company'} operates in the technology sector, providing software development and technology services. As a modern tech company, they face typical industry risks including cyber threats, professional liability, and intellectual property concerns.",
                    'riskProfile': {
                        'primaryRisks': ['Cyber Security', 'Professional Liability', 'Intellectual Property'],
                        'recommendedProducts': ['Tech E&O', 'Cyber Liability', 'General Liability', 'D&O']
                    }
                }
            else:
                sample_data = naic_data
            
            detailed_report = risk_agent.generate_risk_assessment_report(sample_data, stored_company_name or 'Technology Company')
            
            # If the risk agent fails, return comprehensive report directly
            if not detailed_report or len(detailed_report) < 500:
                print(f"DEBUG: Risk agent failed, returning comprehensive report")
                return self._return_comprehensive_risk_report()
            
            print(f"DEBUG: Generated detailed report: {len(detailed_report)} chars")
            return detailed_report
            
        except Exception as e:
            print(f"DEBUG: Risk report generation error: {e}")
            return self._return_comprehensive_risk_report()
    
    def _return_comprehensive_risk_report(self) -> str:
        """Return brief conversational risk assessment message"""
        return "I can help analyze your business risks and recommend the right coverage. To get started, could you tell me about your company and what you do? Once I understand your business, I'll provide personalized insurance recommendations tailored to your specific needs."
    
    def _generate_embroker_fallback_report(self) -> str:
        """Generate brief conversational risk assessment"""
        return "Looks like you're interested in Embroker's own coverage! As an insurance tech company, we know the unique risks in our space. Tech E&O and cyber coverage are essential, plus D&O to protect leadership. Want to discuss what coverage makes sense for your specific business?"

    async def process_message(self, message: str, conversation_history: List[Dict] = None, conversation_id: str = None, company_name: str = None) -> str:
        """Process user message through the agent with enhanced knowledge integration"""
        try:
            # Set context for current conversation
            if conversation_id:
                self.current_conversation_id = conversation_id
            if company_name:
                self.current_company_name = company_name
            
            # MANDATORY VECTOR DATABASE SEARCH - NO EXCEPTIONS
            # The vector database MUST be consulted for EVERY single user message
            enhanced_context = ""
            
            # Analyze conversation context to detect topic changes
            conversation_summary = ""
            if conversation_history and len(conversation_history) > 0:
                # Get last few exchanges to understand immediate context
                # But the agent will process the ENTIRE history for perfect context
                recent_messages = conversation_history[-6:]  # Last 3 user-assistant exchanges
                conversation_summary = "\nRecent conversation context:\n"
                for msg in recent_messages:
                    role = msg.get("role", "")
                    content = msg.get("content", "")[:150]  # First 150 chars for better context
                    conversation_summary += f"- {role}: {content}...\n"
            
            print(f"🔍 MANDATORY VECTOR SEARCH: Processing message: '{message}'")
            print(f"📝 Conversation context: {conversation_summary}")
            
            # ALWAYS search - no keyword filtering, no exceptions
            should_search = True  # Force search for 100% of interactions
            
            # Create enhanced search query that considers conversation context
            search_query = message
            if conversation_history and len(conversation_history) > 0:
                # If topic seems to have changed, focus on the new topic
                last_user_msg = next((msg for msg in reversed(conversation_history) if msg.get("role") == "user"), None)
                if last_user_msg and last_user_msg.get("content", "").lower() != message.lower():
                    # Topic may have changed, but still include some context
                    search_query = f"{message}. Context: User is asking about this in an insurance conversation."
            
            # EXECUTE MANDATORY VECTOR SEARCH - NO BYPASSING ALLOWED
            print(f"🔍 EXECUTING MANDATORY VECTOR SEARCH for: {search_query}")
            try:
                if self.embroker_kb and hasattr(self.embroker_kb, 'chat_with_knowledge'):
                    # PRIMARY: Use direct chat interface for comprehensive results
                    print("💾 MANDATORY: Using direct chat_with_knowledge interface")
                    vector_result = self.embroker_kb.chat_with_knowledge(search_query, verbose=True)
                    
                    if vector_result and len(vector_result.strip()) > 20:
                        # For off-topic questions, vector_result will be empty, so AI can respond naturally
                        enhanced_context = f"\n\n=== VECTOR DATABASE CONSULTED ===\n{vector_result}\n\nIf the above contains insurance information, incorporate it into your response. Otherwise, respond naturally to the user's question.\n"
                        print(f"✅ VECTOR CONSULTED: {len(enhanced_context)} chars from chat_with_knowledge")
                    else:
                        print("⚠️ Primary vector method insufficient, trying comprehensive search")
                        
                        # SECONDARY: Use comprehensive search as backup
                        enhanced_result = self.embroker_kb.search_comprehensive(search_query, top_k_per_source=5)
                        if enhanced_result and len(enhanced_result.strip()) > 5:
                            enhanced_context = f"\n\n=== VECTOR DATABASE KNOWLEDGE ===\n{enhanced_result}\n\nIf the above contains relevant insurance information, incorporate it into your response.\n"
                            print(f"✅ COMPREHENSIVE SUCCESS: {len(enhanced_context)} chars")
                        else:
                            # For off-topic questions, don't force vector context
                            enhanced_context = "\n\n=== VECTOR DATABASE CONSULTED ===\nNo relevant insurance information found. Feel free to respond naturally to the user's question.\n"
                            print("⚠️ No relevant vector results, allowing natural response")
                else:
                    print("❌ Embroker knowledge base not available")
                    enhanced_context = "\n\n=== KNOWLEDGE BASE UNAVAILABLE ===\nRespond naturally based on the conversation context.\n"
            except Exception as e:
                print(f"❌ Enhanced knowledge search failed: {e}")
                # On error, allow natural response
                enhanced_context = "\n\n=== KNOWLEDGE SEARCH ERROR ===\nRespond naturally based on the conversation context.\n"
            
            # If no company name provided, try to get it from database/registration
            if not company_name and conversation_id:
                try:
                    from src.models import Conversation, User, db
                    conversation = db.session.query(Conversation).filter_by(id=conversation_id).first()
                    if conversation and conversation.user:
                        self.current_company_name = conversation.user.company_name
                        print(f"DEBUG: Retrieved company name from database: {self.current_company_name}")
                except Exception as e:
                    print(f"DEBUG: Error retrieving company name from database: {e}")
            
            # Build conversation messages with enhanced context
            system_content = self.instructions + enhanced_context
            messages = [{"role": "system", "content": system_content}]
            
            # Add conversation history - process entire history like ChatGPT/Claude/Gemini
            if conversation_history:
                # Process ALL conversation history to maintain perfect context
                # Modern LLMs handle large contexts efficiently
                for msg in conversation_history:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if content:
                        messages.append({"role": role, "content": content})
            
            # Add current message
            messages.append({"role": "user", "content": message})
            
            # Check if user is asking for claims examples
            is_claims_example = any(keyword in message.lower() for keyword in ['claim example', 'claims example', 'example of a claim', 'example claim'])
            
            # Make API call with tools
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=800 if is_claims_example else None  # Allow longer responses for claims examples
            )
            
            response_message = response.choices[0].message
            
            # Handle tool calls
            if response_message.tool_calls:
                # Process each tool call
                messages.append(response_message)
                
                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    # Execute function
                    if function_name in self.function_mapping:
                        function_result = self.function_mapping[function_name](**function_args)
                        
                        # Special handling for risk assessment reports - don't show in chat, store for menu access
                        if function_name == "generate_risk_assessment_report" and "COMPREHENSIVE RISK ASSESSMENT REPORT" in function_result:
                            # Store report for menu access but don't show in chat
                            return "Your personalized risk assessment report has been generated and is now available in the menu (click the hamburger icon ☰ in the top left and select 'Risk Assessment'). The report includes comprehensive coverage recommendations and risk analysis specific to your company."
                        
                        # Add function result to messages
                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": function_result
                        })
                
                # Get final response with tool results
                # Check if user is asking for claims examples
                is_claims_example = any(keyword in message.lower() for keyword in ['claim example', 'claims example', 'example of a claim', 'example claim'])
                
                final_response = self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=800 if is_claims_example else None  # Allow longer responses for claims examples
                )
                
                return final_response.choices[0].message.content or "I apologize, but I couldn't generate a response."
            
            return response_message.content or "I apologize, but I couldn't generate a response."
            
        except Exception as e:
            print(f"Message processing error: {e}")
            return f"I'm experiencing technical difficulties. Please try again. Error: {e}"

    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        try:
            web_agent = get_web_search_agent()
            web_status = web_agent.get_system_status()
        except:
            web_status = {"web_search_available": False}
            
        return {
            "agent_type": "insurance_knowledge",
            "model": self.model,
            "pinecone_available": self.pinecone_available,
            "web_search_available": web_status.get("web_search_available", False),
            "tools_count": len(self.tools),
            "status": "operational"
        }

# Global agent instance
_insurance_agent = None

def get_insurance_agent():
    """Get or create the global insurance agent instance"""
    global _insurance_agent
    if _insurance_agent is None:
        _insurance_agent = InsuranceKnowledgeAgent()
    return _insurance_agent

async def process_insurance_query(message: str, conversation_history: List[Dict] = None, conversation_id: str = None, company_name: str = None) -> str:
    """Main entry point for processing insurance queries"""
    agent = get_insurance_agent()
    return await agent.process_message(message, conversation_history, conversation_id, company_name)

def get_agent_status() -> Dict[str, Any]:
    """Get agent system status"""
    try:
        agent = get_insurance_agent()
        return agent.get_system_status()
    except Exception as e:
        return {
            "agent_type": "insurance_knowledge",
            "status": "error",
            "error": str(e)
        }

# Test functionality
if __name__ == "__main__":
    async def test_agent():
        agent = get_insurance_agent()
        
        # Test basic functionality
        response = await agent.process_message("What is Tech E&O insurance?")
        print("Test Response:", response)
        
        # Test status
        status = agent.get_system_status()
        print("Agent Status:", status)
    
    asyncio.run(test_agent())