"""
Risk Report Formatter Agent
Formats raw risk assessment reports into clean, structured HTML using AI
"""

import os
from openai import OpenAI

class RiskFormatterAgent:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("POC_OPENAI_API"))
        
    def format_risk_report(self, raw_report_text):
        """Format raw risk assessment text into clean HTML using AI"""
        
        system_prompt = """You are a professional document formatter specializing in insurance risk reports.
Your task is to convert raw risk assessment text into clean, well-structured HTML.

IMPORTANT FORMATTING RULES:
1. Use minimal, clean HTML with simple styling that matches a chat interface
2. Structure the report with clear sections using appropriate HTML tags
3. Use these CSS classes for consistency:
   - executive-summary: For the executive summary section
   - risk-analysis: For risk analysis section
   - coverage-grid: Container for coverage cards
   - coverage-card: Individual coverage recommendation cards
   - limit-amount: For highlighting coverage amounts
   - claim-example: For claim example boxes
   - api-response-section: For API response data

4. Format coverage recommendations as individual cards in a grid
5. Highlight important amounts and limits
6. Keep styling minimal and professional
7. Use semantic HTML tags (h2, h3, p, etc.)
8. Do NOT include any inline styles or complex formatting
9. Return ONLY the HTML content, no markdown or explanations

Example structure:
<div class="executive-summary">
  <h2>Executive Summary</h2>
  <p>Content here...</p>
</div>

<div class="risk-analysis">
  <h2>Risk Analysis</h2>
  <p>Content here...</p>
</div>

<h2>Coverage Recommendations</h2>
<div class="coverage-grid">
  <div class="coverage-card">
    <h3>Coverage Type</h3>
    <p>Description...</p>
    <p>Limit: <span class="limit-amount">$1,000,000</span></p>
  </div>
</div>"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Format this risk assessment report into clean HTML:\n\n{raw_report_text}"}
                ],
                temperature=0.3,
                max_tokens=4000
            )
            
            formatted_html = response.choices[0].message.content.strip()
            
            # Ensure we only return HTML, remove any markdown code blocks if present
            if formatted_html.startswith("```html"):
                formatted_html = formatted_html.replace("```html", "").replace("```", "").strip()
            elif formatted_html.startswith("```"):
                formatted_html = formatted_html.replace("```", "").strip()
            
            return formatted_html
            
        except Exception as e:
            print(f"Error formatting risk report: {e}")
            # Fallback to basic formatting if AI fails
            return self._basic_format_fallback(raw_report_text)
    
    def _basic_format_fallback(self, text):
        """Basic fallback formatting if AI formatting fails"""
        lines = text.split('\n')
        html = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            elif 'EXECUTIVE SUMMARY' in line:
                html.append('<div class="executive-summary"><h2>Executive Summary</h2>')
            elif 'RISK ANALYSIS' in line or "RISK MANAGER'S ANALYSIS" in line:
                if html and '</div>' not in html[-1]:
                    html.append('</div>')
                html.append('<div class="risk-analysis"><h2>Risk Analysis</h2>')
            elif 'COVERAGE RECOMMENDATIONS' in line:
                if html and '</div>' not in html[-1]:
                    html.append('</div>')
                html.append('<h2>Coverage Recommendations</h2><div class="coverage-grid">')
            elif line.startswith('•'):
                # Start of coverage item
                html.append('<div class="coverage-card">')
                html.append(f'<h3>{line[1:].strip()}</h3>')
            elif '$' in line and any(word in line.lower() for word in ['limit', 'coverage', 'deductible']):
                # Highlight amounts
                import re
                formatted = re.sub(r'\$([0-9,]+)', r'<span class="limit-amount">$\1</span>', line)
                html.append(f'<p>{formatted}</p>')
            else:
                html.append(f'<p>{line}</p>')
        
        # Close any open divs
        if html and '</div>' not in html[-1]:
            html.append('</div>')
        if '<div class="coverage-grid">' in ' '.join(html) and not html[-1].endswith('</div>'):
            html.append('</div>')
            
        return '\n'.join(html)

# Global instance
_formatter_agent = None

def get_formatter_agent():
    """Get or create the global risk formatter agent instance"""
    global _formatter_agent
    if _formatter_agent is None:
        _formatter_agent = RiskFormatterAgent()
    return _formatter_agent