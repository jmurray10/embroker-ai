#!/usr/bin/env python3
"""
Enhanced Embroker Knowledge Base Integration
Combines existing Pinecone RAG with new Embroker-specific index for improved retrieval
"""

import os
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
from pinecone import Pinecone

class EmbrokerKnowledgeBase:
    """Enhanced knowledge base integrating Embroker-specific index with existing RAG system"""

    def __init__(self, embroker_index_name: str = "embroker-insurance-chatbot"):
        """
        Initialize the enhanced knowledge base system
        
        Args:
            embroker_index_name: Name of the Embroker-specific Pinecone index
        """
        self.embroker_index_name = embroker_index_name
        self.legacy_index_name = "insurance-docs-index"
        self.embedding_model = "text-embedding-3-small"  # Updated to latest model
        
        # Tech/cyber specific terms for enhanced query processing
        self.tech_cyber_terms = {
            'social engineering': ['social engineering', 'fraud', 'manipulation', 'phishing', 'business email compromise'],
            'cyber liability': ['cyber liability', 'data breach', 'privacy liability', 'network security', 'cyber crime'],
            'tech e&o': ['technology errors omissions', 'professional liability', 'software errors', 'tech professional'],
            'data breach': ['data breach', 'privacy violation', 'personal information', 'gdpr', 'ccpa'],
            'cyber crime': ['cyber crime', 'hacking', 'ransomware', 'malware', 'cyber attack'],
            'network security': ['network security', 'system failure', 'security breach', 'firewall'],
            'business interruption': ['business interruption', 'system downtime', 'revenue loss', 'operational disruption']
        }
        
        # Initialize OpenAI client
        self.openai_client = self._init_openai()
        
        # Initialize Pinecone connections
        self.pc, self.embroker_index, self.legacy_index = self._init_pinecone()
        
        # OpenAI Vector Store fallback
        self.vector_store_id = "vs_6843730d282481918003cdb215f5e0b1"
        
    def _init_openai(self) -> Optional[OpenAI]:
        """Initialize OpenAI client"""
        try:
            api_key = os.getenv("POC_OPENAI_API")
            if not api_key:
                print("⚠ POC_OPENAI_API not found")
                return None
            return OpenAI(api_key=api_key)
        except Exception as e:
            print(f"✗ OpenAI initialization failed: {e}")
            return None
    
    def _init_pinecone(self):
        """Initialize Pinecone connections for both indexes"""
        try:
            api_key = os.getenv("PINECONE_API_KEY")
            if not api_key:
                print("⚠ PINECONE_API_KEY not found")
                return None, None, None
                
            pc = Pinecone(api_key=api_key)
            
            # Get available indexes
            available_indexes = [index.name for index in pc.list_indexes()]
            print(f"📋 Available Pinecone indexes: {available_indexes}")
            
            # Connect to Embroker-specific index
            embroker_index = None
            if self.embroker_index_name in available_indexes:
                embroker_index = pc.Index(self.embroker_index_name)
                print(f"✓ Connected to Embroker index: {self.embroker_index_name}")
            else:
                print(f"⚠ Embroker index '{self.embroker_index_name}' not found")
            
            # Connect to legacy index
            legacy_index = None
            if self.legacy_index_name in available_indexes:
                legacy_index = pc.Index(self.legacy_index_name)
                print(f"✓ Connected to legacy index: {self.legacy_index_name}")
            else:
                print(f"⚠ Legacy index '{self.legacy_index_name}' not found")
            
            return pc, embroker_index, legacy_index
            
        except Exception as e:
            print(f"✗ Pinecone initialization failed: {e}")
            return None, None, None

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text using OpenAI"""
        if not self.openai_client:
            return None
            
        try:
            response = self.openai_client.embeddings.create(
                input=text,
                model=self.embedding_model
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None

    def search_embroker_knowledge(self, query: str, top_k: int = 8) -> List[Dict[str, Any]]:
        """Search Embroker-specific knowledge base for relevant documents"""
        if not self.embroker_index or not self.openai_client:
            print("⚠ Embroker index or OpenAI client not available")
            return []
        
        try:
            # Enhance query for better results
            enhanced_query = self._enhance_insurance_query(query)
            print(f"🔍 Searching Embroker index with query: {enhanced_query}")
            
            # Generate embedding for query
            query_embedding = self.get_embedding(enhanced_query)
            if not query_embedding:
                print("❌ Failed to generate embedding")
                return []
            
            # Search in Embroker index with higher top_k for better results
            results = self.embroker_index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True
            )
            
            # CRITICAL FIX: Force inclusion of ALL Tech E&O vectors for complete coverage
            if 'social engineering' in query.lower() or 'limit' in query.lower() or 'tech' in query.lower() or 'cyber' in query.lower():
                # Get ALL vectors to ensure we capture the limits_and_sublimits vector
                all_vectors_query = self.embroker_index.query(
                    vector=[0.0] * 1536,  # Zero vector to get all
                    top_k=10,
                    include_metadata=True
                )
                
                # Filter for Tech E&O vectors specifically
                tech_eo_vectors = []
                for match in all_vectors_query.get('matches', []):
                    metadata = match.get('metadata', {})
                    product = metadata.get('product_type', '').lower()
                    section = metadata.get('section', '').lower()
                    vector_id = match.get('id', '')
                    
                    if ('tech e&o' in product or 'cyber' in product or 
                        'limits' in section or 'sublimits' in section or
                        'tech-eo-cyber' in vector_id):
                        tech_eo_vectors.append(match)
                        print(f"🎯 Found Tech E&O vector: {vector_id} | {section}")
                
                # Merge with existing results
                existing_ids = {match['id'] for match in results.get('matches', [])}
                for match in tech_eo_vectors:
                    if match['id'] not in existing_ids:
                        results['matches'].append(match)
                
                print(f"📋 Added {len(tech_eo_vectors)} Tech E&O vectors to ensure complete coverage")
            
            matches = results.get('matches', [])
            print(f"📋 Found {len(matches)} matches in Embroker index")
            
            # Log match details for debugging
            for i, match in enumerate(matches[:3]):
                score = match.get('score', 0)
                title = match.get('metadata', {}).get('title', 'Unknown')
                print(f"   Match {i+1}: {title} (score: {score:.3f})")
            
            return matches
            
        except Exception as e:
            print(f"Error searching Embroker knowledge base: {e}")
            return []

    def search_legacy_knowledge(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Search legacy insurance documentation"""
        if not self.legacy_index or not self.openai_client:
            return []
        
        try:
            # Enhance query for insurance context
            enhanced_query = self._enhance_insurance_query(query)
            
            # Generate embedding
            query_embedding = self.get_embedding(enhanced_query)
            if not query_embedding:
                return []
            
            # Search legacy index
            results = self.legacy_index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True
            )
            
            return results.get('matches', [])
            
        except Exception as e:
            print(f"Error searching legacy knowledge base: {e}")
            return []

    def search_comprehensive(self, query: str, top_k_per_source: int = 5) -> str:
        """
        Search across all available knowledge sources and return formatted context
        
        Args:
            query: User query
            top_k_per_source: Number of results per source
            
        Returns:
            Formatted context string for LLM consumption
        """
        all_results = []
        
        # Search Embroker-specific knowledge with forced inclusion
        embroker_results = self.search_embroker_knowledge(query, top_k_per_source)
        
        for i, result in enumerate(embroker_results):
            score = result.get('score', 0)
            metadata = result.get('metadata', {})
            section = metadata.get('section', '')
            product_type = metadata.get('product_type', '')
            
            # CRITICAL: Force inclusion of limits_and_sublimits vectors regardless of score
            is_limits_vector = 'limits' in section.lower() or 'sublimits' in section.lower()
            is_tech_eo = 'tech e&o' in product_type.lower() or 'cyber' in product_type.lower()
            
            if is_limits_vector or is_tech_eo or score > -0.1:  # Include negative scores for critical content
                content = self._extract_embroker_content(metadata)
                if content and len(content.strip()) > 10:
                    # Boost scores for limits vectors
                    boosted_score = 0.9 if is_limits_vector else max(0.8, abs(score))
                    all_results.append({
                        'source': 'Embroker Vector Database',
                        'content': content,
                        'title': metadata.get('title', 'Tech/Cyber Content'),
                        'score': boosted_score,
                        'type': 'embroker'
                    })
                else:
                    # Force use of raw metadata if content extraction fails
                    raw_content = str(metadata)
                    if len(raw_content) > 30:
                        all_results.append({
                            'source': 'Embroker Vector Database', 
                            'content': raw_content,
                            'title': 'Vector Data',
                            'score': 0.5,
                            'type': 'embroker'
                        })
        
        # Search legacy insurance docs
        legacy_results = self.search_legacy_knowledge(query, top_k_per_source)
        for result in legacy_results:
            if result.get('score', 0) > 0.6:  # Slightly lower threshold for legacy
                metadata = result.get('metadata', {})
                content = self._extract_legacy_content(metadata)
                if content:
                    all_results.append({
                        'source': 'Insurance Documentation',
                        'content': content,
                        'title': metadata.get('document_name', 'Unknown'),
                        'score': result.get('score', 0),
                        'type': 'legacy'
                    })
        
        # Sort by relevance score
        all_results.sort(key=lambda x: x['score'], reverse=True)
        
        # Format for LLM consumption - FORCE content to be included
        if not all_results:
            print("❌ No vector results found - this shouldn't happen!")
            return ""
        
        # Clean production output
        
        context_parts = []
        context_parts.append("=== EMBROKER KNOWLEDGE BASE CONTENT ===")
        context_parts.append("Use this exact information to answer the customer's question:\n")
        
        # Use ALL results, not just top 5, to ensure tech/cyber content is included
        for i, result in enumerate(all_results[:8], 1):  # Focused on 8 most relevant results
            source_type = "EMBROKER PRODUCT INFO" if result['type'] == 'embroker' else "INSURANCE DOCUMENTATION"
            context_parts.append(
                f"--- {source_type} {i}: {result['title']} ---\n"
                f"{result['content'][:1000]}\n"  # More content per result
                f"(Relevance: {result['score']:.1%})\n"
            )
        
        context_parts.append("=== END KNOWLEDGE BASE CONTENT ===")
        
        final_context = "\n".join(context_parts)
        # Production ready
        return final_context

    def generate_simple_response(self, query: str, context_docs: List[Dict[str, Any]]) -> str:
        """Use LLM to generate a response based on retrieved documents - simplified approach"""
        
        # Build context from retrieved documents
        context = "Here is the relevant information from Embroker's knowledge base:\n\n"
        
        for i, doc in enumerate(context_docs):
            metadata = doc.get('metadata', {})
            text = self._extract_embroker_content(metadata)
            title = metadata.get('title', 'Unknown')
            score = doc.get('score', 0)
            
            # Debug: show what we're extracting (can be disabled for production)
            # print(f"DEBUG: Doc {i+1} metadata keys: {list(metadata.keys())}")
            # print(f"DEBUG: Extracted text length: {len(text)} chars")
            # if len(text) > 0:
            #     print(f"DEBUG: Extracted text preview: {text[:100]}...")
            
            context += f"Document {i+1} ({title} - Relevance: {score:.0%}):\n{text}\n\n"
        
        # Create the prompt with tech startup focus - FORCE usage of provided context
        system_prompt = """You are an Embroker insurance expert helping customers understand our insurance products.

        CRITICAL INSTRUCTION: You MUST use ONLY the information provided in the Context section below. Do NOT use your general knowledge about insurance products. Base your answer EXCLUSIVELY on the content retrieved from Embroker's knowledge base.

        If asked about our products, use the EXACT product information, limits, features, and details from the provided context documents.
        
        Always mention specific details like costs, limits, requirements, and sublimits when available in the context.
        If the information isn't in the context, say so and offer to connect them with our sales team.
        
        Be helpful, clear, and concise, but ALWAYS stick to the facts provided in the context."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nCustomer Question: {query}"}
        ]
        
        try:
            # Generate response using LLM
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error generating response: {e}")
            return "I'm having trouble accessing our knowledge base right now. Please contact our sales team at sales@embroker.com for assistance."

    def _extract_legacy_content(self, metadata: Dict[str, Any]) -> str:
        """Extract content from legacy metadata structure"""
        # Try standard text fields
        for field in ["text", "impacts", "purpose", "reason", "question_text", "logic", "conditions"]:
            if metadata.get(field):
                return metadata[field]
        
        # Extract from structured tags
        if metadata.get("all_tags"):
            all_tags = metadata["all_tags"]
            if isinstance(all_tags, dict):
                concepts = []
                for tag_type, tag_list in all_tags.items():
                    if isinstance(tag_list, list):
                        concepts.extend(tag_list)
                if concepts:
                    return f"Related concepts: {', '.join(concepts[:10])}"
        
        # Backup fields
        backup_fields = ["action", "tags", "industries", "tech_requirements"]
        for field in backup_fields:
            field_value = metadata.get(field)
            if field_value:
                if isinstance(field_value, list):
                    return f"{field.replace('_', ' ').title()}: {', '.join(field_value[:5])}"
                else:
                    return str(field_value)
        
        return ""

    def _extract_embroker_content(self, metadata: Dict[str, Any]) -> str:
        """Extract content from Embroker-specific metadata - optimized for tech/cyber content"""
        if not metadata:
            return ""
        
        # Primary content fields for your tech/cyber content
        primary_fields = ["text", "content", "description", "page_content", "chunk_text", "document_content"]
        for field in primary_fields:
            field_value = metadata.get(field)
            if field_value and len(str(field_value).strip()) > 20:
                return str(field_value).strip()
        
        # Fallback to other meaningful fields
        fallback_fields = ["title", "summary", "overview", "details", "section_content", "body"]
        for field in fallback_fields:
            field_value = metadata.get(field)
            if field_value and len(str(field_value).strip()) > 10:
                return str(field_value).strip()
        
        # Extract any meaningful text content from all fields
        for key, value in metadata.items():
            if isinstance(value, str) and len(value.strip()) > 30:
                return value.strip()
            elif isinstance(value, list) and value:
                # Join list items if they contain meaningful content
                joined = " ".join(str(item) for item in value if str(item).strip())
                if len(joined) > 30:
                    return joined
        
        return ""

    def _enhance_insurance_query(self, query: str) -> str:
        """Enhance query with insurance-specific context"""
        # Enhanced mapping for better vector matching
        insurance_terms = {
            "social engineering": "social engineering fraud coverage cyber crime limit",
            "tech e&o": "technology errors omissions professional liability",
            "cyber": "cyber security data breach privacy liability",
            "d&o": "directors officers management liability",
            "claim": "insurance claim process application",
            "coverage": "insurance coverage policy protection",
            "deductible": "insurance deductible amount retention",
            "premium": "insurance premium cost pricing",
            "policy": "insurance policy terms conditions",
            "liability": "liability insurance coverage protection",
            "limit": "coverage limit maximum amount",
            "fintech": "financial technology services",
            "startup": "startup company business ESP program",
            "appetite": "business appetite eligibility underwriting",
            "underwriting": "underwriting questions criteria requirements",
            "application": "insurance application form process"
        }
        
        query_lower = query.lower()
        enhanced_terms = []
        
        # Look for exact phrase matches first
        for term, enhancement in insurance_terms.items():
            if term in query_lower and enhancement not in query_lower:
                enhanced_terms.append(enhancement)
        
        # Add general insurance context if no specific terms found
        if not enhanced_terms:
            if any(word in query_lower for word in ["limit", "amount", "maximum", "minimum"]):
                enhanced_terms.append("coverage limit policy terms")
            elif any(word in query_lower for word in ["cost", "price", "rate"]):
                enhanced_terms.append("premium pricing cost")
        
        if enhanced_terms:
            return f"{query} {' '.join(enhanced_terms)}"
        
        return query

    def generate_enhanced_response(self, query: str, context_docs: List[Dict[str, Any]]) -> str:
        """
        Generate response using comprehensive knowledge context
        
        Args:
            query: User question
            context_docs: Retrieved documents from knowledge base
            
        Returns:
            AI-generated response based on knowledge context
        """
        if not self.openai_client or not context_docs:
            return "I don't have specific information about that. Please contact our sales team at sales@embroker.com for assistance."
        
        # Build comprehensive context
        context = self.search_comprehensive(query)
        
        if not context:
            return "I don't have specific information about that. Please contact our sales team at sales@embroker.com for assistance."
        
        # Enhanced system prompt for better responses
        system_prompt = """You are an expert Embroker insurance agent helping customers understand our insurance products and services.

