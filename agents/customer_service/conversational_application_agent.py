"""
Conversational Insurance Application Agent
Guides users through insurance applications using chat interface with NAIC background data
"""

import os
import json
import time
from typing import Dict, List, Optional, Any
from openai import OpenAI
from dataclasses import dataclass

@dataclass
class ApplicationSection:
    """Represents a section of the insurance application"""
    name: str
    fields: List[Dict[str, Any]]
    completed: bool = False
    current_field_index: int = 0

@dataclass
class ApplicationState:
    """Tracks the current state of application completion"""
    conversation_id: str
    company_name: str
    applicant_name: str
    sections: List[ApplicationSection]
    current_section_index: int = 0
    completed_fields: Dict[str, Any] = None
    naic_data: Optional[Dict[str, Any]] = None
    started_at: float = None
    
    def __post_init__(self):
        if self.completed_fields is None:
            self.completed_fields = {}
        if self.started_at is None:
            self.started_at = time.time()

class ConversationalApplicationAgent:
    """Agent for completing insurance applications through conversational interface"""
    
    def __init__(self):
        """Initialize the conversational application agent"""
        # Initialize OpenAI client
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.openai_client = OpenAI(api_key=api_key)
        self.model = "gpt-4o"
        
        # Application state storage
        self.active_applications = {}
        
        # Define application sections based on insurance forms
        self.application_template = self._create_application_template()
        
    def _create_application_template(self) -> List[ApplicationSection]:
        """Create template for Tech E&O insurance application"""
        return [
            ApplicationSection(
                name="Company Profile",
                fields=[
                    {"name": "legal_name", "question": "What is your company's full legal name?", "type": "text", "required": True},
                    {"name": "dba_name", "question": "Do you operate under a different business name (DBA)?", "type": "text", "required": False},
                    {"name": "website", "question": "What is your company website URL?", "type": "text", "required": True},
                    {"name": "business_description", "question": "How does your company generate revenue? Please describe your main business activities.", "type": "text", "required": True, "use_naic": True},
                    {"name": "industry_classification", "question": "What industry category best describes your business?", "type": "text", "required": True, "use_naic": True},
                    {"name": "years_in_business", "question": "How many years has your company been in operation?", "type": "number", "required": True},
                    {"name": "employee_count", "question": "How many full-time employees does your company currently have?", "type": "number", "required": True},
                    {"name": "contractor_count", "question": "How many contractors or part-time employees work for your company?", "type": "number", "required": False},
                    {"name": "annual_revenue", "question": "What was your company's annual revenue for the most recent fiscal year?", "type": "currency", "required": True},
                    {"name": "projected_revenue", "question": "What is your projected annual revenue for the current fiscal year?", "type": "currency", "required": True}
                ]
            ),
            ApplicationSection(
                name="Technology & Security",
                fields=[
                    {"name": "primary_technology", "question": "What is your primary technology stack or platform?", "type": "text", "required": True},
                    {"name": "cloud_services", "question": "Which cloud services do you use? (AWS, Google Cloud, Azure, etc.)", "type": "text", "required": True},
                    {"name": "data_storage", "question": "Where and how do you store customer data?", "type": "text", "required": True},
                    {"name": "security_measures", "question": "What security measures do you have in place? (MFA, encryption, firewalls, etc.)", "type": "text", "required": True},
                    {"name": "backup_procedures", "question": "How frequently do you backup data and test recovery procedures?", "type": "text", "required": True},
                    {"name": "access_controls", "question": "How do you manage user access and permissions?", "type": "text", "required": True},
                    {"name": "incident_response", "question": "Do you have an incident response plan in place?", "type": "boolean", "required": True},
                    {"name": "security_training", "question": "Do you provide cybersecurity training to employees?", "type": "boolean", "required": True}
                ]
            ),
            ApplicationSection(
                name="Data & Privacy",
                fields=[
                    {"name": "data_types", "question": "What types of personal or sensitive data do you collect or process?", "type": "text", "required": True},
                    {"name": "data_retention", "question": "How long do you retain customer data?", "type": "text", "required": True},
                    {"name": "third_party_sharing", "question": "Do you share data with third parties? If yes, please describe.", "type": "text", "required": True},
                    {"name": "privacy_policy", "question": "Do you have a published privacy policy?", "type": "boolean", "required": True},
                    {"name": "gdpr_compliance", "question": "Are you subject to GDPR or other data protection regulations?", "type": "boolean", "required": True},
                    {"name": "data_breach_procedures", "question": "What procedures do you have for handling data breaches?", "type": "text", "required": True}
                ]
            ),
            ApplicationSection(
                name="Claims & Risk History",
                fields=[
                    {"name": "previous_claims", "question": "Have you ever filed an E&O or cyber liability insurance claim?", "type": "boolean", "required": True},
                    {"name": "security_incidents", "question": "Have you experienced any security breaches or cyber incidents in the past 5 years?", "type": "boolean", "required": True},
                    {"name": "incident_details", "question": "If yes to security incidents, please provide details.", "type": "text", "required": False, "conditional": "security_incidents"},
                    {"name": "regulatory_actions", "question": "Have you been subject to any regulatory actions or investigations?", "type": "boolean", "required": True},
                    {"name": "litigation_history", "question": "Are you currently involved in any litigation related to your professional services?", "type": "boolean", "required": True}
                ]
            ),
            ApplicationSection(
                name="Coverage Requirements",
                fields=[
                    {"name": "coverage_limit", "question": "What coverage limit are you seeking? (e.g., $1M, $2M, $5M)", "type": "text", "required": True},
                    {"name": "deductible_preference", "question": "What deductible amount would you prefer?", "type": "currency", "required": True},
                    {"name": "additional_coverages", "question": "Are you interested in additional coverages like cyber liability or D&O?", "type": "text", "required": False},
                    {"name": "coverage_start_date", "question": "When do you need coverage to begin?", "type": "date", "required": True}
                ]
            )
        ]
    
    def start_application(self, conversation_id: str, company_name: str, applicant_name: str) -> Dict[str, Any]:
        """Start a new insurance application"""
        try:
            # Get comprehensive user data before starting
            user_data = self._get_existing_user_data(conversation_id, company_name)
            
            # Get NAIC data for the company
            naic_data = self._get_company_naic_data(company_name, conversation_id)
            
            # Create application state
            application_state = ApplicationState(
                conversation_id=conversation_id,
                company_name=company_name,
                applicant_name=applicant_name,
                sections=[section for section in self.application_template],
                naic_data=naic_data
            )
            
            # Pre-fill from all available data sources
            self._pre_fill_from_existing_data(application_state, user_data, naic_data)
            
            # Store application state
            self.active_applications[conversation_id] = application_state
            
            # Generate first question with context, skipping pre-filled data
            first_question = self._generate_contextual_question(application_state)
            
            # Add efficiency tip for grouped answers
            efficiency_tip = "\n\n💡 **Efficiency Tip**: You can answer multiple questions in one response to save time (e.g., 'Legal name: ABC Corp, Website: abc.com, Revenue: $5M')."
            
            # Show what data we already have
            data_context = ""
            pre_filled_count = len(application_state.completed_fields)
            if pre_filled_count > 0:
                data_context = f" I've pre-filled {pre_filled_count} fields using your registration and company analysis data."
            elif naic_data:
                data_context = " I have your company's background analysis available to help pre-fill relevant fields."
            
            return {
                "status": "started", 
                "message": f"**Tech E&O Insurance Application Started for {company_name}**{data_context}\n\n{first_question}{efficiency_tip}",
                "progress": self._calculate_progress(application_state),
                "section": application_state.sections[application_state.current_section_index].name
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Unable to start application: {str(e)}"
            }
    
    def process_application_response(self, conversation_id: str, user_response: str) -> Dict[str, Any]:
        """Process user response and continue application"""
        try:
            if conversation_id not in self.active_applications:
                return {
                    "status": "error",
                    "message": "No active application found. Please start a new application."
                }
            
            application_state = self.active_applications[conversation_id]
            
            # Process current field response
            result = self._process_field_response(application_state, user_response)
            
            if result["status"] == "field_completed":
                # Move to next field
                next_question = self._get_next_question(application_state)
                
                if next_question:
                    progress = self._calculate_progress(application_state)
                    current_section = application_state.sections[application_state.current_section_index]
                    
                    return {
                        "status": "continue",
                        "message": next_question,
                        "progress": f"{progress}%",
                        "section": current_section.name
                    }
                else:
                    # Application completed
                    summary = self._generate_application_summary(application_state)
                    return {
                        "status": "completed",
                        "message": f"Congratulations! Your application is complete. Here's your summary:\n\n{summary}",
                        "progress": "100%",
                        "application_data": application_state.completed_fields
                    }
            
            elif result["status"] == "clarification_needed":
                return {
                    "status": "clarification",
                    "message": result["message"],
                    "progress": self._calculate_progress(application_state),
                    "section": application_state.sections[application_state.current_section_index].name
                }
            
            else:
                return result
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error processing response: {str(e)}"
            }
    
    def _get_company_naic_data(self, company_name: str, conversation_id: str = None) -> Optional[Dict[str, Any]]:
        """Get NAIC background data for the company"""
        try:
            from agents.analysis.background_agent import get_company_agent
            from agents.core.agents_insurance_chatbot import get_insurance_agent
            
            # Try to get from chat agent's stored data first
            if conversation_id:
                chat_agent = get_insurance_agent()
                stored_data = chat_agent.get_stored_naic_data(conversation_id)
                if stored_data:
                    try:
                        analysis_data = json.loads(stored_data)
                        if isinstance(analysis_data, dict) and 'raw_naic_response' in analysis_data:
                            return analysis_data
                    except (json.JSONDecodeError, KeyError):
                        pass
            
            # Fallback to company agent
            company_agent = get_company_agent()
            raw_analysis = company_agent.get_analysis(company_name)
            
            # Try to parse as JSON to get complete NAIC data
            try:
                analysis_data = json.loads(raw_analysis)
                if isinstance(analysis_data, dict) and 'raw_naic_response' in analysis_data:
                    return analysis_data
            except (json.JSONDecodeError, KeyError):
                pass
                
            return None
            
        except Exception as e:
            print(f"Error getting NAIC data: {e}")
            return None
    
    def _get_existing_user_data(self, conversation_id: str, company_name: str) -> Dict[str, Any]:
        """Get all existing user data from registration and previous interactions"""
        user_data = {}
        
        try:
            # Get registration data from database
            from src.app import db
            from src.models import User, Conversation
            
            # Find user by conversation
            conversation = db.session.query(Conversation).filter_by(id=conversation_id).first()
            if conversation and hasattr(conversation, 'user'):
                user = conversation.user
                user_data.update({
                    'company_name': user.company_name,
                    'company_email': user.company_email,
                    'applicant_name': user.name,
                    'legal_name': user.company_name  # Use registered company name as legal name
                })
                
                # Extract website from email domain
                if user.company_email and '@' in user.company_email:
                    domain = user.company_email.split('@')[1]
                    if domain != 'gmail.com' and domain != 'yahoo.com' and not domain.endswith('.edu'):
                        user_data['website'] = f"https://{domain}"
                        
            print(f"Retrieved user data: {list(user_data.keys())}")
            
        except Exception as e:
            print(f"Error retrieving user data: {e}")
            
        return user_data
    
    def _pre_fill_from_existing_data(self, application_state: ApplicationState, user_data: Dict[str, Any], naic_data: Optional[Dict[str, Any]]) -> None:
        """Pre-fill application fields using all available data sources"""
        # Start with user registration data (highest priority)
        if user_data:
            for key, value in user_data.items():
                if value and key not in application_state.completed_fields:
                    application_state.completed_fields[key] = value
                    
        # Add NAIC data (secondary priority, don't override registration data)
        if naic_data:
            naic_response = naic_data.get('raw_naic_response', {})
            company_name = naic_data.get('company_name', '')
            website_url = naic_data.get('website_url', '')
            
            # Pre-fill company profile section from NAIC
            if naic_response:
                # Extract industry and business description
                industry = naic_response.get('industry', naic_response.get('classification', ''))
                description = naic_response.get('description', naic_response.get('business_description', ''))
                naic_code = naic_response.get('naic_code', '')
                revenue = naic_response.get('revenue', naic_response.get('annual_revenue', ''))
                
                # Only fill if not already set from registration
                mapping = {
                    'industry_classification': industry,
                    'business_description': description,
                    'naic_code': naic_code,
                    'annual_revenue': revenue
                }
                
                # Use company name from NAIC if not from registration
                if company_name and 'legal_name' not in application_state.completed_fields:
                    mapping['legal_name'] = company_name
                if website_url and 'website' not in application_state.completed_fields:
                    mapping['website'] = website_url
                
                for field_name, value in mapping.items():
                    if value and field_name not in application_state.completed_fields:
                        application_state.completed_fields[field_name] = value
                        
        print(f"Pre-filled {len(application_state.completed_fields)} fields from all data sources: {list(application_state.completed_fields.keys())}")
    
    def _get_grouped_questions(self, application_state: ApplicationState) -> List[Dict[str, Any]]:
        """Group related questions to reduce chat interactions"""
        current_section = application_state.sections[application_state.current_section_index]
        
        # Get remaining fields in current section (skip pre-filled data)
        remaining_fields = []
        for i, field in enumerate(current_section.fields):
            if field['name'] not in application_state.completed_fields:
                remaining_fields.append(field)
        
        # If all fields in current section are pre-filled, move to next section
        if not remaining_fields:
            application_state.current_section_index += 1
            if application_state.current_section_index < len(application_state.sections):
                return self._get_grouped_questions(application_state)  # Recursively check next section
        
        if not remaining_fields:
            return []
            
        # Group questions by similarity and logical flow
        if current_section.name == "Company Profile":
            # Group basic company info together
            basic_info = [f for f in remaining_fields if f['name'] in ['legal_name', 'dba_name', 'website']]
            business_info = [f for f in remaining_fields if f['name'] in ['industry', 'business_description', 'annual_revenue']]
            
            if basic_info:
                return basic_info[:3]  # Max 3 questions at once
            elif business_info:
                return business_info[:3]
        
        elif current_section.name == "Risk Assessment":
            # Group risk-related questions
            tech_questions = [f for f in remaining_fields if 'technology' in f['name'] or 'software' in f['name']]
            business_questions = [f for f in remaining_fields if f['name'] in ['business_model', 'client_types', 'employees_count']]
            
            if tech_questions:
                return tech_questions[:2]
            elif business_questions:
                return business_questions[:3]
        
        # Default: return up to 3 related questions
        return remaining_fields[:3]
    
    def _generate_contextual_question(self, application_state: ApplicationState) -> str:
        """Generate intelligent grouped questions with NAIC context"""
        # Get grouped questions for efficiency
        grouped_questions = self._get_grouped_questions(application_state)
        
        if not grouped_questions:
            # Move to next section if current section is complete
            if application_state.current_section_index < len(application_state.sections) - 1:
                application_state.current_section_index += 1
                grouped_questions = self._get_grouped_questions(application_state)
            else:
                return self._generate_quote_summary(application_state)
        
        if not grouped_questions:
            return self._generate_quote_summary(application_state)
        
        # Build context from NAIC data and pre-filled fields
        naic_context = ""
        pre_filled_info = []
        
        if application_state.naic_data:
            naic_response = application_state.naic_data.get('raw_naic_response', {})
            if naic_response:
                industry = naic_response.get('industry', '')
                if industry:
                    naic_context = f"\\n\\nBased on our analysis, your company is in the {industry} industry."
        
        # Show pre-filled information
        if application_state.completed_fields:
            for field_name, value in application_state.completed_fields.items():
                if field_name in ['legal_name', 'website', 'industry_classification', 'business_description']:
                    display_name = field_name.replace('_', ' ').title()
                    pre_filled_info.append(f"{display_name}: {value}")
        
        if pre_filled_info:
            naic_context += f"\\n\\nI've already gathered some information about your company:\\n" + "\\n".join(f"• {info}" for info in pre_filled_info)
        
        # Create efficient grouped question prompt
        question_list = []
        for i, field in enumerate(grouped_questions, 1):
            question_list.append(f"{i}. {field['question']}")
        
        questions_text = "\\n".join(question_list)
        current_section = application_state.sections[application_state.current_section_index]
        
        intro_text = f"**{current_section.name} Section** - To provide you with an accurate quote, I need the following {len(grouped_questions)} pieces of information:"
        
        efficiency_note = ""
        if len(grouped_questions) > 1:
            efficiency_note = f"\\n\\n💡 *You can answer all {len(grouped_questions)} questions in one response to save time.*"
        
        return f"{intro_text}\\n\\n{questions_text}{naic_context}{efficiency_note}"
    
    def _generate_quote_summary(self, application_state: ApplicationState) -> str:
        """Generate quote summary when application is complete"""
        try:
            # Calculate completeness
            total_fields = sum(len(section.fields) for section in application_state.sections)
            completed_fields = len(application_state.completed_fields)
            completeness = (completed_fields / total_fields) * 100
            
            if completeness >= 80:
                quote_status = "Ready to generate detailed quote"
                next_steps = "I'll now analyze your company profile and generate competitive Tech E&O insurance quotes."
            elif completeness >= 60:
                quote_status = "Preliminary quote available"
                next_steps = "I can provide initial pricing estimates. Complete remaining fields for precise quotes."
            else:
                quote_status = "Additional information needed"
                next_steps = "Please complete more application fields to generate accurate quotes."
            
            summary = f"""
**Application Summary for {application_state.company_name}**

📊 **Completion Status**: {completeness:.0f}% complete
🎯 **Quote Status**: {quote_status}

**Collected Information**:
"""
            
            # Group completed fields by category
            profile_fields = []
            business_fields = []
            risk_fields = []
            
            for field_name, value in application_state.completed_fields.items():
                display_name = field_name.replace('_', ' ').title()
                if any(term in field_name for term in ['name', 'website', 'email']):
                    profile_fields.append(f"• {display_name}: {value}")
                elif any(term in field_name for term in ['industry', 'revenue', 'employees']):
                    business_fields.append(f"• {display_name}: {value}")
                else:
                    risk_fields.append(f"• {display_name}: {value}")
            
            if profile_fields:
                summary += "\\n**Company Profile**:\\n" + "\\n".join(profile_fields)
            if business_fields:
                summary += "\\n\\n**Business Details**:\\n" + "\\n".join(business_fields)
            if risk_fields:
                summary += "\\n\\n**Risk Assessment**:\\n" + "\\n".join(risk_fields)
            
            summary += f"\\n\\n**Next Steps**: {next_steps}"
            
            return summary
            
        except Exception as e:
            print(f"Error generating quote summary: {e}")
            return "Application completed! Preparing your Tech E&O insurance quote based on the information provided."
    
    def _process_field_response(self, application_state: ApplicationState, user_response: str) -> Dict[str, Any]:
        """Process user response for current field"""
        current_section = application_state.sections[application_state.current_section_index]
        current_field = current_section.fields[current_section.current_field_index]
        
        # Use LLM to validate and process response
        validation_result = self._validate_field_response(current_field, user_response, application_state)
        
        if validation_result["valid"]:
            # Store the processed response
            field_key = f"{current_section.name.lower().replace(' ', '_')}_{current_field['name']}"
            application_state.completed_fields[field_key] = validation_result["processed_value"]
            
            return {"status": "field_completed"}
        else:
            return {
                "status": "clarification_needed",
                "message": validation_result["clarification_message"]
            }
    
    def _validate_field_response(self, field: Dict[str, Any], response: str, application_state: ApplicationState) -> Dict[str, Any]:
        """Validate user response using LLM"""
        try:
            # Build context for validation
            context_parts = [
                f"Field: {field['question']}",
                f"Type: {field['type']}",
                f"Required: {field['required']}",
                f"User Response: {response}"
            ]
            
            # Add NAIC context if available and relevant
            if field.get("use_naic") and application_state.naic_data:
                naic_data = application_state.naic_data.get("raw_naic_response", {})
                context_parts.append(f"NAIC Background Data: {json.dumps(naic_data, indent=2)}")
            
            validation_prompt = f"""
Validate this insurance application field response:

{chr(10).join(context_parts)}

Please validate the response and return JSON in this format:
{{
    "valid": true/false,
    "processed_value": "cleaned and formatted value",
    "clarification_message": "message if clarification needed, or null if valid"
}}

Validation rules:
- For text fields: Accept reasonable responses, clean formatting
- For numbers: Ensure valid numeric values
- For currency: Accept various formats ($1M, 1000000, etc.) and normalize
- For booleans: Accept yes/no, true/false variations
- For dates: Accept various date formats and normalize
- Use NAIC data to provide helpful suggestions or validate industry information
- Be helpful and conversational in clarification messages
"""
            
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an insurance application assistant. Validate responses helpfully and conversationally."},
                    {"role": "user", "content": validation_prompt}
                ],
                temperature=0.1
            )
            
            try:
                result = json.loads(response.choices[0].message.content)
                return result
            except json.JSONDecodeError:
                # Fallback validation
                return {
                    "valid": True,
                    "processed_value": response.strip(),
                    "clarification_message": None
                }
                
        except Exception as e:
            print(f"Validation error: {e}")
            # Fallback to accepting response
            return {
                "valid": True,
                "processed_value": response.strip(),
                "clarification_message": None
            }
    
    def _get_next_question(self, application_state: ApplicationState) -> Optional[str]:
        """Get the next question in the application"""
        current_section = application_state.sections[application_state.current_section_index]
        
        # Move to next field in current section
        if current_section.current_field_index + 1 < len(current_section.fields):
            current_section.current_field_index += 1
            next_field = current_section.fields[current_section.current_field_index]
            
            # Check conditional logic
            if next_field.get("conditional"):
                conditional_field = next_field["conditional"]
                # Look for the conditional field value
                conditional_key = f"{current_section.name.lower().replace(' ', '_')}_{conditional_field}"
                if not application_state.completed_fields.get(conditional_key):
                    # Skip this field and get next
                    return self._get_next_question(application_state)
            
            # Generate contextual question
            return self._generate_question_with_context(next_field, application_state)
        
        # Move to next section
        elif application_state.current_section_index + 1 < len(application_state.sections):
            current_section.completed = True
            application_state.current_section_index += 1
            next_section = application_state.sections[application_state.current_section_index]
            next_section.current_field_index = 0
            
            next_field = next_section.fields[0]
            section_intro = f"\n**{next_section.name}**\nNow let's move on to {next_section.name.lower()}.\n\n"
            question = self._generate_question_with_context(next_field, application_state)
            
            return section_intro + question
        
        # Application completed
        return None
    
    def _generate_question_with_context(self, field: Dict[str, Any], application_state: ApplicationState) -> str:
        """Generate question with NAIC context"""
        base_question = field["question"]
        
        # Add NAIC context for relevant fields
        if field.get("use_naic") and application_state.naic_data:
            try:
                naic_data = application_state.naic_data.get("raw_naic_response", {})
                
                # Generate contextual help using LLM
                context_prompt = f"""
Based on this NAIC classification data for {application_state.company_name}:
{json.dumps(naic_data, indent=2)}

Provide helpful context for this insurance application question: "{base_question}"

Return a conversational suggestion that helps the user answer the question based on the NAIC data.
Keep it brief (1-2 sentences) and helpful. If the NAIC data doesn't provide relevant context, return "NO_CONTEXT".
"""
                
                response = self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an insurance application assistant providing helpful context."},
                        {"role": "user", "content": context_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=200
                )
                
                context_suggestion = response.choices[0].message.content.strip()
                
                if context_suggestion != "NO_CONTEXT":
                    return f"{base_question}\n\n💡 *{context_suggestion}*"
                    
            except Exception as e:
                print(f"Error generating context: {e}")
        
        return base_question
    
    def _calculate_progress(self, application_state: ApplicationState) -> int:
        """Calculate completion progress percentage"""
        total_fields = sum(len(section.fields) for section in application_state.sections)
        completed_fields = len(application_state.completed_fields)
        
        return min(100, int((completed_fields / total_fields) * 100))
    
    def _generate_application_summary(self, application_state: ApplicationState) -> str:
        """Generate comprehensive application summary"""
        try:
            # Prepare all collected data
            summary_data = {
                "company_name": application_state.company_name,
                "applicant_name": application_state.applicant_name,
                "completion_time": time.time() - application_state.started_at,
                "completed_fields": application_state.completed_fields,
                "naic_background": application_state.naic_data
            }
            
            summary_prompt = f"""
Generate a comprehensive insurance application summary for this completed application:

{json.dumps(summary_data, indent=2)}

Create a professional summary that includes:

1. **Application Overview**
   - Company name and applicant
   - Application type and completion date
   - Key company metrics

2. **Company Profile Summary**
   - Business description and industry classification
   - Revenue and employee information
   - Years in operation

3. **Technology & Security Assessment**
   - Technology stack and infrastructure
   - Security measures and compliance
   - Risk assessment based on responses

4. **Coverage Recommendations**
   - Suggested coverage limits based on company profile
   - Risk factors identified
   - Additional coverages to consider

5. **Next Steps**
   - What happens next in the underwriting process
   - Expected timeline for quote
   - Any additional information needed

Format as a professional insurance summary with clear sections and bullet points.
Use the NAIC background data to provide context and validate the application responses.
"""
            
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert insurance underwriter creating application summaries."},
                    {"role": "user", "content": summary_prompt}
                ],
                temperature=0.1
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error generating summary: {e}")
            return f"Application completed for {application_state.company_name}. Our underwriting team will review your responses and provide a quote within 24-48 hours."
    
    def get_application_status(self, conversation_id: str) -> Dict[str, Any]:
        """Get current application status"""
        if conversation_id not in self.active_applications:
            return {"status": "not_found"}
        
        application_state = self.active_applications[conversation_id]
        progress = self._calculate_progress(application_state)
        current_section = application_state.sections[application_state.current_section_index]
        
        return {
            "status": "active",
            "progress": progress,
            "current_section": current_section.name,
            "company_name": application_state.company_name,
            "fields_completed": len(application_state.completed_fields)
        }
    
    def is_application_active(self, conversation_id: str) -> bool:
        """Check if an application is currently active"""
        return conversation_id in self.active_applications

# Global application agent instance
_application_agent = None

def get_conversational_application_agent():
    """Get or create the global conversational application agent instance"""
    global _application_agent
    if _application_agent is None:
        _application_agent = ConversationalApplicationAgent()
    return _application_agent

async def start_application(conversation_id: str, company_name: str, applicant_name: str) -> Dict[str, Any]:
    """Start a new conversational application"""
    agent = get_conversational_application_agent()
    return agent.start_application(conversation_id, company_name, applicant_name)

async def process_application_response(conversation_id: str, user_response: str) -> Dict[str, Any]:
    """Process application response"""
    agent = get_conversational_application_agent()
    return agent.process_application_response(conversation_id, user_response)

def get_application_status(conversation_id: str) -> Dict[str, Any]:
    """Get application status"""
    agent = get_conversational_application_agent()
    return agent.get_application_status(conversation_id)

def is_application_active(conversation_id: str) -> bool:
    """Check if application is active"""
    agent = get_conversational_application_agent()
    return agent.is_application_active(conversation_id)