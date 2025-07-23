"""
NAIC Risk Assessment Report Generator
Uses stored NAIC JSON data to generate comprehensive risk assessments with Embroker product recommendations
"""

import json
import os
import time
from typing import Dict, Any, List, Optional
from openai import OpenAI

class RiskAssessmentAgent:
    """Agent for generating detailed risk assessment reports using NAIC data"""
    
    def __init__(self):
        """Initialize the risk assessment agent"""
        self.openai_client = OpenAI(api_key=os.environ.get("POC_OPENAI_API"))
        # Using o3-mini-2025-01-31 for enhanced reasoning capabilities in risk assessment
        self.reasoning_model = "gpt-4"
        
        # Embroker product portfolio with coverage details
        self.embroker_products = {
            "tech_eo": {
                "name": "Technology Errors & Omissions",
                "limits": ["$1M", "$2M", "$5M", "$10M"],
                "deductibles": ["$2,500", "$5,000", "$10,000", "$25,000"],
                "key_coverages": [
                    "Professional liability for technology services",
                    "Network security and privacy liability",
                    "Data breach response costs",
                    "Regulatory defense and fines",
                    "Media liability protection"
                ]
            },
            "cyber_liability": {
                "name": "Cyber Liability",
                "limits": ["$1M", "$2M", "$5M", "$10M"],
                "deductibles": ["$1,000", "$2,500", "$5,000", "$10,000"],
                "key_coverages": [
                    "Data breach notification costs",
                    "Credit monitoring services",
                    "Business interruption due to cyber events",
                    "Cyber extortion and ransomware",
                    "Third-party cyber liability"
                ]
            },
            "epli": {
                "name": "Employment Practices Liability Insurance (EPLI)",
                "limits": ["$1M", "$2M", "$5M", "$10M"],
                "deductibles": ["$5,000", "$10,000", "$25,000"],
                "key_coverages": [
                    "Wrongful termination claims",
                    "Discrimination and harassment defense",
                    "Wage and hour disputes",
                    "Third-party coverage for client claims",
                    "Defense costs and settlements"
                ]
            },
            "directors_officers": {
                "name": "Directors & Officers (D&O)",
                "limits": ["$1M", "$2M", "$5M", "$10M"],
                "deductibles": ["$5,000", "$10,000", "$25,000", "$50,000"],
                "key_coverages": [
                    "Management liability protection",
                    "Securities claims defense",
                    "Fiduciary liability",
                    "Crime and fidelity coverage",
                    "Corporate reimbursement"
                ]
            },
            "general_liability": {
                "name": "General Liability",
                "limits": ["$1M", "$2M", "$5M", "$10M"],
                "deductibles": ["$1,000", "$2,500", "$5,000", "$10,000"],
                "key_coverages": [
                    "Bodily injury and property damage",
                    "Personal and advertising injury",
                    "Products and completed operations",
                    "Medical expenses",
                    "Legal defense costs"
                ]
            }
        }
        
        # Embroker class code specific claims examples
        self.class_code_claims = {
            "Technology": {
                "tech_eo": [
                    {
                        "scenario": "Software Bug Causes Client Financial Loss",
                        "claim_amount": "$750,000",
                        "description": "A fintech startup's payment processing software contained a bug that caused transaction data corruption, resulting in client financial losses and regulatory investigation."
                    },
                    {
                        "scenario": "API Integration Failure",
                        "claim_amount": "$350,000",
                        "description": "An e-commerce platform's API integration error led to incorrect pricing on a major client's website, causing significant revenue loss."
                    }
                ],
                "cyber_liability": [
                    {
                        "scenario": "Ransomware Attack on SaaS Platform",
                        "claim_amount": "$2.1M",
                        "description": "Ransomware encrypted customer data. Costs included forensics, notification, credit monitoring, and business interruption."
                    }
                ]
            },
            "Insurance": {
                "tech_eo": [
                    {
                        "scenario": "Insurance Platform Data Breach",
                        "claim_amount": "$1.2M",
                        "description": "Insurance technology platform exposed policyholder data during system migration, affecting 50,000 customers."
                    },
                    {
                        "scenario": "Quote Engine Algorithm Error",
                        "claim_amount": "$450,000",
                        "description": "Incorrect algorithm in insurance quoting system led to underpriced policies and carrier losses."
                    }
                ],
                "cyber_liability": [
                    {
                        "scenario": "Broker Portal Ransomware",
                        "claim_amount": "$890,000",
                        "description": "Insurance broker's client portal was compromised, requiring full system rebuild and customer notification."
                    }
                ]
            },
            "Professional Services": {
                "tech_eo": [
                    {
                        "scenario": "Consulting Project Failure",
                        "claim_amount": "$550,000",
                        "description": "Management consulting firm's flawed recommendations led to client's failed digital transformation."
                    }
                ],
                "cyber_liability": [
                    {
                        "scenario": "Client Data Exposure",
                        "claim_amount": "$320,000",
                        "description": "Professional services firm's cloud storage misconfiguration exposed sensitive client documents."
                    }
                ]
            }
        }
        
        # Legacy claims examples for backward compatibility
        self.claims_examples = {
            "tech_eo": [
                {
                    "scenario": "Software Bug Causes Client Data Loss",
                    "claim_amount": "$750,000",
                    "description": "A fintech startup's payment processing software contained a bug that caused transaction data corruption, resulting in client financial losses and regulatory investigation."
                },
                {
                    "scenario": "API Integration Failure",
                    "claim_amount": "$350,000", 
                    "description": "An e-commerce platform's API integration error led to incorrect pricing on a major client's website, causing significant revenue loss and reputation damage."
                },
                {
                    "scenario": "Cloud Migration Data Breach",
                    "claim_amount": "$1.2M",
                    "description": "During cloud migration services, a consulting firm inadvertently exposed client database credentials, leading to a data breach affecting 50,000 customers."
                }
            ],
            "cyber_liability": [
                {
                    "scenario": "Ransomware Attack on SaaS Platform",
                    "claim_amount": "$2.1M",
                    "description": "A ransomware attack encrypted customer data and demanded $500K ransom. Costs included forensics, notification, credit monitoring, and business interruption."
                },
                {
                    "scenario": "Employee Phishing Incident",
                    "claim_amount": "$480,000",
                    "description": "An employee fell for a phishing attack that compromised customer payment information, requiring breach notification and regulatory compliance costs."
                },
                {
                    "scenario": "Third-Party Vendor Data Breach",
                    "claim_amount": "$850,000",
                    "description": "A vendor's security failure exposed client data stored on their systems, triggering breach notification requirements and potential lawsuits."
                }
            ],
            "directors_officers": [
                {
                    "scenario": "Securities Class Action Lawsuit",
                    "claim_amount": "$3.2M",
                    "description": "Shareholders filed a lawsuit claiming management made misleading statements about company performance, resulting in stock price volatility."
                },
                {
                    "scenario": "Employment Discrimination Claim",
                    "claim_amount": "$650,000",
                    "description": "Former employee filed discrimination lawsuit against company executives, including claims of wrongful termination and hostile work environment."
                },
                {
                    "scenario": "Regulatory Investigation Defense",
                    "claim_amount": "$450,000",
                    "description": "SEC investigation into financial reporting practices required extensive legal defense and compliance consulting costs."
                }
            ],
            "general_liability": [
                {
                    "scenario": "Client Slip and Fall at Office",
                    "claim_amount": "$125,000",
                    "description": "A client visiting the company office slipped on wet floor and sustained injuries, requiring medical treatment and legal settlement."
                },
                {
                    "scenario": "Product Liability for Software Defect",
                    "claim_amount": "$380,000",
                    "description": "Software defect in IoT device caused property damage at customer location, triggering product liability claim."
                },
                {
                    "scenario": "Advertising Injury Lawsuit",
                    "claim_amount": "$200,000",
                    "description": "Competitor claimed company's marketing materials contained false statements about their products, leading to defamation lawsuit."
                }
            ]
        }
    
    def generate_risk_assessment_report(self, classification_data: Dict[str, Any], company_name: str) -> str:
        """Generate comprehensive risk assessment report using Classification API data"""
        try:
            # Import Embroker Knowledge Base for vector insights
            from integrations.embroker_knowledge_base import EmbrokerKnowledgeBase
            kb = EmbrokerKnowledgeBase()
            
            # Create structured prompt for reasoning model
            assessment_prompt = self._build_enhanced_assessment_prompt(classification_data, company_name, kb)
            
            # Generate risk assessment using reasoning model
            print(f"DEBUG: Generating risk assessment for {company_name}")
            print(f"DEBUG: Using model: {self.reasoning_model}")
            
            response = self.openai_client.chat.completions.create(
                model=self.reasoning_model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a professional senior risk manager at Embroker reviewing a company classification report. 
Generate comprehensive risk assessments with clear, professional language.

Generate a COMPREHENSIVE risk assessment report that includes:

1. EXECUTIVE SUMMARY OF CLASSIFICATION DATA WITH OPERATIONS SUMMARY
2. RISK MANAGER'S ANALYSIS 
3. COVERAGE RECOMMENDATIONS WITH JUSTIFICATIONS
4. CLAIM EXAMPLES SPECIFIC TO THE EMBROKER CLASS CODE

FORMAT:

=== EXECUTIVE SUMMARY ===
Company Name: [name]
Website: [url]
NAICS: [code] - [description]
Embroker Class Code: [code]
Confidence Score: [score]%
Risk Level: [from safety check]

Summary of Operations: [Include the full company summary from the API response that describes what the company does]

=== RISK MANAGER'S ANALYSIS ===
Based on the classification data, this company operates in [industry] with the following key risk factors:
• [Risk factor 1 with explanation]
• [Risk factor 2 with explanation]
• [Risk factor 3 with explanation]

=== COVERAGE RECOMMENDATIONS ===

1. TECH E&O/CYBER LIABILITY
Recommended Limit: $[amount]
Deductible: $[amount]
Justification: [Why this coverage is critical based on their business model and Embroker class code]
Key Coverages:
• [Coverage 1]
• [Coverage 2]
• [Coverage 3]
Claim Example for [Embroker Class Code]: [Real claim scenario specific to their class code with amount and description]
Embroker KB Insight: [Specific insight from knowledge base]

2. EMPLOYMENT PRACTICES LIABILITY (EPLI)
Recommended Limit: $[amount]
Deductible: $[amount]
Justification: [Why EPLI is important for this company's specific industry and size]
Key Coverages:
• [Coverage 1]
• [Coverage 2]
• [Coverage 3]
Claim Example for [Embroker Class Code]: [Real claim scenario specific to their class code with amount and description]
Embroker KB Insight: [Specific insight from knowledge base]

3. DIRECTORS & OFFICERS (D&O)
Recommended Limit: $[amount]
Deductible: $[amount]
Justification: [Why D&O coverage matters for this business type and structure]
Key Coverages:
• [Coverage 1]
• [Coverage 2]
• [Coverage 3]
Claim Example for [Embroker Class Code]: [Real claim scenario specific to their class code with amount and description]

4. GENERAL LIABILITY
Recommended Limit: $[amount] per occurrence / $[amount] aggregate
Deductible: $[amount]
Justification: [Why GL coverage is needed based on their operations]
Key Coverages:
• [Coverage 1]
• [Coverage 2]
• [Coverage 3]
Claim Example for [Embroker Class Code]: [Real claim scenario specific to their class code with amount and description]

=== ADDITIONAL COVERAGES ===
• Workers Compensation: [Recommendation based on business type]
• Commercial Property: [Recommendation based on assets]
• Commercial Auto: [If applicable]

IMPORTANT: Use specific dollar amounts, real claim examples specific to the Embroker class code, and insights from Embroker's knowledge base. Do NOT mention retentions."""
                    },
                    {
                        "role": "user",
                        "content": assessment_prompt
                    }
                ],
                max_completion_tokens=2000
            )
            
            risk_assessment = response.choices[0].message.content
            print(f"DEBUG: Raw LLM response length: {len(risk_assessment) if risk_assessment else 0}")
            print(f"DEBUG: First 200 chars of response: {risk_assessment[:200] if risk_assessment else 'EMPTY'}")
            
            return risk_assessment
            
        except Exception as e:
            print(f"Error generating risk assessment: {e}")
            import traceback
            traceback.print_exc()
            
            # No fallback report - only generate reports with actual API data
            raise ValueError(f"Cannot generate risk assessment without valid classification API data: {str(e)}")
    
    def _build_enhanced_assessment_prompt(self, classification_data: Dict[str, Any], company_name: str, kb: Any) -> str:
        """Build comprehensive prompt for risk assessment"""
        
        # Handle both direct classification data and nested format for backward compatibility
        if 'raw_classification_response' in classification_data:
            raw_response = classification_data.get('raw_classification_response', {})
        else:
            raw_response = classification_data
        
        # Validate that we have proper API data
        if not raw_response or not raw_response.get('naicsCode'):
            raise ValueError("Risk assessment cannot start - no classification API data received")
        
        # Get company details from the new API structure
        company_summary = raw_response.get('companySummary')
        naics_code = raw_response.get('naicsCode')
        naics_title = raw_response.get('naicsTitle')
        embroker_class_code = raw_response.get('embrokerClassCode', 'Not available')
        embroker_category = raw_response.get('embrokerCategory')
        confidence = raw_response.get('confidence')
        website_url = raw_response.get('websiteUrl', '')
        
        # Ensure we have all required fields
        if not all([naics_code, naics_title, embroker_category, company_summary]):
            raise ValueError("Incomplete classification data - missing required fields")
        
        # Get enhanced knowledge from vector database
        vector_context = self._get_vector_knowledge(company_name, naics_title)
        
        # Get vector insights for each coverage type (limit to first result to save tokens)
        tech_results = kb.search_embroker_knowledge(f"Tech E&O cyber coverage for {naics_title}")
        tech_insights = "Tech E&O coverage available"
        if tech_results and len(tech_results) > 0:
            # Extract content from metadata
            metadata = getattr(tech_results[0], 'metadata', {})
            tech_insights = metadata.get('text', metadata.get('content', 'Tech E&O coverage available'))[:200]
        
        epli_results = kb.search_embroker_knowledge(f"EPLI employment practices for {naics_title}")
        epli_insights = "EPLI coverage available"
        if epli_results and len(epli_results) > 0:
            metadata = getattr(epli_results[0], 'metadata', {})
            epli_insights = metadata.get('text', metadata.get('content', 'EPLI coverage available'))[:200]
        
        # Select class code specific claim examples
        embroker_category = raw_response.get('embrokerCategory', 'Technology')
        class_specific_claims = self.class_code_claims.get(embroker_category, self.class_code_claims.get('Technology', {}))
        
        # Build relevant claims with class-specific examples
        relevant_claims = {}
        if 'tech_eo' in class_specific_claims:
            relevant_claims['tech_eo'] = class_specific_claims['tech_eo'][:2]
        else:
            relevant_claims['tech_eo'] = self.claims_examples['tech_eo'][:2]
            
        if 'cyber_liability' in class_specific_claims:
            relevant_claims['cyber_liability'] = class_specific_claims['cyber_liability'][:1]
        else:
            relevant_claims['cyber_liability'] = self.claims_examples['cyber_liability'][:1]
            
        relevant_claims['directors_officers'] = self.claims_examples['directors_officers'][:1]
        relevant_claims['general_liability'] = self.claims_examples['general_liability'][:1]
        
        prompt = f"""
You are a senior risk manager at Embroker reviewing a company classification report. 

CLASSIFICATION DATA:
Company: {company_name}
Website: {website_url}
NAICS: {naics_code} - {naics_title}
Embroker Class: {embroker_class_code}
Category: {embroker_category}
Summary: {company_summary}
Confidence: {confidence}%
Risk Level: {raw_response.get('safetyCheck', {}).get('overallRisk', 'Unknown')}

SAMPLE CLAIM SCENARIOS:
{json.dumps(relevant_claims, indent=2)}

VECTOR INSIGHTS:
Tech E&O: {tech_insights}
EPLI: {epli_insights}

Generate a comprehensive risk assessment report following the exact format in your instructions. Include the executive summary with operations summary, risk analysis, and coverage recommendations with claim examples specific to the Embroker class code and justifications."""
        return prompt
    

    
    def _get_vector_knowledge(self, company_name: str, industry: str) -> str:
        """Get relevant knowledge from vector database with focus on Embroker products"""
        try:
            # Try to import vector knowledge - gracefully handle if not available
            try:
                from integrations.rag_pinecone import EmbrokerKnowledgeBase
                knowledge_base = EmbrokerKnowledgeBase()
            except ImportError:
                try:
                    from integrations.rag_pinecone import InsuranceKnowledgeAgent
                    knowledge_base = InsuranceKnowledgeAgent()
                except ImportError:
                    # Return basic knowledge if vector system not available
                    return "## Embroker Knowledge: Professional insurance solutions available including Tech E&O, Cyber Liability, EPLI, and D&O coverage."

            
            # Enhanced search queries focusing on Embroker products
            search_queries = [
                "Embroker Tech E&O technology errors omissions coverage",
                "Embroker Cyber Liability data breach insurance",
                "Embroker EPLI employment practices liability insurance", 
                "Embroker D&O directors officers liability coverage",
                f"Embroker {industry} insurance requirements",
                "Embroker general liability commercial insurance",
                "Embroker professional liability limits deductibles",
                "Embroker insurance products technology companies"
            ]
            
            vector_context = "## Embroker Product Knowledge Highlights:\n\n"
            
            # Track unique content to avoid duplicates
            seen_content = set()
            
            for query in search_queries:
                try:
                    results = knowledge_base.search_embroker_knowledge(query, top_k=5)
                    if results and len(results) > 0:
                        has_new_content = False
                        section_content = ""
                        
                        for result in results[:3]:  # Top 3 results per query
                            content = result.get('content', result.get('metadata', {}).get('content', ''))
                            if content and len(content) > 50:
                                # Extract key information and avoid duplicates
                                content_preview = content[:500]
                                content_hash = hash(content_preview[:100])
                                
                                if content_hash not in seen_content:
                                    seen_content.add(content_hash)
                                    has_new_content = True
                                    
                                    # Extract specific product details
                                    if any(term in content.lower() for term in ['tech e&o', 'technology errors', 'professional liability']):
                                        section_content += f"**Tech E&O/Professional Liability**: {content_preview}\n\n"
                                    elif any(term in content.lower() for term in ['cyber', 'data breach', 'network security']):
                                        section_content += f"**Cyber Liability**: {content_preview}\n\n"
                                    elif any(term in content.lower() for term in ['epli', 'employment practices']):
                                        section_content += f"**EPLI Coverage**: {content_preview}\n\n"
                                    elif any(term in content.lower() for term in ['d&o', 'directors', 'officers']):
                                        section_content += f"**D&O Insurance**: {content_preview}\n\n"
                                    else:
                                        section_content += f"- {content_preview}\n\n"
                        
                        if has_new_content:
                            vector_context += section_content
                            
                except Exception as e:
                    print(f"Error searching for {query}: {e}")
                    continue
            
            # Ensure key products are mentioned
            if "Tech E&O" not in vector_context:
                vector_context += "\n**Tech E&O/Professional Liability**: Comprehensive coverage for technology errors, omissions, and professional services failures. Includes network security and privacy liability.\n\n"
            
            if "EPLI" not in vector_context:
                vector_context += "**EPLI**: Employment Practices Liability Insurance protecting against wrongful termination, discrimination, and harassment claims.\n\n"
            
            if "D&O" not in vector_context:
                vector_context += "**D&O Insurance**: Directors & Officers liability coverage for management decisions, including entity coverage and employment practices defense.\n\n"
            
            return vector_context
            
        except Exception as e:
            print(f"Error getting vector knowledge: {e}")
            return "## Embroker Knowledge: Core products include Tech E&O/Cyber Liability, EPLI, D&O, and General Liability coverage tailored for technology companies."
    
    def _format_assessment_report(self, assessment: str, company_name: str, classification_data: Dict[str, Any]) -> str:
        """Format the assessment into a clean, professional report"""
        
        # Return the clean assessment without adding any markdown formatting
        return assessment
    
    def _get_relevant_claims_examples(self, assessment: str) -> str:
        """Extract relevant claims examples based on assessment content"""
        
        claims_section = "### Relevant Claims Scenarios\n\n"
        
        # Check which products are mentioned in the assessment
        products_mentioned = []
        if "tech" in assessment.lower() or "e&o" in assessment.lower() or "errors" in assessment.lower():
            products_mentioned.append("tech_eo")
        if "cyber" in assessment.lower() or "data breach" in assessment.lower():
            products_mentioned.append("cyber_liability")
        if "epli" in assessment.lower() or "employment" in assessment.lower():
            products_mentioned.append("epli")
        if "director" in assessment.lower() or "d&o" in assessment.lower():
            products_mentioned.append("directors_officers")
        if "general liability" in assessment.lower() or "bodily injury" in assessment.lower():
            products_mentioned.append("general_liability")
        
        # Default to tech E&O and cyber if nothing specific mentioned
        if not products_mentioned:
            products_mentioned = ["tech_eo", "cyber_liability"]
        
        # Add relevant claims examples
        for product in products_mentioned:
            if product in self.claims_examples:
                product_name = self.embroker_products[product]["name"]
                claims_section += f"**{product_name} Claims Examples:**\n\n"
                
                for claim in self.claims_examples[product][:2]:  # Show top 2 examples
                    claims_section += f"• **{claim['scenario']}** - *Claim Amount: {claim['claim_amount']}*\n"
                    claims_section += f"  {claim['description']}\n\n"
        
        return claims_section
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp for report"""
        from datetime import datetime
        return datetime.now().strftime("%B %d, %Y at %I:%M %p")
    
    def get_assessment_status(self) -> Dict[str, Any]:
        """Get agent status"""
        return {
            "agent_type": "Risk Assessment Agent",
            "model": self.reasoning_model,
            "products_available": len(self.embroker_products),
            "claims_examples": sum(len(examples) for examples in self.claims_examples.values()),
            "status": "operational"
        }

# Global agent instance
_risk_assessment_agent = None

def get_risk_assessment_agent():
    """Get or create the global risk assessment agent instance"""
    global _risk_assessment_agent
    if _risk_assessment_agent is None:
        _risk_assessment_agent = RiskAssessmentAgent()
    return _risk_assessment_agent

def generate_risk_report(classification_data: Dict[str, Any], company_name: str) -> str:
    """Main entry point for generating risk assessment reports"""
    agent = get_risk_assessment_agent()
    return agent.generate_risk_assessment_report(classification_data, company_name)