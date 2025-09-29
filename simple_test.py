#!/usr/bin/env python3
"""
Simple test of the API-only solicitation analyzer
"""

import os
import json
from dotenv import load_dotenv

try:
    from .solicitation_analyzer import SolicitationAnalyzer
except ImportError:
    from solicitation_analyzer import SolicitationAnalyzer

load_dotenv()

# Sample opportunity data (mock)
sample_opportunity = {
    "title": "Test IT Services Contract",
    "solicitationNumber": "TEST-2025-001", 
    "noticeId": "test123",
    "postedDate": "2025-09-25",
    "responseDeadLine": "2025-10-25",
    "naicsCode": "541511",
    "description": "This is a test solicitation for IT consulting services. The government requires comprehensive technical support including system analysis, software development, and project management services.",
    "organizationName": "Department of Test",
    "officeAddress": {
        "city": "Washington",
        "state": "DC",
        "zipcode": "20001"
    },
    "typeOfSetAside": "Small Business",
    "uiLink": "https://sam.gov/test"
}

def main():
    sam_api_key = os.getenv("SAM_GOV_API_KEY")
    if not sam_api_key:
        print("Error: SAM_GOV_API_KEY not found")
        return
    
    analyzer = SolicitationAnalyzer(sam_api_key)
    
    print("Testing API-only solicitation analysis...")
    print("=" * 50)
    
    result = analyzer.analyze_solicitation(sample_opportunity)
    
    print("RESULTS:")
    print("-" * 30)
    
    if result.get("detailed_description"):
        print(f"Description: {result['detailed_description'][:200]}...")
    
    if result.get("additional_info"):
        print(f"\nAdditional Info: {len(result['additional_info'])} fields extracted")
        for key, value in list(result["additional_info"].items())[:3]:
            print(f"  - {key}: {value}")
    
    if result.get("documents_info"):
        print(f"\nDocuments: {len(result['documents_info'])} found")
    
    print(f"\nAI Response Available: {'Yes' if result.get('ai_response') and 'Error' not in str(result['ai_response']) else 'No (quota exceeded)'}")
    
    # Save result
    with open("simple_test_result.json", "w") as f:
        json.dump(result, f, indent=2)
    
    print("\nAnalysis complete - saved to simple_test_result.json")

if __name__ == "__main__":
    main()