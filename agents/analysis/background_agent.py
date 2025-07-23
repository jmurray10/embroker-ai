# background_agent.py
import threading
import requests
import time
import json
from typing import Dict, Optional

class CompanyAnalysisAgent:
    def __init__(self):
        """
        Initialize company analysis agent with caching and background processing.
        """
        self.analysis_cache: Dict[str, str] = {}
        self.pending_requests: Dict[str, float] = {}  # Track request timestamps
        self.cache_expiry = 3600  # Cache expires after 1 hour
        self.request_timeout = 30  # Timeout for external API calls

    def get_analysis(self, company: str) -> str:
        """
        Get company analysis, either from cache or by triggering background fetch.
        
        Args:
            company: Company name to analyze
            
        Returns:
            Analysis result or status message
        """
        if not company:
            return ""
            
        company_key = company.lower().strip()
        
        # Check if we have cached analysis
        if company_key in self.analysis_cache:
            return self.analysis_cache[company_key]
        
        # Check if request is already pending
        if company_key in self.pending_requests:
            elapsed = time.time() - self.pending_requests[company_key]
            if elapsed < self.request_timeout:
                return f"Company analysis for {company} is being prepared, please ask again in a moment."
            else:
                # Remove stale pending request
                del self.pending_requests[company_key]
        
        # Start background analysis
        self.pending_requests[company_key] = time.time()
        threading.Thread(
            target=self._fetch_analysis, 
            args=(company_key, company, None, None), 
            daemon=True
        ).start()
        
        return f"Company analysis for {company} is being prepared, please ask again in a moment."

    def _fetch_analysis(self, company_key: str, original_company_name: str, company_email: str = None, conversation_id: str = None):
        """
        Fetch company analysis from NAIC API using company name and email domain.
        
        Args:
            company_key: Normalized company name for caching
            original_company_name: Original company name for API call
            company_email: Company email to extract domain for website analysis
            conversation_id: Conversation ID for user notifications
        """
        try:
            # Extract domain from company email for website analysis
            website_url = None
            if company_email and '@' in company_email:
                domain = company_email.split('@')[1].lower()
                website_url = f"https://{domain}"
            
            # Try website analysis first if email domain available
            analysis_result = None
            if website_url:
                analysis_result = self._analyze_via_website(website_url)
            
            # Fallback to company name analysis if website analysis fails
            if not analysis_result:
                analysis_result = self._analyze_via_company_name(original_company_name)
            
            if analysis_result:
                # Store complete raw API response for LLM use
                complete_analysis = {
                    'company_name': original_company_name,
                    'website_url': website_url,
                    'raw_classification_response': analysis_result,
                    'formatted_summary': self._format_analysis(analysis_result, original_company_name, website_url),
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'source': 'Embroker Classification API'
                }
                cache_data = json.dumps(complete_analysis, indent=2)
                self.analysis_cache[company_key] = cache_data
                print(f"[BACKGROUND AGENT] Stored analysis data, length: {len(cache_data)}, starts with: {cache_data[:100]}...")
                
                # Analysis complete - no chat notification needed (reports available in menu)
                    
            else:
                self.analysis_cache[company_key] = f"Company analysis for {original_company_name} requires manual underwriter review."
                
                # Analysis complete - no chat notification needed (reports available in menu)
                
        except Exception as e:
            # Silent error handling for clean interface
            self.analysis_cache[company_key] = f"Analysis for {original_company_name} encountered an issue. Manual review recommended."
            
            # Analysis complete - no chat notification needed (reports available in menu)
                
        finally:
            # Always remove from pending requests
            if company_key in self.pending_requests:
                del self.pending_requests[company_key]

    def _analyze_via_website(self, website_url: str) -> Optional[Dict]:
        """Analyze company via website URL using Embroker Classification API."""
        try:
            # Extract company name from website URL for the API
            domain = website_url.replace('https://', '').replace('http://', '').replace('www.', '')
            company_name = domain.split('.')[0].title()
            
            api_data = {
                "companyName": company_name,
                "websiteUrl": website_url
            }
            print(f"[BACKGROUND AGENT] Calling classification API with: {json.dumps(api_data)}")
            
            response = requests.post(
                "https://emb-classification.onrender.com/classify?skip_safety=false",
                headers={
                    "accept": "application/json", 
                    "Content-Type": "application/json"
                },
                json=api_data,
                timeout=self.request_timeout
            )
            
            print(f"[BACKGROUND AGENT] API response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"[BACKGROUND AGENT] API returned data, NAICS: {result.get('naicsCode')}")
                return result
            else:
                print(f"[BACKGROUND AGENT] API error: {response.text}")
            return None
        except requests.exceptions.Timeout:
            print(f"[BACKGROUND AGENT] API timeout after {self.request_timeout} seconds")
            return None
        except Exception as e:
            print(f"[BACKGROUND AGENT] API error: {str(e)}")
            return None

    def _analyze_via_company_name(self, company_name: str) -> Optional[Dict]:
        """Analyze company via company name using Embroker Classification API."""
        try:
            # Create a reasonable website URL from company name
            website_url = f"https://{company_name.lower().replace(' ', '').replace(',', '').replace('.', '')}.com"
            
            response = requests.post(
                "https://emb-classification.onrender.com/classify?skip_safety=false",
                headers={
                    "accept": "application/json", 
                    "Content-Type": "application/json"
                },
                json={
                    "companyName": company_name,
                    "websiteUrl": website_url
                },
                timeout=self.request_timeout
            )
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None

    def _format_analysis(self, result: Dict, company_name: str, website_url: Optional[str] = None) -> str:
        """Format Embroker Classification API result into readable analysis."""
        try:
            analysis_parts = [f"Company Analysis for {company_name}:"]
            
            if website_url:
                analysis_parts.append(f"Website: {website_url}")
            
            # Extract key information from Embroker Classification API response
            if isinstance(result, dict):
                # Add industry classification if available
                if 'classification' in result:
                    industry = result.get('classification', 'Unknown')
                    analysis_parts.append(f"Industry Classification: {industry}")
                
                # Add business description if available
                if 'description' in result:
                    desc = result.get('description', '')
                    if desc:
                        analysis_parts.append(f"Business Description: {desc}")
                
                # Add risk factors if available
                if 'risk_factors' in result:
                    risk_factors = result.get('risk_factors', [])
                    if risk_factors:
                        analysis_parts.append(f"Risk Factors: {', '.join(risk_factors)}")
                
                # Add recommended coverage based on classification
                if 'recommended_coverage' in result:
                    coverage = result.get('recommended_coverage', [])
                    if coverage:
                        analysis_parts.append(f"Recommended Coverage: {', '.join(coverage)}")
                
                # Add confidence score if available
                if 'confidence' in result:
                    confidence = result.get('confidence', 0)
                    analysis_parts.append(f"Classification Confidence: {confidence:.2f}")
                elif 'healthcare' in industry_lower or 'medical' in industry_lower:
                    analysis_parts.append("Recommended Coverage: Medical Professional Liability")
                else:
                    analysis_parts.append("Recommended Coverage: General Liability with industry-specific addons")
                
                # Add raw data for underwriter reference
                analysis_parts.append(f"Source: Embroker Classification API")
                analysis_parts.append(f"Analysis completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            return "\n".join(analysis_parts)
            
        except Exception as e:
            return f"Company analysis for {company_name} completed with limited data. Manual underwriter review recommended."

    def start_background_analysis(self, company_name: str, company_email: str, conversation_id: str = None) -> None:
        """Start background analysis immediately for registration workflow."""
        if not company_name:
            return
            
        company_key = company_name.lower().strip()
        
        # Skip if already cached or pending
        if company_key in self.analysis_cache or company_key in self.pending_requests:
            return
        
        # Background analysis starting - no chat notification needed
        
        # Start immediate background analysis
        self.pending_requests[company_key] = time.time()
        threading.Thread(
            target=self._fetch_analysis, 
            args=(company_key, company_name, company_email, conversation_id), 
            daemon=True
        ).start()
    
    def store_classification_data(self, company_name: str, classification_data: Dict) -> None:
        """
        Store classification API data for a company.
        
        Args:
            company_name: Company name
            classification_data: Classification data from API
        """
        company_key = company_name.lower().strip()
        
        # Store the complete classification response as JSON
        import json
        self.analysis_cache[company_key] = json.dumps({
            'raw_classification_response': classification_data,
            'stored_at': time.time()
        })
        
        # Remove from pending if exists
        if company_key in self.pending_requests:
            del self.pending_requests[company_key]

    def clear_cache(self):
        """Clear the analysis cache."""
        self.analysis_cache.clear()
        self.pending_requests.clear()

    def get_cache_status(self) -> Dict[str, int]:
        """Get current cache status for monitoring."""
        return {
            "cached_analyses": len(self.analysis_cache),
            "pending_requests": len(self.pending_requests)
        }
    
    def _queue_notification(self, conversation_id: str, message: str) -> None:
        """Queue notification for user about analysis status"""
        try:
            import json
            import os
            
            # Store notification for delivery via check-messages endpoint
            notification_file = f".analysis_notification_{conversation_id}.json"
            notification_data = {
                "message": message,
                "timestamp": time.time(),
                "conversation_id": conversation_id,
                "type": "analysis_notification"
            }
            
            with open(notification_file, 'w') as f:
                json.dump(notification_data, f)
            print(f"Notification queued: {message}")
                
        except Exception as e:
            print(f"Error queuing notification: {e}")

# Global instance
_company_agent = None

def get_company_agent():
    """Get or create the global company analysis agent instance"""
    global _company_agent
    if _company_agent is None:
        _company_agent = CompanyAnalysisAgent()
    return _company_agent