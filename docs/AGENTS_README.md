Agent Organization Structure
Overview
The agents have been reorganized into functional categories for better maintainability and scalability. Each category represents a specific domain of functionality within the insurance chatbot system.

Directory Structure
agents/
├── core/                              # Core orchestration and session management
│   ├── agents_insurance_chatbot.py   # Main orchestrator agent
│   └── conversation_coordinator.py    # Session and thread management
│
├── analysis/                          # Risk analysis and decision-making
│   ├── background_agent.py           # Company background analysis (NAIC API)
│   ├── risk_assessment_agent.py      # Comprehensive risk report generation
│   └── underwriting_agent.py         # Automated underwriting decisions
│
├── customer_service/                  # Customer interaction and applications
│   ├── application_agent.py          # Basic application processing
│   └── conversational_application_agent.py  # Conversational form completion
│
├── monitoring/                        # Real-time monitoring and escalation
│   ├── parallel_monitoring_agent.py  # Asynchronous conversation monitoring
│   └── escalation_agent.py           # Human handoff management
│
└── formatting/                        # Report formatting and presentation
    └── risk_formatter_agent.py       # HTML report formatting
Category Descriptions
Core (/core)
Purpose: Central coordination and orchestration of all agent activities

agents_insurance_chatbot.py: The main entry point for all insurance queries. Routes requests to specialized agents and synthesizes responses. Integrates with WebSearchAgent for real-time web search.
conversation_coordinator.py: Manages conversation sessions, thread mapping, and state persistence across channels.
Analysis (/analysis)
Purpose: Data analysis, risk assessment, and decision-making

background_agent.py: Retrieves and analyzes company information using external APIs (NAIC classification).
risk_assessment_agent.py: Generates detailed risk assessment reports with coverage recommendations.
underwriting_agent.py: Makes automated underwriting decisions based on company data and guidelines.
Customer Service (/customer_service)
Purpose: Direct customer interactions and application processing

application_agent.py: Handles basic insurance application workflows.
conversational_application_agent.py: Provides conversational interface for completing complex applications.
Monitoring (/monitoring)
Purpose: Real-time monitoring and human escalation

parallel_monitoring_agent.py: Runs asynchronously to monitor conversations for sentiment, complexity, and escalation needs.
escalation_agent.py: Manages escalation to human specialists via Slack integration.
Formatting (/formatting)
Purpose: Professional report generation and formatting

risk_formatter_agent.py: Converts raw risk assessment data into professionally formatted HTML reports.
Agent Communication Flow
User Request
    ↓
[Core: Main Insurance Agent]
    ├─→ [Analysis: Background Agent] → Company Data
    ├─→ [Analysis: Risk Assessment] → Risk Reports
    ├─→ [Customer Service: Application] → Form Processing
    └─→ [Monitoring: PMA] → Real-time Analysis
         └─→ [Monitoring: Escalation] → Human Handoff
              ↓
         [Formatting: Risk Formatter] → Professional Reports
Import Examples
After reorganization, imports should follow this pattern:

# Core agents
from agents.core.agents_insurance_chatbot import InsuranceKnowledgeAgent
from agents.core.conversation_coordinator import ConversationCoordinator
# Analysis agents
from agents.analysis.background_agent import get_company_agent
from agents.analysis.risk_assessment_agent import RiskAssessmentAgent
from agents.analysis.underwriting_agent import UnderwritingAgent
# Customer service agents
from agents.customer_service.application_agent import ApplicationAgent
from agents.customer_service.conversational_application_agent import get_conversational_application_agent
# Monitoring agents
from agents.monitoring.parallel_monitoring_agent import ParallelMonitoringAgent
from agents.monitoring.escalation_agent import EscalationAgent
# Formatting agents
from agents.formatting.risk_formatter_agent import RiskFormatterAgent
Benefits of This Structure
Clear Separation of Concerns: Each category has a specific purpose
Easier Navigation: Developers can quickly find agents by function
Scalability: New agents can be added to appropriate categories
Maintainability: Related agents are grouped together
Import Clarity: Import paths clearly indicate agent purpose
Adding New Agents
When adding new agents, follow these guidelines:

Determine the primary function of the agent
Place it in the appropriate category directory
Update imports in dependent files
Add documentation to this README
Follow the naming convention: {function}_agent.py