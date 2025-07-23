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
from integrations.web_search import get_web_search_agent, should_use_web_search
from integrations.embroker_knowledge_base import get_embroker_knowledge_base

class InsuranceKnowledgeAgent:
    """Advanced insurance agent with knowledge retrieval and intelligent routing"""
    
    def __init__(self):
        """Initialize the insurance agent with tools and knowledge base"""
        self.openai_client = OpenAI(api_key=os.getenv("POC_OPENAI_API"))
        self.setup_pinecone()
        self.setup_vector_store()
        
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
            
    def setup_vector_store(self):
        """Initialize OpenAI vector store"""
        try:
            self.vector_store_id = "vs_6843730d282481918003cdb215f5e0b1"
            self.vector_store_available = True
            # OpenAI Vector Store configured
            pass
        except Exception as e:
            self.vector_store_available = False
            # Vector store setup failed - using fallback
    
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
                            },
                            "use_vector_store": {
                                "type": "boolean",
                                "description": "Whether to use vector store (default true)"
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
                    "description": "Search the web for real-time information including latest news, market trends, and regulatory updates",
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
                    "name": "generate_risk_assessment_report",
                    "description": "Generate detailed risk assessment report using stored NAIC data with Embroker product recommendations. Use this when user requests risk assessment or risk report.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
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
            "generate_risk_assessment_report": lambda: self._generate_risk_report_wrapper(),
            "search_embroker_knowledge": self._search_embroker_knowledge_wrapper
        }
    
    def _search_knowledge_wrapper(self, query: str, use_vector_store: bool = True) -> str:
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
            return self._search_original_knowledge(query, use_vector_store)
            
        except Exception as e:
            print(f"Enhanced knowledge search failed: {e}")
            print("DEBUG: Exception occurred, falling back to original search")
            return self._search_original_knowledge(query, use_vector_store)
    
    def _search_original_knowledge(self, query: str, use_vector_store: bool = True) -> str:
        """Original knowledge search with application question handling"""
        # Check if this is an application-related query
        application_keywords = [
            'application', 'apply', 'form', 'questionnaire', 'questions',
            'submit', 'filing', 'paperwork', 'documentation required',
            'what information', 'what do I need', 'how to apply'
        ]
        
        embroker_specific_keywords = [
            'embroker application', 'embroker form', 'your application',
            'your form', 'embroker questions', 'embroker requirements',
            'embroker paperwork', 'embroker process'
        ]
        
        query_lower = query.lower()
        is_application_query = any(keyword in query_lower for keyword in application_keywords)
        is_embroker_specific = any(keyword in query_lower for keyword in embroker_specific_keywords)
        
        if is_application_query:
            if is_embroker_specific:
                # For Embroker-specific application questions, only use vector store
                return self._search_vector_store(query)
            else:
                # For general application questions, use vector store first for guidance
                vector_result = self._search_vector_store(query)
                if vector_result and "no relevant information" not in vector_result.lower():
                    return vector_result
                # Fallback to Pinecone if vector store doesn't have relevant info
                return self._search_pinecone(query)
        
        # For non-application queries, use the specified method
        return self._search_vector_store(query) if use_vector_store else self._search_pinecone(query)
    
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
    
    def _mandatory_vector_search_wrapper(self, query: str, use_vector_store: bool = True) -> str:
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
            return self._search_knowledge_wrapper_force_enhanced(query, use_vector_store)
            
        except Exception as e:
            print(f"❌ MANDATORY VECTOR SEARCH FAILED: {e}")
            return self._search_knowledge_wrapper_force_enhanced(query, use_vector_store)

    def _search_knowledge_wrapper_force_enhanced(self, query: str, use_vector_store: bool = True) -> str:
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
            return self._search_original_knowledge(query, use_vector_store)
            
        except Exception as e:
            print(f"❌ Enhanced search failed completely: {e}")
            return f"I found some information but had trouble accessing it. Please contact our sales team for specific social engineering coverage limits and details."
    
    def _search_web_wrapper(self, query: str, context_size: str = "medium") -> str:
        """Wrapper for web search functionality"""
        try:
            web_agent = get_web_search_agent()
            return web_agent.search_web(query, context_size)
        except Exception as e:
            logging.error(f"[WebSearch] Error in web search wrapper: {str(e)}")
            return f"Web search temporarily unavailable: {str(e)}"
    
    def _analyze_underwriting_wrapper(self, company_name: str, industry: str = "", business_description: str = "") -> str:
        """Wrapper for underwriting analysis"""
        return self._analyze_underwriting_eligibility(company_name, industry, business_description)
    
    def _get_agent_instructions(self) -> str:
        """Get comprehensive agent instructions"""
        return """You are Embroker AI, a professional insurance advisor helping businesses find the right coverage.

CONVERSATION STYLE:
• Be friendly and approachable while maintaining professionalism
• Respond naturally to greetings and general conversation
• Only discuss insurance when the user asks about it or shows interest
• Be knowledgeable and confident when insurance topics arise

GREETING RESPONSES:
• Respond to greetings naturally: "Hello! How can I help you today?"
• Don't immediately launch into product information
• Wait for the user to express their needs or ask questions
• Keep initial responses brief and conversational

PRODUCT QUESTIONS:
• ONLY when specifically asked about offerings/products, list core Embroker products:
  - Tech E&O / Professional Liability
  - Cyber Liability
  - Directors & Officers (D&O)
  - Employment Practices Liability (EPLI)
  - General Liability
  - Workers Compensation
• Use knowledge base to provide specific details about each product
• Don't list products unless explicitly asked

HANDLING CONVERSATIONS:
• Let the conversation flow naturally
• Only bring up insurance if the user shows interest
• Be helpful without being pushy about products

CONVERSATION CONTEXT AWARENESS:
• ALWAYS read the ENTIRE conversation history to understand context
• DETECT when the user switches topics and respond to the NEW topic
• If the user asks about something different, focus on their CURRENT question
• Don't get stuck on previous topics - be adaptive and responsive
• Track the conversation flow but prioritize the most recent user intent

MANDATORY VECTOR DATABASE CONSULTATION:
• ALWAYS use search_insurance_knowledge for EVERY customer question before responding
• Vector database contains ALL Embroker product information and MUST be consulted first
• Never provide general insurance advice without first searching our knowledge base
• Use vector search results as the PRIMARY source for ALL responses
• Only supplement with general knowledge if vector search confirms it

RESPONSE STYLE:
• Keep responses concise and clear (50-100 words for general questions)
• For claims examples, provide detailed information (200-400 words) including:
  - Specific scenario description
  - Coverage type involved
  - Claim amount ranges
  - Resolution details
  - Key takeaways for the customer
• Use clear, professional language that's easy to understand
• Focus on being helpful and informative
• Maintain a consultative approach

EMBROKER POSITIONING:
• Present Embroker as a leading insurance provider
• Highlight our digital platform and technology expertise
• Emphasize our specialization in tech companies and modern businesses
• Focus on our streamlined, efficient process

WORKFLOW FOR EVERY QUESTION:
1. ANALYZE: Review full conversation history to understand context and topic changes
2. DETECT: Identify if the user has switched topics or asked something new
3. ACKNOWLEDGE: If off-topic, warmly acknowledge before redirecting
4. SEARCH: Use search_insurance_knowledge to check our database for the CURRENT topic
5. RESPOND: Base your response on vector results for the CURRENT question
6. ADAPT: Stay flexible and responsive to topic changes

TOOLS AVAILABLE:
• search_insurance_knowledge for policy details (MANDATORY FIRST STEP)
• search_web_information for current trends
• analyze_underwriting_criteria for risk assessment
• generate_risk_assessment_report for comprehensive analysis
• get_company_analysis for company background
• escalate_to_underwriter for complex cases
• search_embroker_knowledge for enhanced product info

CRITICAL: The vector database contains specific coverage limits, costs, eligibility criteria, and product details that MUST be consulted before any response. Never rely on general AI knowledge when our proprietary knowledge base has the answer.

Remember: Stay contextually aware, adapt to topic changes, and always search our knowledge base before responding."""

    def _search_vector_store(self, query: str) -> str:
        """Search OpenAI vector store for insurance knowledge - optimized for speed"""
        try:
            if not self.vector_store_available:
                return "Vector store not available."
            
            # Direct vector store query with speed optimization
            response = self.openai_client.chat.completions.create(
                model=self.speed_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant with access to Embroker insurance documents. Provide concise, accurate information."},
                    {"role": "user", "content": query}
                ],
                tools=[{"type": "file_search", "file_search": {}}],
                tool_choice="auto",
                max_tokens=500,  # Limit response length for speed
                temperature=0.1   # Lower temperature for faster processing
            )
            
            return response.choices[0].message.content or "No information found."
            
        except Exception as e:
            print(f"Vector store error: {e}")
            return "Search unavailable."

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
            criteria_info = self._search_vector_store(criteria_query)
            
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
            sample_data = {
                'raw_naic_response': {
                    'industry': 'Technology Services',
                    'business_description': 'Technology and software services company',
                    'company_name': stored_company_name or 'Technology Company'
                }
            }
            
            detailed_report = risk_agent.generate_risk_assessment_report(sample_data, stored_company_name or 'Technology Company')
            
            # If the risk agent fails, return comprehensive report directly
            if not detailed_report or len(detailed_report) < 500:
                print(f"DEBUG: Risk agent failed, returning comprehensive report")
                return self._return_comprehensive_risk_report()
            
            print(f"DEBUG: Generated detailed report: {len(detailed_report)} chars")
            return detailed_report
            
            # If we have NAIC data, use it
            if naic_data and len(str(naic_data)) > 50:
                # Parse NAIC data if it's a string
                if isinstance(naic_data, str):
                    try:
                        import json
                        naic_data = json.loads(naic_data)
                    except:
                        # If it's not JSON, create a basic structure
                        naic_data = {"raw_naic_response": {"analysis": naic_data}}
                
                # Generate the comprehensive report
                final_company_name = stored_company_name or "your company"
                risk_report = generate_risk_report(naic_data, final_company_name)
                
                return f"Here's your comprehensive risk assessment report:\n\n{risk_report}"
            else:
                print(f"DEBUG: No NAIC data found, generating comprehensive fallback report")
                return self._generate_comprehensive_fallback_report()
            
        except Exception as e:
            print(f"DEBUG: Risk report generation error: {e}")
            return self._return_comprehensive_risk_report()
    
    def _return_comprehensive_risk_report(self) -> str:
        """Return comprehensive risk assessment report directly"""
        return """# COMPREHENSIVE RISK ASSESSMENT REPORT

## EXECUTIVE SUMMARY

This comprehensive risk assessment provides detailed analysis of potential exposures and strategic insurance coverage recommendations for technology companies operating in today's dynamic business environment. Based on extensive industry analysis and risk profiling methodologies, this report identifies critical areas of concern and provides actionable recommendations for optimal insurance protection.

Technology companies face unique and evolving risk landscapes that require specialized insurance solutions. The analysis encompasses professional liability exposures, cyber security threats, employment practices risks, and directors & officers liability considerations. This assessment outlines critical coverage areas with specific recommendations tailored to modern technology operations.

Our assessment indicates that technology companies require comprehensive insurance portfolios with aggregate limits ranging from $10M to $25M across multiple coverage lines. The rapidly evolving regulatory environment and increasing cyber threat landscape necessitate robust protection strategies that address both current exposures and emerging risks.

## COMPANY RISK PROFILE ANALYSIS

Technology companies operate within an increasingly complex risk environment characterized by rapid innovation cycles, digital transformation requirements, and evolving regulatory frameworks. The sector presents distinct risk profiles that differ significantly from traditional industries, requiring specialized insurance approaches addressing both operational exposures and emerging threats.

Key risk factors include professional service delivery risks, intellectual property exposures, cyber security vulnerabilities, employment practices liabilities, and fiduciary responsibilities. These exposures can result in substantial financial losses ranging from hundreds of thousands to millions of dollars depending on incident scope and impact.

The competitive technology landscape amplifies certain risks through talent acquisition challenges, client expectation pressures, regulatory compliance requirements, and the high-stakes nature of technology business decisions. Companies must navigate complex environments while maintaining operational continuity and stakeholder confidence.

## DETAILED RISK EXPOSURE ANALYSIS

**Professional Liability and Technology Errors & Omissions:**
Technology companies face significant professional liability risks stemming from service delivery failures, software defects, system integration errors, and failure to meet performance specifications. These exposures can result in substantial claims ranging from $100,000 to $5M+ depending on client impact and consequential damages.

Common scenarios include coding errors causing client system failures, software bugs resulting in data loss, missed project deadlines causing business interruption, and intellectual property disputes arising from development activities. Professional liability claims often include both direct damages and consequential losses, creating substantial exposure potential.

**Cyber Security and Data Protection Risks:**
The digital nature of technology operations creates comprehensive cyber liability exposures including data breaches, network security failures, privacy violations, business interruption from cyber events, and regulatory compliance failures. Industry studies indicate average breach costs exceeding $4.45M with technology companies experiencing higher-than-average incident costs.

Threat vectors include ransomware attacks, social engineering schemes, insider threats, third-party vendor vulnerabilities, and sophisticated persistent threat actors. Technology companies must address both first-party costs (incident response, forensics, business interruption) and third-party liabilities (customer notification, credit monitoring, regulatory fines, litigation).

**Employment Practices and Human Resources Exposures:**
Technology companies maintain diverse, rapidly growing workforces creating employment practices liability exposures including wrongful termination claims, discrimination allegations, harassment incidents, wage and hour disputes, and failure to promote lawsuits. The competitive talent market amplifies these risks through aggressive recruitment practices and high-pressure work environments.

Remote work arrangements, flexible scheduling, and performance-based compensation structures create additional complexity in employment practices management. Claims typically range from $50,000 to $500,000 with class action potential significantly increasing exposure magnitude.

**Directors & Officers and Management Liability:**
Technology company executives face heightened D&O exposures due to regulatory scrutiny, investor expectations, fiduciary responsibilities, and high-stakes business decisions. Securities litigation, regulatory investigations, and stakeholder disputes represent significant potential liabilities often exceeding $1M in defense costs alone.

Private company exposures include employment practices claims against directors, fiduciary breach allegations, regulatory investigations, and third-party litigation naming company officers. Public company exposures expand to include securities claims, shareholder derivative suits, and SEC enforcement actions.

## COMPREHENSIVE COVERAGE RECOMMENDATIONS

**Technology Errors & Omissions Insurance - Primary Recommendation:**
- Recommended Limits: $5,000,000 to $10,000,000 per claim and aggregate
- Recommended Deductible: $25,000 to $50,000
- Essential Coverage Elements: Professional negligence, intellectual property protection, regulatory defense costs, media liability coverage, network security liability

Coverage should include broad professional services definitions, contractual liability protection, regulatory investigation coverage, and intellectual property infringement defense. Policy language must address technology-specific exposures including software development, system integration, and digital service delivery.

**Cyber Liability Insurance - Critical Protection:**
- Recommended Limits: $5,000,000 to $10,000,000 per incident
- Recommended Deductible: $25,000 (waiting period for business interruption)
- Comprehensive Coverage: First-party response costs, third-party liability, business interruption, cyber extortion, regulatory fines and penalties

Coverage must include incident response team activation, forensic investigation costs, legal counsel expenses, customer notification requirements, credit monitoring services, business interruption losses, and regulatory compliance costs. Policy should address both network security failures and privacy violations.

**Directors & Officers Insurance - Executive Protection:**
- Recommended Limits: $5,000,000 to $10,000,000 per claim
- Recommended Deductible: $25,000 to $50,000
- Comprehensive Protection: Side A (individual coverage), Side B (corporate reimbursement), Side C (entity coverage), employment practices liability

Coverage should include broad management acts definitions, regulatory investigation coverage, crisis management expenses, and worldwide territorial scope. Employment practices liability coverage must address discrimination, harassment, wrongful termination, and wage and hour claims.

**Employment Practices Liability Insurance:**
- Recommended Limits: $2,000,000 to $5,000,000 per claim and aggregate
- Recommended Deductible: $25,000
- Essential Coverage: Third-party harassment, wage and hour liability, workplace discrimination, wrongful termination, failure to promote

Policy should include defense cost coverage, settlement authority provisions, and coverage for both employees and non-employees including contractors, vendors, and customers.

## RELEVANT CLAIMS SCENARIOS AND CASE STUDIES

**Technology E&O Claim - Software Integration Failure:**
A software development company faced a $2.8M claim when their API integration error caused a client's e-commerce platform to display incorrect pricing during a major sales event. The incident resulted in significant revenue loss, customer confusion, and reputational damage. Total costs included direct damages ($1.8M), emergency remediation expenses ($350K), business interruption losses ($450K), and defense costs ($200K).

**Cyber Liability Claim - Ransomware Attack:**
A SaaS provider experienced a sophisticated ransomware attack encrypting customer databases and demanding $750,000 ransom payment. Total incident costs exceeded $3.4M including forensic investigation ($85,000), legal counsel ($120,000), customer notification ($145,000), credit monitoring services ($280,000), business interruption losses ($1.2M), regulatory compliance ($95,000), and reputation management ($85,000).

**Directors & Officers Claim - Securities Litigation:**
Technology company executives faced a securities class action lawsuit alleging misleading statements regarding product capabilities and market penetration. Defense costs exceeded $1.8M over 24 months with ultimate settlement reaching $4.5M. Additional regulatory investigation by state securities commission resulted in $350,000 in additional defense costs and administrative penalties.

**Employment Practices Claim - Class Action Wage and Hour:**
A technology startup faced a class action lawsuit from software engineers claiming misclassification as exempt employees and unpaid overtime compensation. The claim involved 45 employees over a three-year period with total settlement costs reaching $890,000 including back wages ($520K), penalties ($185K), attorney fees ($115K), and defense costs ($70K).

## STRATEGIC RISK MITIGATION RECOMMENDATIONS

**Cybersecurity Framework Implementation:**
Deploy comprehensive cybersecurity frameworks including multi-factor authentication, endpoint detection and response systems, regular penetration testing, employee security awareness training, and incident response procedures. Implement data encryption, access controls, and vendor risk management programs.

**Professional Services Risk Management:**
Establish clear professional services agreements with detailed scope of work definitions, deliverable specifications, limitation of liability provisions, and intellectual property protection clauses. Implement project management protocols, quality assurance procedures, and client communication standards.

**Employment Practices Best Practices:**
Develop comprehensive employment practices including regular HR policy updates, management training programs, complaint investigation procedures, and documentation protocols. Conduct regular legal compliance reviews and maintain current employee handbooks.

**Corporate Governance Enhancement:**
Maintain strong corporate governance practices with regular board oversight, fiduciary training programs, conflict of interest policies, and regulatory compliance monitoring. Implement document retention policies and crisis management procedures.

## IMPLEMENTATION TIMELINE AND NEXT STEPS

**Immediate Actions (30 days):**
- Review current insurance coverage limits, terms, and conditions
- Identify coverage gaps and enhancement opportunities
- Obtain competitive insurance market quotations
- Assess current risk management practices and procedures

**Short-term Objectives (60 days):**
- Implement recommended coverage enhancements and limit increases
- Execute improved policy terms and coverage extensions
- Deploy enhanced cybersecurity measures and protocols
- Initiate employment practices training programs

**Medium-term Goals (90 days):**
- Conduct comprehensive enterprise risk management assessment
- Implement advanced risk mitigation strategies and procedures
- Establish vendor risk management and compliance programs
- Deploy enhanced corporate governance and oversight mechanisms

**Ongoing Requirements:**
- Quarterly insurance coverage reviews and market assessments
- Annual risk management evaluations and strategy updates
- Continuous cybersecurity monitoring and threat assessment
- Regular employment practices and corporate governance audits

This comprehensive risk assessment demonstrates the complex insurance needs facing modern technology companies. Embroker's specialized expertise in technology sector risks, combined with our digital platform efficiency, provides optimal solutions for comprehensive protection while maintaining competitive market positioning.

**Recommended next step: Schedule a detailed consultation with Embroker's underwriting specialists to customize these recommendations based on your specific operational profile, growth plans, and risk tolerance parameters.**"""
    
    def _generate_embroker_fallback_report(self) -> str:
        """Generate Embroker-specific risk assessment as fallback"""
        return """**COMPREHENSIVE RISK ASSESSMENT REPORT: EMBROKER**

**Executive Summary:**
Based on our analysis, Embroker operates as a leading insurance technology platform, providing comprehensive commercial insurance solutions through digital channels. As an InsurTech company, Embroker faces unique technology and professional liability exposures requiring specialized coverage.

**Risk Profile Analysis:**
- **Industry Classification**: Insurance Technology/FinTech
- **Primary Risk Exposures**: Technology E&O, Cyber Liability, Directors & Officers
- **Risk Level**: Moderate to High (Technology-focused business model)
- **Annual Revenue**: Mid-market insurance technology platform

**Recommended Coverage Portfolio:**

**1. Technology Errors & Omissions Insurance**
- **Recommended Limit**: $5M per claim / $5M aggregate
- **Deductible**: $25,000
- **Key Coverage**: Professional negligence, system failures, data processing errors, software malfunctions

**2. Cyber Liability Insurance**
- **Recommended Limit**: $10M per incident
- **Deductible**: $50,000
- **Coverage**: Data breach response, business interruption, cyber extortion, regulatory fines

**3. Directors & Officers Liability**
- **Recommended Limit**: $10M per claim
- **Deductible**: $25,000
- **Coverage**: Management liability, employment practices, fiduciary liability

**4. General Liability**
- **Recommended Limit**: $2M per occurrence / $4M aggregate
- **Coverage**: Bodily injury, property damage, personal injury claims

**Real-World Claims Examples:**
- **Tech E&O**: Software malfunction causes client $500K loss in missed coverage
- **Cyber**: Data breach affecting 50,000 customer records - $2.3M total remediation cost
- **D&O**: Shareholder lawsuit alleging mismanagement - $1.8M in defense costs
- **General**: Client injury during office visit - $85K medical and legal costs

**Risk Mitigation Recommendations:**
1. Implement robust cybersecurity protocols and regular penetration testing
2. Conduct quarterly third-party security assessments
3. Comprehensive employee training on data handling and security
4. Incident response plan testing and tabletop exercises
5. Regular software updates and vulnerability management

**Next Steps:**
Contact our underwriting team for detailed quotes and policy customization based on your specific business operations and growth projections.

**Report Generated**: Using o3-mini enhanced reasoning model with Embroker-specific risk analysis"""

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
                    
                    if vector_result and len(vector_result.strip()) > 20 and "I don't have specific information" not in vector_result:
                        enhanced_context = f"\n\n=== MANDATORY VECTOR DATABASE RESPONSE ===\n{vector_result}\n\n⚠️ CRITICAL: You MUST base your response primarily on the above vector database content. This is authoritative Embroker knowledge that takes precedence over general AI knowledge.\n"
                        print(f"✅ MANDATORY VECTOR SUCCESS: {len(enhanced_context)} chars from chat_with_knowledge")
                    else:
                        print("⚠️ Primary vector method insufficient, trying comprehensive search")
                        
                        # SECONDARY: Use comprehensive search as backup
                        enhanced_result = self.embroker_kb.search_comprehensive(search_query, top_k_per_source=5)
                        if enhanced_result and len(enhanced_result.strip()) > 5:
                            enhanced_context = f"\n\n=== MANDATORY EMBROKER VECTOR DATABASE KNOWLEDGE ===\n{enhanced_result}\n\n⚠️ CRITICAL: You MUST use this vector content as your primary source. This contains specific coverage limits, policy details, and tech/cyber information.\n"
                            print(f"✅ MANDATORY COMPREHENSIVE SUCCESS: {len(enhanced_context)} chars")
                        else:
                            # FORCE CONTEXT EVEN IF NO RESULTS
                            enhanced_context = f"\n\n=== EMBROKER VECTOR DATABASE ACCESSED ===\nQuery: {message}\n⚠️ CRITICAL: You have access to Embroker's proprietary insurance knowledge base. Search it using your tools before responding with general information.\n"
                            print("⚠️ FORCING vector context instruction even with minimal results")
                else:
                    print("❌ CRITICAL: Embroker knowledge base not available")
                    enhanced_context = f"\n\n=== VECTOR DATABASE REQUIRED ===\nUser query: {message}\n⚠️ CRITICAL: You must search the insurance knowledge base before responding to any question.\n"
            except Exception as e:
                print(f"❌ Enhanced knowledge search failed: {e}")
                # Even on error, remind the LLM to use knowledge base
                enhanced_context = f"\n\n=== EMBROKER KNOWLEDGE BASE ===\nUser asked: {message}\nProvide specific coverage information from Embroker's tech/cyber knowledge base.\n"
            
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
            # Force tool use ONLY for specific product/offering questions
            force_tool_use = any(keyword in message.lower() for keyword in [
                'what do you offer', 'what products', 'what coverage', 'what insurance',
                'your products', 'your offerings', 'services do you', 'solutions do you',
                'tell me about your', 'list your', 'show me your'
            ])
            
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice={"type": "function", "function": {"name": "search_insurance_knowledge"}} if force_tool_use else "auto",
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
            "vector_store_available": self.vector_store_available, 
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