# underwriting_agent.py
"""
Specialized Underwriting Agent for Embroker insurance decisions
Handles eligibility analysis, risk assessment, and underwriting guidelines
"""

import json
from typing import Dict, Any, List, Optional
from openai import OpenAI
import os
from integrations.openai_vector_store import OpenAIVectorStore

class UnderwritingAgent:
    """Specialized agent for underwriting decisions and risk assessment"""
    
    def __init__(self):
        """Initialize underwriting agent with specialized knowledge"""
        self.openai_client = OpenAI(api_key=os.getenv("POC_OPENAI_API"))
        self.vector_store = OpenAIVectorStore()
        self.model = "o4-mini-2025-04-16"
        
        # Underwriting decision thresholds
        self.risk_thresholds = {
            "high_risk_keywords": ["cryptocurrency", "cannabis", "blockchain", "adult", "gambling"],
            "requires_review": ["fintech", "healthcare", "insurance", "medical devices"],
            "automatic_decline": ["cannabis", "cryptocurrency", "adult entertainment", "online gaming"]
        }
    
    async def analyze_underwriting_eligibility(self, company_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive underwriting eligibility analysis
        
        Args:
            company_info: Dictionary containing company details
            
        Returns:
            Underwriting decision with reasoning and recommendations
        """
        
        company_name = company_info.get("name", "")
        industry = company_info.get("industry", "")
        business_description = company_info.get("description", "")
        revenue = company_info.get("revenue", 0)
        employee_count = company_info.get("employees", 0)
        
        # Step 1: Check against automatic decline criteria
        decline_reason = self._check_automatic_decline(industry, business_description)
        if decline_reason:
            return {
                "decision": "decline",
                "confidence": 0.95,
                "reason": decline_reason,
                "recommendation": "Refer to business development for appetite expansion consideration",
                "next_steps": ["Document decline reason", "Add to CRM with decline flag"]
            }
        
        # Step 2: Search knowledge base for specific industry guidelines
        industry_guidelines = await self._get_industry_guidelines(industry)
        
        # Step 3: Assess risk factors
        risk_assessment = self._assess_risk_factors(company_info, industry_guidelines)
        
        # Step 4: Check if requires additional review
        requires_review = self._requires_additional_review(industry, business_description, risk_assessment)
        
        # Step 5: Make final underwriting decision
        decision = await self._make_underwriting_decision(
            company_info, risk_assessment, industry_guidelines, requires_review
        )
        
        return decision
    
    def _check_automatic_decline(self, industry: str, description: str) -> Optional[str]:
        """Check if company meets automatic decline criteria"""
        
        combined_text = f"{industry} {description}".lower()
        
        for keyword in self.risk_thresholds["automatic_decline"]:
            if keyword in combined_text:
                return f"Automatic decline: {keyword} industry outside of Embroker appetite"
        
        return None
    
    async def _get_industry_guidelines(self, industry: str) -> str:
        """Retrieve industry-specific underwriting guidelines from knowledge base"""
        
        query = f"underwriting guidelines {industry} industry eligibility criteria"
        guidelines = self.vector_store.search_knowledge_base(query)
        return guidelines
    
    def _assess_risk_factors(self, company_info: Dict[str, Any], guidelines: str) -> Dict[str, Any]:
        """Assess various risk factors for the company"""
        
        risk_factors = {
            "industry_risk": "low",
            "size_risk": "low",
            "operational_risk": "low",
            "financial_risk": "low",
            "overall_risk": "low"
        }
        
        # Assess industry risk
        industry = company_info.get("industry", "").lower()
        if any(keyword in industry for keyword in self.risk_thresholds["high_risk_keywords"]):
            risk_factors["industry_risk"] = "high"
        elif any(keyword in industry for keyword in self.risk_thresholds["requires_review"]):
            risk_factors["industry_risk"] = "medium"
        
        # Assess size risk
        revenue = company_info.get("revenue", 0)
        employees = company_info.get("employees", 0)
        
        if revenue > 100000000 or employees > 500:  # Large company
            risk_factors["size_risk"] = "medium"
        elif revenue < 100000 or employees < 5:  # Very small company
            risk_factors["size_risk"] = "medium"
        
        # Calculate overall risk
        risk_levels = list(risk_factors.values())[:-1]  # Exclude overall_risk
        if "high" in risk_levels:
            risk_factors["overall_risk"] = "high"
        elif "medium" in risk_levels:
            risk_factors["overall_risk"] = "medium"
        
        return risk_factors
    
    def _requires_additional_review(self, industry: str, description: str, risk_assessment: Dict[str, Any]) -> bool:
        """Determine if application requires additional underwriter review"""
        
        # High risk always requires review
        if risk_assessment["overall_risk"] == "high":
            return True
        
        # Specific industries require review
        combined_text = f"{industry} {description}".lower()
        for keyword in self.risk_thresholds["requires_review"]:
            if keyword in combined_text:
                return True
        
        return False
    
    async def _make_underwriting_decision(self, company_info: Dict[str, Any], 
                                        risk_assessment: Dict[str, Any],
                                        guidelines: str, requires_review: bool) -> Dict[str, Any]:
        """Make final underwriting decision using AI analysis"""
        
        decision_prompt = f"""
        You are an expert Embroker underwriter making an eligibility decision. Analyze the following:
        
        Company Information:
        - Name: {company_info.get('name', 'N/A')}
        - Industry: {company_info.get('industry', 'N/A')}
        - Description: {company_info.get('description', 'N/A')}
        - Revenue: ${company_info.get('revenue', 0):,}
        - Employees: {company_info.get('employees', 0)}
        
        Risk Assessment:
        {json.dumps(risk_assessment, indent=2)}
        
        Industry Guidelines:
        {guidelines}
        
        Requires Additional Review: {requires_review}
        
        Make an underwriting decision. Respond with JSON in this format:
        {{
            "decision": "accept|conditional|review|decline",
            "confidence": 0.0-1.0,
            "reason": "detailed explanation",
            "conditions": ["any conditions for acceptance"],
            "recommendation": "next steps recommendation",
            "coverage_types": ["recommended coverage types"],
            "estimated_premium_range": "premium estimate if applicable"
        }}
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert Embroker underwriter. Provide decisions in JSON format only."},
                    {"role": "user", "content": decision_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=800
            )
            
            decision = json.loads(response.choices[0].message.content)
            
            # Add additional metadata
            decision["risk_assessment"] = risk_assessment
            decision["requires_human_review"] = requires_review
            decision["timestamp"] = time.time()
            
            return decision
            
        except Exception as e:
            # Fallback decision
            return {
                "decision": "review",
                "confidence": 0.5,
                "reason": f"Unable to complete automated analysis: {str(e)}",
                "recommendation": "Forward to human underwriter for manual review",
                "requires_human_review": True
            }
    
    async def get_class_code_eligibility(self, class_code: str, business_description: str = "") -> Dict[str, Any]:
        """Check eligibility for specific class code"""
        
        query = f"class code {class_code} eligibility requirements {business_description}"
        guidelines = self.vector_store.search_knowledge_base(query)
        
        eligibility_prompt = f"""
        Analyze eligibility for class code {class_code} with business description: {business_description}
        
        Guidelines from knowledge base:
        {guidelines}
        
        Determine if this class code is:
        1. Accepted by Embroker
        2. Requires additional review
        3. Outside appetite (declined)
        
        Respond with JSON format including decision, reason, and any conditions.
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an Embroker underwriting specialist analyzing class code eligibility."},
                    {"role": "user", "content": eligibility_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=600
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            return {
                "decision": "review",
                "reason": f"Unable to analyze class code: {str(e)}",
                "recommendation": "Contact underwriting team for manual review"
            }
    
    def get_underwriting_status(self) -> Dict[str, Any]:
        """Get underwriting agent status and statistics"""
        return {
            "agent_type": "underwriting",
            "model": self.model,
            "risk_thresholds": self.risk_thresholds,
            "vector_store_available": self.vector_store.is_available()
        }

# Import time for timestamps
import time

# Global underwriting agent instance
_underwriting_agent = None

def get_underwriting_agent():
    """Get or create the global underwriting agent instance"""
    global _underwriting_agent
    if _underwriting_agent is None:
        _underwriting_agent = UnderwritingAgent()
    return _underwriting_agent

async def analyze_underwriting_eligibility(company_info: Dict[str, Any]) -> Dict[str, Any]:
    """Main entry point for underwriting analysis"""
    agent = get_underwriting_agent()
    return await agent.analyze_underwriting_eligibility(company_info)