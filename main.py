#!/usr/bin/env python3
"""
Main entry point for the Aegis Orchestrator security automation system.

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

import os
import sys
import argparse
import logging
from typing import Dict, Any
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import threading

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.orchestrator_app import OrchestratorApp

def setup_logging(log_level: str = "INFO") -> None:
    """Set up logging configuration."""
    handlers = [logging.StreamHandler(sys.stdout)]
    
    # Only add file handler if we have write permissions (not in container)
    try:
        handlers.append(logging.FileHandler('aegis_orchestrator.log'))
    except (PermissionError, OSError):
        # Container environment - use only stdout
        pass
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

def main() -> int:
    """Main entry point for the Aegis Orchestrator."""
    parser = argparse.ArgumentParser(
        description="Aegis Orchestrator - AI-powered security vulnerability remediation"
    )
    parser.add_argument(
        "repo_url",
        nargs='?',
        help="Git repository URL to analyze and fix security vulnerabilities"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set the logging level"
    )
    parser.add_argument(
        "--list-vulnerabilities",
        action="store_true", 
        help="List supported vulnerability types and exit"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run analysis without creating pull requests"
    )
    parser.add_argument(
        "--server",
        action="store_true",
        help="Run as HTTP server for Cloud Run deployment"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        # Handle server mode for Cloud Run
        if args.server:
            return run_server()
        
        # Require repo_url if not in server mode
        if not args.repo_url:
            parser.error("repo_url is required when not running in server mode")
        
        # Initialize orchestrator
        orchestrator = OrchestratorApp()
        
        # Handle list vulnerabilities option
        if args.list_vulnerabilities:
            vulnerability_info = orchestrator.list_supported_vulnerability_types()
            print_vulnerability_info(vulnerability_info)
            return 0
        
        logger.info("Starting Aegis Orchestrator security analysis")
        logger.info("Target repository: %s", args.repo_url)
        
        if args.dry_run:
            logger.info("Running in dry-run mode - no pull requests will be created")
        
        # Process the repository
        result = orchestrator.process_repository(args.repo_url)
        
        # Print results
        print_results(result)
        
        # Cleanup
        orchestrator.cleanup()
        
        # Return appropriate exit code
        if result["status"] == "success":
            return 0
        elif result["status"] == "error":
            return 1
        else:
            return 2
            
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        return 130
    except (ValueError, ConnectionError, OSError) as e:
        logger.error("Process error: %s", e, exc_info=True)
        return 1

def print_vulnerability_info(vuln_info: Dict[str, Any]) -> None:
    """Print supported vulnerability types information."""
    print("🔍 Supported Vulnerability Types:")
    print("=" * 50)
    
    for vuln in vuln_info["supported_vulnerabilities"]:
        print(f"\n• {vuln['type']}")
        print(f"  CWE IDs: {', '.join(vuln['cwe_ids'])}")
        print(f"  Description: {vuln['description']}")
    
    print("\n🤖 AI Models Used:")
    print("=" * 20)
    for model_type, model_name in vuln_info["ai_models_used"].items():
        print(f"• {model_type.replace('_', ' ').title()}: {model_name}")

def print_results(result: Dict[str, Any]) -> None:
    """Print workflow execution results."""
    print("\n" + "=" * 60)
    print("🔒 AEGIS ORCHESTRATOR SECURITY ANALYSIS RESULTS")
    print("=" * 60)
    
    if result["status"] == "success":
        print("✅ Status: SUCCESS")
        print(f"🔍 Vulnerabilities Found: {result.get('vulnerabilities_found', 0)}")
        print(f"🛠️  Fixes Applied: {result.get('fixes_applied', 0)}")
        
        if result.get('pull_request', {}).get('url'):
            print(f"🔗 Pull Request: {result['pull_request']['url']}")
        
        if result.get('summary_report'):
            print("\n📋 Summary Report:")
            print(result['summary_report'])
            
    elif result["status"] == "error":
        print("❌ Status: ERROR")
        print(f"💥 Error: {result.get('error', 'Unknown error')}")
        
    elif result["status"] == "incomplete":
        print("⚠️  Status: INCOMPLETE")
        print(f"🔍 Vulnerabilities Found: {result.get('vulnerabilities_found', 0)}")
        print(f"🛠️  Fixes Applied: {result.get('fixes_applied', 0)}")
        print(f"🏁 Final State: {result.get('final_state', 'unknown')}")
        print(f"📝 Message: {result.get('message', 'No additional information')}")
    
    print("\n" + "=" * 60)

class AegisRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Aegis Orchestrator server."""
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "healthy"}).encode())
        elif self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<h1>Aegis Orchestrator</h1><p>AI-powered security automation platform</p>")
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        """Handle POST requests for repository analysis."""
        if self.path == '/analyze':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                
                repo_url = data.get('repo_url')
                if not repo_url:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "repo_url is required"}).encode())
                    return
                
                # Initialize orchestrator and process repository
                orchestrator = OrchestratorApp()
                result = orchestrator.process_repository(repo_url)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()

def run_server() -> int:
    """Run HTTP server for Cloud Run deployment."""
    port = int(os.environ.get('PORT', 8080))
    
    server = HTTPServer(('', port), AegisRequestHandler)
    print(f"🌐 Aegis Orchestrator server starting on port {port}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("🛑 Server stopped")
        server.shutdown()
        return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)