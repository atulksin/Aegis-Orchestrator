"""
Main orchestrator application using LangGraph workflow for security automation.

Copyright 2025 Aegis Orchestrator Contributors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import logging
from typing import Dict, Optional
from langchain_core.messages import HumanMessage
from agents.workflow import create_aegis_workflow, AegisState, WorkflowState
from config.settings import config, ModelType

logger = logging.getLogger(__name__)

class OrchestratorApp:
    """Main application that orchestrates security automation using LangGraph workflow."""

    def __init__(self, config_dict: Optional[Dict] = None):
        """Initialize the Orchestrator with LangGraph workflow.
        
        Args:
            config_dict: Optional configuration dictionary for backward compatibility
        """
        # Validate configuration
        config.validate()
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        self.workflow = create_aegis_workflow()
        logger.info("LangGraph-based Orchestrator initialized")

    def process_repository(self, repo_url: str) -> Dict:
        """Process a repository for vulnerabilities and fixes using LangGraph workflow.
        
        Args:
            repo_url: URL of the repository to process
            
        Returns:
            Dictionary containing processing results
        """
        try:
            logger.info(f"Starting security analysis for repository: {repo_url}")
            
            # Initialize workflow state
            initial_state: AegisState = {
                "repo_url": repo_url,
                "repo_path": None,
                "branch_name": None,
                "current_state": WorkflowState.INITIALIZE,
                "messages": [HumanMessage(content=f"Analyze repository: {repo_url}")],
                "error_message": None,
                "vulnerabilities": [],
                "research_results": {},
                "fixes": [],
                "reviewed_fixes": [],
                "pull_request_url": None,
                "summary_report": None
            }
            
            # Execute the LangGraph workflow
            final_state = self.workflow.invoke(initial_state)
            
            # Process results
            if final_state["current_state"] == WorkflowState.ERROR:
                return {
                    "status": "error",
                    "error": final_state.get("error_message", "Unknown error occurred"),
                    "fixes_applied": 0
                }
            
            elif final_state["current_state"] == WorkflowState.COMPLETE:
                return {
                    "status": "success",
                    "fixes_applied": len(final_state.get("reviewed_fixes", [])),
                    "vulnerabilities_found": len(final_state.get("vulnerabilities", [])),
                    "pull_request": {
                        "url": final_state.get("pull_request_url"),
                        "status": "created" if final_state.get("pull_request_url") else "not_created"
                    },
                    "summary_report": final_state.get("summary_report"),
                    "workflow_state": final_state["current_state"].value
                }
            
            else:
                # Workflow didn't complete successfully
                return {
                    "status": "incomplete",
                    "fixes_applied": len(final_state.get("reviewed_fixes", [])),
                    "vulnerabilities_found": len(final_state.get("vulnerabilities", [])),
                    "final_state": final_state["current_state"].value,
                    "message": "Workflow did not complete all steps"
                }
                
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": f"Workflow execution failed: {str(e)}",
                "fixes_applied": 0
            }

    def get_workflow_status(self, repo_url: str) -> Dict:
        """Get status information about a workflow run.
        
        Args:
            repo_url: Repository URL to check status for
            
        Returns:
            Dictionary containing workflow status
        """
        # This is a placeholder - in a real implementation you might 
        # track workflow runs in a database or state store
        return {
            "status": "not_implemented",
            "message": "Workflow status tracking not yet implemented"
        }

    def list_supported_vulnerability_types(self) -> Dict:
        """List the types of vulnerabilities the system can detect and fix.
        
        Returns:
            Dictionary containing supported vulnerability types
        """
        return {
            "supported_vulnerabilities": [
                {
                    "type": "SQL Injection",
                    "cwe_ids": ["CWE-89"],
                    "description": "Improper neutralization of SQL commands"
                },
                {
                    "type": "Cross-Site Scripting (XSS)",
                    "cwe_ids": ["CWE-79", "CWE-80"],
                    "description": "Improper neutralization of script-related HTML tags"
                },
                {
                    "type": "Command Injection", 
                    "cwe_ids": ["CWE-78"],
                    "description": "OS command injection vulnerabilities"
                },
                {
                    "type": "Path Traversal",
                    "cwe_ids": ["CWE-22"],
                    "description": "Path traversal and directory traversal"
                },
                {
                    "type": "Insecure Deserialization",
                    "cwe_ids": ["CWE-502"],
                    "description": "Deserialization of untrusted data"
                },
                {
                    "type": "Authentication Issues",
                    "cwe_ids": ["CWE-287", "CWE-306"],
                    "description": "Authentication and authorization weaknesses"
                },
                {
                    "type": "Cryptographic Issues",
                    "cwe_ids": ["CWE-327", "CWE-328"],
                    "description": "Weak or broken cryptographic implementations"
                }
            ],
            "ai_models_used": {
                "vulnerability_scanner": config.get_model_config(ModelType.VULNERABILITY_SCANNER).model_name,
                "security_researcher": config.get_model_config(ModelType.SECURITY_RESEARCHER).model_name,
                "code_fixer": config.get_model_config(ModelType.CODE_FIXER).model_name,
                "code_reviewer": config.get_model_config(ModelType.CODE_REVIEWER).model_name
            }
        }

    def cleanup(self) -> None:
        """Clean up resources (maintained for backward compatibility)."""
        logger.info("Cleanup completed - LangGraph workflow is stateless")
        
    # Backward compatibility methods for existing tests
    @property  
    def sast_client(self):
        """Placeholder for backward compatibility."""
        class MockSASTClient:
            def cleanup(self): pass
        return MockSASTClient()
    
    @property
    def researcher(self):
        """Placeholder for backward compatibility."""
        class MockResearcher:
            def cleanup(self): pass
        return MockResearcher()
        
    @property
    def fixer(self):
        """Placeholder for backward compatibility."""
        class MockFixer:
            def cleanup(self): pass
        return MockFixer()
