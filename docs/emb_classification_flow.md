# Embroker Classification API Flow

## 1. USER REGISTRATION TRIGGERS API CALL
```
User registers with:
- Company Name: "TechCorp Inc"
- Email: john@techcorp.com
```

## 2. BACKGROUND AGENT EXTRACTS DATA
**File:** `agents/background_agent.py`

```python
# Extract domain from email
website_url = "https://techcorp.com"  # Extracted from john@techcorp.com
company_name = "TechCorp Inc"
```

## 3. API REQUEST TO EMB_CLASSIFICATION
**Endpoint:** `https://emb-classification.onrender.com/classify?skip_safety=false`

**Request Payload:**
```json
{
    "companyName": "TechCorp Inc",
    "websiteUrl": "https://techcorp.com"
}
```

**Method:** `_analyze_via_website()` (lines 119-130)

## 4. API RESPONSE RECEIVED
**Example Response:**
```json
{
    "companyName": "TechCorp Inc",
    "websiteUrl": "https://techcorp.com",
    "naicsCode": "541511",
    "naicsTitle": "Custom Computer Programming Services",
    "embrokerClassCode": "91362",
    "embrokerCategory": "Eligible",
    "companySummary": "TechCorp Inc provides custom software development and IT consulting services...",
    "confidence": 83.8,
    "routingDecision": "auto_route",
    "analysis": {
        "industry": "Technology",
        "riskFactors": ["cyber", "professional_liability"],
        "recommendedProducts": ["Tech E&O", "Cyber", "D&O"]
    }
}
```

## 5. RESPONSE CACHED
**Location:** `background_agent.py` line 92
```python
self.analysis_cache[company_key] = json.dumps({
    'company_name': 'TechCorp Inc',
    'website_url': 'https://techcorp.com',
    'raw_classification_response': <API_RESPONSE>,  # Full response stored here
    'formatted_summary': <FORMATTED_TEXT>,
    'timestamp': '2025-07-19 12:00:00',
    'source': 'Embroker Classification API'
})
```

## 6. RISK ASSESSMENT RETRIEVES DATA
**File:** `app.py` lines 984-992

```python
# Get cached analysis
background_analysis = company_agent.get_analysis(company_name)

# Parse JSON to extract classification data
analysis_json = json.loads(background_analysis)
classification_data = analysis_json.get('raw_classification_response')
```

## 7. RISK ASSESSMENT AGENT USES DATA
**File:** `agents/risk_assessment_agent.py` line 156

```python
def generate_risk_assessment_report(self, classification_data: Dict[str, Any], company_name: str):
    # classification_data contains the full API response
    # Used to generate customized risk report with:
    # - NAICS code from API
    # - Embroker class code from API  
    # - Company summary from API
    # - Risk-based product recommendations
```

## 8. FINAL RISK REPORT GENERATED
```
Company Name: TechCorp Inc
Website: https://techcorp.com
NAICS: 541511 - Custom Computer Programming Services
Embroker Class Code: 91362
Summary of Operations: TechCorp Inc provides custom software development...

RECOMMENDATIONS
Tech E&O/Cyber
• Limit: $3M
• Retention: $10,000
...
```

## KEY POINTS:
1. **API is called ONCE** during user registration
2. **Full response is cached** for reuse
3. **Risk assessment REQUIRES** this API data
4. **Fallback exists** if API fails (lines 994-1017 in app.py)
5. **Vector search enhances** recommendations but API provides core classification