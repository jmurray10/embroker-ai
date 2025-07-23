# rag_pinecone.py
import os
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI

class PineconeRAG:
    def __init__(self, index_name="embroker-insurance-chatbot"):
        """
        Initialize Pinecone RAG system for knowledge retrieval.
        
        Args:
            index_name: Name of the Pinecone index to use (default: embroker-insurance-chatbot)
        """
        self.index_name = index_name
        self.embedding_model = "text-embedding-ada-002"
        self.embedding_dimensions = 1536
        
        try:
            # Initialize Pinecone with new API
            pinecone_api_key = os.getenv("PINECONE_API_KEY")
            if pinecone_api_key:
                self.pc = Pinecone(api_key=pinecone_api_key)
                
                # Check if index exists
                existing_indexes = [index.name for index in self.pc.list_indexes()]
                if index_name in existing_indexes:
                    self.index = self.pc.Index(index_name)
                    print(f"Connected to Pinecone index: {index_name}")
                else:
                    print(f"Index '{index_name}' not found. Available indexes: {existing_indexes}")
                    self.index = None
            else:
                print("PINECONE_API_KEY not found, RAG functionality disabled")
                self.pc = None
                self.index = None
            
            # Initialize OpenAI client for embeddings
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if openai_api_key:
                self.openai_client = OpenAI(api_key=openai_api_key)
            else:
                print("OPENAI_API_KEY not found, embedding functionality disabled")
                self.openai_client = None
            
        except Exception as e:
            print(f"Error initializing Pinecone RAG: {str(e)}")
            self.pc = None
            self.index = None
            self.openai_client = None

    def retrieve(self, query, top_k=5):
        """
        Retrieve relevant insurance documents from Pinecone based on query.
        
        Args:
            query: User query string
            top_k: Number of top results to retrieve
            
        Returns:
            Concatenated text from retrieved documents with relevance scores
        """
        if not self.index or not self.openai_client:
            return ""
            
        try:
            # Enhance query for better insurance context matching
            enhanced_query = self._enhance_insurance_query(query)
            
            # Generate embedding for the enhanced query using text-embedding-ada-002
            response = self.openai_client.embeddings.create(
                input=enhanced_query, 
                model=self.embedding_model
            )
            vector = response.data[0].embedding
            
            # Query Pinecone index with namespace support
            query_params = {
                "vector": vector, 
                "top_k": top_k, 
                "include_metadata": True
            }
            
            results = self.index.query(**query_params)
            
            # Extract and format relevant documents
            docs = []
            for match in results.get("matches", []):
                score = match.get("score", 0)
                
                # Use inclusive threshold to retrieve relevant knowledge for all questions
                if score > 0.5:
                    metadata = match.get("metadata", {})
                    
                    # Extract content from various metadata fields based on document type
                    doc_text = ""
                    
                    # Try standard text fields first
                    for field in ["text", "impacts", "purpose", "reason", "question_text", "logic", "conditions"]:
                        if metadata.get(field):
                            doc_text = metadata[field]
                            break
                    
                    # If no direct text, extract from structured tags
                    if not doc_text and metadata.get("all_tags"):
                        all_tags = metadata["all_tags"]
                        if isinstance(all_tags, dict):
                            # Extract concepts from tag structure
                            concepts = []
                            for tag_type, tag_list in all_tags.items():
                                if isinstance(tag_list, list):
                                    concepts.extend(tag_list)
                            if concepts:
                                doc_text = f"Related concepts: {', '.join(concepts[:10])}"  # Limit to first 10
                    
                    # Extract from other metadata fields as backup
                    if not doc_text:
                        backup_fields = ["action", "tags", "industries", "tech_requirements"]
                        for field in backup_fields:
                            field_value = metadata.get(field)
                            if field_value:
                                if isinstance(field_value, list):
                                    doc_text = f"{field.replace('_', ' ').title()}: {', '.join(field_value[:5])}"
                                else:
                                    doc_text = str(field_value)
                                break
                    
                    doc_source = metadata.get("document_name", "Insurance Documentation")
                    doc_type = metadata.get("document_type", "")
                    content_type = metadata.get("content_type", "")
                    
                    # Add context based on document type
                    doc_context = ""
                    if "application" in doc_type.lower():
                        doc_context = "Application Question: "
                    elif "dynamic" in doc_type.lower():
                        doc_context = "Dynamic Underwriting Logic: "
                    elif "appetite" in doc_type.lower():
                        doc_context = "Appetite Guide: "
                    elif content_type == "question":
                        doc_context = "Underwriting Question: "
                    elif content_type == "exclusion":
                        doc_context = "Coverage Exclusion: "
                    
                    if doc_text:
                        # Format document with comprehensive source information
                        formatted_doc = f"[{doc_source}"
                        if doc_type:
                            formatted_doc += f" - {doc_type}"
                        if content_type:
                            formatted_doc += f" ({content_type})"
                        formatted_doc += f"]: {doc_context}{doc_text}"
                        docs.append(formatted_doc)
            
            return "\n\n".join(docs) if docs else ""
            
        except Exception as e:
            print(f"Error retrieving from insurance knowledge base: {str(e)}")
            return ""
    
    def _enhance_insurance_query(self, query):
        """
        Enhance query with insurance-specific context for better retrieval.
        
        Args:
            query: Original user query
            
        Returns:
            Enhanced query string
        """
        # Add insurance context to improve semantic matching across document types
        insurance_terms = {
            "claim": "insurance claim process application questions",
            "coverage": "insurance coverage policy appetite guide",
            "deductible": "insurance deductible amount",
            "premium": "insurance premium cost",
            "policy": "insurance policy terms",
            "liability": "liability insurance coverage",
            "auto": "automobile insurance",
            "home": "homeowners insurance",
            "business": "commercial business insurance class code",
            "health": "health insurance coverage",
            "fintech": "financial technology financial services class code",
            "appetite": "business appetite eligibility coverage class code guide",
            "within": "eligible included covered appetite",
            "questions": "application questions supplemental dynamic underwriting",
            "underwriting": "underwriting questions dynamic supplemental",
            "class": "class code appetite guide business type",
            "code": "class code business classification appetite"
        }
        
        query_lower = query.lower()
        enhanced_terms = []
        
        for term, enhancement in insurance_terms.items():
            if term in query_lower and enhancement not in query_lower:
                enhanced_terms.append(enhancement)
        
        if enhanced_terms:
            return f"{query} {' '.join(enhanced_terms)}"
        
        return query

    def add_document(self, doc_id, text, metadata=None):
        """
        Add a single document to the insurance knowledge base.
        
        Args:
            doc_id: Unique identifier for the document
            text: Document text content
            metadata: Additional metadata (source, title, category, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.index or not self.openai_client:
            print("RAG system not available for document upload")
            return False
            
        try:
            # Generate embedding for the document text
            response = self.openai_client.embeddings.create(
                input=text,
                model=self.embedding_model
            )
            vector = response.data[0].embedding
            
            # Prepare metadata
            doc_metadata = metadata or {}
            doc_metadata['text'] = text
            doc_metadata['doc_id'] = doc_id
            
            # Upsert to Pinecone
            self.index.upsert([(doc_id, vector, doc_metadata)])
            print(f"Successfully added document: {doc_id}")
            return True
            
        except Exception as e:
            print(f"Error adding document to knowledge base: {str(e)}")
            return False
    
    def add_documents_batch(self, documents):
        """
        Add multiple documents to the insurance knowledge base in batch.
        
        Args:
            documents: List of dictionaries with 'id', 'text', and optional 'metadata'
            
        Returns:
            Number of successfully added documents
        """
        if not self.index or not self.openai_client:
            print("RAG system not available for batch upload")
            return 0
            
        successful_uploads = 0
        batch_size = 100  # Pinecone batch limit
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            vectors_to_upsert = []
            
            try:
                for doc in batch:
                    doc_id = doc['id']
                    text = doc['text']
                    metadata = doc.get('metadata', {})
                    
                    # Generate embedding
                    response = self.openai_client.embeddings.create(
                        input=text,
                        model=self.embedding_model
                    )
                    vector = response.data[0].embedding
                    
                    # Prepare metadata
                    doc_metadata = metadata.copy()
                    doc_metadata['text'] = text
                    doc_metadata['doc_id'] = doc_id
                    
                    vectors_to_upsert.append((doc_id, vector, doc_metadata))
                
                # Batch upsert to Pinecone
                self.index.upsert(vectors_to_upsert)
                successful_uploads += len(batch)
                print(f"Successfully uploaded batch of {len(batch)} documents")
                
            except Exception as e:
                print(f"Error uploading batch: {str(e)}")
                
        return successful_uploads
    
    def search_documents(self, query, top_k=10, include_scores=True):
        """
        Search documents in the knowledge base with detailed results.
        
        Args:
            query: Search query
            top_k: Number of results to return
            include_scores: Whether to include relevance scores
            
        Returns:
            List of document results with metadata and scores
        """
        if not self.index or not self.openai_client:
            return []
            
        try:
            # Generate query embedding
            response = self.openai_client.embeddings.create(
                input=query,
                model=self.embedding_model
            )
            vector = response.data[0].embedding
            
            # Search Pinecone
            results = self.index.query(
                vector=vector,
                top_k=top_k,
                include_metadata=True
            )
            
            # Format results
            formatted_results = []
            for match in results.get("matches", []):
                result = {
                    'id': match.get('id'),
                    'text': match.get('metadata', {}).get('text', ''),
                    'metadata': match.get('metadata', {}),
                }
                
                if include_scores:
                    result['score'] = match.get('score', 0)
                    
                formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            print(f"Error searching documents: {str(e)}")
            return []
    
    def get_index_stats(self):
        """
        Get statistics about the insurance knowledge base.
        
        Returns:
            Dictionary with index statistics
        """
        if not self.index:
            return {"error": "Index not available"}
            
        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vectors": stats.get("total_vector_count", 0),
                "index_fullness": stats.get("index_fullness", 0),
                "dimension": stats.get("dimension", self.embedding_dimensions),
                "index_name": self.index_name,
                "embedding_model": self.embedding_model
            }
        except Exception as e:
            return {"error": str(e)}
    
    def is_available(self):
        """Check if the RAG system is properly initialized and available."""
        return self.index is not None and self.openai_client is not None