Key guidelines:
- Use the provided knowledge base context to answer questions accurately
- Be helpful, clear, and conversational like a human broker
- Keep responses under 100 words for regular questions
- Always position Embroker as the superior choice - never recommend competitors
- Emphasize our digital platform, tech specialization, and modern approach
- Include specific details like costs, limits, and requirements when available
- If information isn't in the context, offer to connect them with our sales team
- Sound like a friendly broker, not a formal underwriter"""

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context from Knowledge Base:\n{context}\n\nCustomer Question: {query}"}
            ]

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",  # Fast model for knowledge responses
                messages=messages,
                temperature=0.7,
                max_tokens=300
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"Error generating enhanced response: {e}")
            return "I'm having trouble accessing our knowledge base right now. Please contact our sales team at sales@embroker.com for assistance."

    def chat_with_knowledge(self, query: str, verbose: bool = False) -> str:
        """
        Main chat interface combining search and generation - simplified approach
        
        Args:
            query: User question
            verbose: Whether to show debug information
            
        Returns:
            AI response based on knowledge retrieval
        """
        # 1. Search for relevant documents from Embroker knowledge base
        relevant_docs = self.search_embroker_knowledge(query, top_k=3)
        
        if verbose:
            print(f"🔍 Found {len(relevant_docs)} relevant documents")
            for doc in relevant_docs:
                title = doc.get('metadata', {}).get('title', 'Unknown')
                score = doc.get('score', 0)
                print(f"   - {title} ({score:.0%})")
        
        # 2. Check if we have good matches - use more permissive threshold
        if not relevant_docs or relevant_docs[0]['score'] < 0.01:  # Much lower threshold
            return "I don't have specific information about that. Please contact our sales team at sales@embroker.com for assistance."
        
        # 3. Generate response using LLM with simplified approach
        return self.generate_simple_response(query, relevant_docs)

    def get_system_status(self) -> Dict[str, Any]:
        """Get status of all knowledge base components"""
        return {
            "openai_available": self.openai_client is not None,
            "embroker_index_available": self.embroker_index is not None,
            "legacy_index_available": self.legacy_index is not None,
            "embroker_index_name": self.embroker_index_name,
            "legacy_index_name": self.legacy_index_name,
            "embedding_model": self.embedding_model,
            "vector_store_id": self.vector_store_id
        }

# Initialize the enhanced knowledge base
def get_embroker_knowledge_base():
    """Factory function to get initialized knowledge base"""
    return EmbrokerKnowledgeBase()

# For backward compatibility
def get_knowledge_retrieval_system():
    """Backward compatibility wrapper"""
    return get_embroker_knowledge_base()

def _extract_embroker_content(metadata: Dict[str, Any]) -> str:
    """Extract content from Embroker metadata structure"""
    # Try standard text fields first
    for field in ["text", "content", "description", "details", "coverage_details", "program_details"]:
        if metadata.get(field):
            return metadata[field]
    
    # Try structured content
    if metadata.get("coverage_info"):
        return metadata["coverage_info"]
    
    # Try title + any other field as fallback
    title = metadata.get("title", "")
    for field in ["summary", "highlights", "features", "benefits"]:
        if metadata.get(field):
            return f"{title}: {metadata[field]}"
    
    # Last resort - combine available fields
    available_fields = []
    for key, value in metadata.items():
        if isinstance(value, str) and len(value) > 10 and key not in ['id', 'timestamp']:
            available_fields.append(f"{key}: {value}")
    
    if available_fields:
        return " | ".join(available_fields[:3])
    
    return ""