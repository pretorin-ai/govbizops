"""
Solicitation analyzer for fetching detailed information and generating AI responses
"""

import requests
import re
import logging
from typing import Dict, List, Any, Optional
from openai import OpenAI
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add current directory to path if running as script
if __name__ == "__main__" or not __package__:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from .sam_scraper import scrape_sam_opportunity
except ImportError:
    from sam_scraper import scrape_sam_opportunity

load_dotenv()

logger = logging.getLogger(__name__)


class SolicitationAnalyzer:
    """Analyzes solicitations and generates responses using AI"""
    
    def __init__(self, api_key: str):
        """
        Initialize solicitation analyzer
        
        Args:
            api_key: SAM.gov API key
        """
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "X-Api-Key": api_key,
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        # Initialize OpenAI client if API key is available
        openai_key = os.getenv("OPENAI_API_KEY")
        self.openai_client = None
        if openai_key:
            self.openai_client = OpenAI(api_key=openai_key)
    
    def fetch_description_from_api_url(self, desc_url: str) -> Optional[str]:
        """
        Fetch description content from SAM.gov API description URL
        
        Args:
            desc_url: The API URL for the description
            
        Returns:
            Description content or None if fetch fails
        """
        try:
            # Try to convert v1 URLs to v2 if needed
            if '/opportunities/v1/' in desc_url:
                v2_url = desc_url.replace('/opportunities/v1/', '/opportunities/v2/')
                logger.info(f"Converting v1 URL to v2: {v2_url}")
                desc_url = v2_url
            
            logger.info(f"Fetching description from API: {desc_url}")
            response = self.session.get(desc_url, timeout=30)
            
            if response.status_code == 200:
                content = response.text.strip()
                # Sometimes the API returns HTML, sometimes plain text
                # Remove basic HTML tags if present
                if content.startswith('<'):
                    import html
                    # Basic HTML stripping
                    content = re.sub(r'<[^>]+>', '', content)
                    content = html.unescape(content).strip()
                
                logger.info(f"Successfully fetched description, length: {len(content)}")
                return content
            elif response.status_code == 404:
                logger.warning(f"Description URL returned 404. SAM.gov may have changed their API structure.")
                logger.warning("Consider checking SAM.gov's latest API documentation or using the web interface.")
                return None
            else:
                logger.warning(f"Failed to fetch description, status: {response.status_code}, response: {response.text[:200]}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching description from URL: {e}")
            return None
    
    def fetch_description_from_web(self, opportunity: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Fetch description by scraping the SAM.gov web page
        
        Args:
            opportunity: Opportunity data containing uiLink
            
        Returns:
            Dictionary with description and attachments, or None if scraping fails
        """
        ui_link = opportunity.get('uiLink')
        if not ui_link:
            logger.warning("No uiLink found in opportunity data")
            return None
        
        try:
            logger.info(f"Attempting to scrape description from: {ui_link}")
            
            # Convert workspace URL to public view URL if needed
            if '/workspace/' in ui_link:
                # Extract opportunity ID and create public URL
                match = re.search(r'/opp/([a-f0-9]{32})/view', ui_link)
                if match:
                    opp_id = match.group(1)
                    public_url = f"https://sam.gov/opp/{opp_id}/view"
                    logger.info(f"Converted to public URL: {public_url}")
                    ui_link = public_url
            
            # Scrape the page
            result = scrape_sam_opportunity(ui_link, headless=True)
            
            if result['success'] and result['description']:
                logger.info(f"Successfully scraped description from web page")
                return result
            else:
                logger.warning(f"Web scraping failed: {result.get('error', 'No description found')}")
                return None
                
        except Exception as e:
            logger.error(f"Error scraping web page: {e}")
            return None
        
    def fetch_detailed_description(self, opportunity: Dict[str, Any]) -> Optional[str]:
        """
        Get detailed description from opportunity API data, including fetching from description URLs
        
        Note: As of 2025, SAM.gov's description API endpoints (v1/noticedesc) appear to be 
        deprecated and return 404 errors. The API now only provides URLs that no longer work.
        Users may need to access descriptions through the SAM.gov web interface or check
        for updated API documentation.
        
        Args:
            opportunity: Opportunity data from API
            
        Returns:
            Detailed description text or None if not available
        """
        # Try multiple fields that might contain description data
        description_fields = [
            'description',
            'fullDescription', 
            'shortDescription',
            'additionalInformationText',
            'descriptionOfRequirement',
            'performanceLocation',
            'requirements'
        ]
        
        descriptions = []
        
        for field in description_fields:
            if field in opportunity and opportunity[field]:
                desc_text = str(opportunity[field]).strip()
                
                # If it's a description URL, fetch the actual content
                if desc_text.startswith('https://api.sam.gov/') and 'noticedesc' in desc_text:
                    logger.info(f"Found description URL in field '{field}': {desc_text}")
                    fetched_content = self.fetch_description_from_api_url(desc_text)
                    if fetched_content:
                        descriptions.append(f"{field}: {fetched_content}")
                    else:
                        # API failed, try web scraping
                        logger.info("API fetch failed, attempting web scraping...")
                        web_result = self.fetch_description_from_web(opportunity)
                        if web_result and web_result['description']:
                            descriptions.append(f"{field} (from web): {web_result['description']}")
                            # Store attachments for later use
                            if 'attachments' in web_result and web_result['attachments']:
                                if '_web_attachments' not in opportunity:
                                    opportunity['_web_attachments'] = []
                                opportunity['_web_attachments'].extend(web_result['attachments'])
                        else:
                            # Both methods failed
                            descriptions.append(f"{field} (URL - fetch failed): {desc_text}")
                
                elif len(desc_text) > 50:  # Only meaningful descriptions
                    descriptions.append(f"{field}: {desc_text}")
                    logger.info(f"Found description in field: {field}")
        
        if descriptions:
            return '\n\n'.join(descriptions)
        else:
            logger.warning(f"No description found in API data for {opportunity.get('noticeId')}")
            return None
    
    def extract_additional_info(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract additional structured information from opportunity data
        
        Args:
            opportunity: Opportunity data from API
            
        Returns:
            Dictionary with extracted information
        """
        additional_info = {}
        
        # Extract key fields that might contain useful information
        info_fields = {
            'naics_code': 'naicsCode',
            'psc_code': 'pscCode',
            'organization_name': 'organizationName',
            'office_address': 'officeAddress',
            'primary_contact': 'primaryContact',
            'contract_award_date': 'awardDate',
            'performance_period': 'performancePeriod',
            'place_of_performance': 'placeOfPerformance',
            'set_aside_type': 'typeOfSetAside',
            'contract_type': 'typeOfContract',
            'solicitation_procedures': 'solicitationProcedures'
        }
        
        for key, field in info_fields.items():
            if field in opportunity and opportunity[field]:
                additional_info[key] = opportunity[field]
        
        # Look for attachments/documents
        if 'attachments' in opportunity:
            additional_info['attachments'] = opportunity['attachments']
        
        # Look for amendment information
        if 'isAmendment' in opportunity:
            additional_info['is_amendment'] = opportunity['isAmendment']
            
        return additional_info
    
    def extract_documents_info(self, opportunity: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Extract document information from opportunity API data
        
        Args:
            opportunity: Opportunity data from API
            
        Returns:
            List of document info dictionaries
        """
        documents = []
        
        # Check for attachments in the API data
        if 'attachments' in opportunity and opportunity['attachments']:
            for attachment in opportunity['attachments']:
                if isinstance(attachment, dict):
                    documents.append({
                        "type": attachment.get('type', 'Unknown'),
                        "name": attachment.get('name', 'Unknown'),
                        "description": attachment.get('description', ''),
                        "url": attachment.get('url', '')
                    })
        
        # Add web-scraped attachments if available
        if '_web_attachments' in opportunity and opportunity['_web_attachments']:
            for attachment in opportunity['_web_attachments']:
                documents.append({
                    "type": "Web Attachment",
                    "name": attachment.get('name', 'Unknown'),
                    "description": "Scraped from SAM.gov",
                    "url": attachment.get('url', '')
                })
        
        # Look for document references in description text
        description_text = self.fetch_detailed_description(opportunity) or ""
        
        document_patterns = [
            r'Statement of Work|SOW',
            r'Request for Proposal|RFP',
            r'Request for Quotation|RFQ', 
            r'Instructions to Offerors',
            r'Contract Data Requirements List|CDRL',
            r'Performance Work Statement|PWS',
            r'Solicitation.*Document',
            r'Amendment.*\d+'
        ]
        
        for pattern in document_patterns:
            matches = re.finditer(pattern, description_text, re.IGNORECASE)
            for match in matches:
                # Extract surrounding context
                start = max(0, match.start() - 100)
                end = min(len(description_text), match.end() + 100)
                context = description_text[start:end].strip()
                
                documents.append({
                    "type": match.group(),
                    "context": context
                })
        
        return documents
    
    def generate_ai_response(self, opportunity: Dict[str, Any], 
                           detailed_description: str,
                           additional_info: Dict[str, Any],
                           documents_info: List[Dict[str, str]]) -> Optional[str]:
        """
        Generate an AI response to the solicitation
        
        Args:
            opportunity: Basic opportunity data
            detailed_description: Detailed description from API
            additional_info: Additional structured information
            documents_info: Extracted document information
            
        Returns:
            Generated AI response or None if OpenAI not configured
        """
        if not self.openai_client:
            logger.warning("OpenAI client not configured")
            return None
            
        try:
            # Format additional info for context
            additional_context = []
            for key, value in additional_info.items():
                if value:
                    additional_context.append(f"{key.replace('_', ' ').title()}: {value}")
            
            additional_text = '\n'.join(additional_context) if additional_context else 'Not available'
            
            # Format documents info
            documents_text = []
            for doc in documents_info[:5]:
                if 'name' in doc:
                    documents_text.append(f"{doc.get('type', 'Document')}: {doc.get('name', 'Unknown')} - {doc.get('description', '')}")
                else:
                    documents_text.append(f"{doc['type']}: {doc.get('context', '')[:200]}")
            
            # Prepare context for AI
            context = f"""
Solicitation Title: {opportunity.get('title', '')}
Solicitation Number: {opportunity.get('solicitationNumber', '')}
Posted Date: {opportunity.get('postedDate', '')}
Response Deadline: {opportunity.get('responseDeadLine', '')}
NAICS Code: {opportunity.get('naicsCode', '')}

Detailed Description:
{detailed_description[:3000] if detailed_description else 'Not available'}

Additional Information:
{additional_text}

Identified Documents:
{chr(10).join(documents_text) if documents_text else 'None identified'}
"""
            
            prompt = f"""
You are a government contracting expert. Based on the following solicitation information, create a professional initial response that addresses the key requirements.

{context}

Please provide:
1. Executive Summary - Brief overview of understanding
2. Technical Approach - High-level approach to meet requirements
3. Key Qualifications - Relevant experience and capabilities
4. Compliance Matrix - How you'll address major requirements
5. Next Steps - What additional information is needed

Keep the response professional and specific to the solicitation requirements. Focus on demonstrating understanding rather than making specific commitments.
"""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Use the current cost-effective model
                messages=[
                    {"role": "system", "content": "You are a government contracting expert helping to draft solicitation responses."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return f"Error generating AI response: {str(e)}"
    
    def fetch_opportunity_by_id(self, opportunity_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch opportunity data by ID from SAM.gov API
        
        Args:
            opportunity_id: The opportunity ID from SAM.gov URL
            
        Returns:
            Opportunity data or None if not found
        """
        try:
            from datetime import datetime, timedelta
            
            # SAM.gov API requires PostedFrom and PostedTo parameters
            # Try multiple date ranges since we don't know when this was posted
            today = datetime.now()
            
            date_ranges = [
                # Recent (last 3 months)
                ((today - timedelta(days=90)).strftime("%m/%d/%Y"), today.strftime("%m/%d/%Y")),
                # Last 6 months  
                ((today - timedelta(days=180)).strftime("%m/%d/%Y"), today.strftime("%m/%d/%Y")),
                # Last year
                ((today - timedelta(days=365)).strftime("%m/%d/%Y"), today.strftime("%m/%d/%Y")),
                # This year so far
                (f"01/01/{today.year}", today.strftime("%m/%d/%Y")),
            ]
            
            base_url = "https://api.sam.gov/opportunities/v2/search"
            
            # Try different search approaches with multiple date ranges
            search_variations = [
                {"q": opportunity_id},
                {"noticeId": opportunity_id}, 
                {"opportunityId": opportunity_id},
            ]
            
            for posted_from, posted_to in date_ranges:
                logger.info(f"Trying date range: {posted_from} to {posted_to}")
                
                # Base parameters for this date range
                base_params = {
                    "api_key": self.api_key,
                    "postedFrom": posted_from,
                    "postedTo": posted_to,
                    "limit": 1000
                }
                
                for variation in search_variations:
                    try:
                        params = {**base_params, **variation}
                        logger.info(f"Searching with: {variation}")
                        
                        response = self.session.get(base_url, params=params)
                        
                        if response.status_code == 200:
                            data = response.json()
                            opportunities = data.get('opportunitiesData', [])
                            
                            logger.info(f"Found {len(opportunities)} opportunities in search")
                            
                            # Look for exact match first
                            for opp in opportunities:
                                if (opp.get('noticeId') == opportunity_id or 
                                    opp.get('opportunityId') == opportunity_id or
                                    opportunity_id in str(opp.get('uiLink', ''))):
                                    logger.info(f"Found exact match: {opp.get('title')}")
                                    return opp
                            
                            # If no exact match but we have results, check if any contain the ID
                            for opp in opportunities:
                                ui_link = opp.get('uiLink', '')
                                if opportunity_id in ui_link:
                                    logger.info(f"Found match by URL: {opp.get('title')}")
                                    return opp
                                    
                        else:
                            logger.warning(f"API request failed with status {response.status_code}: {response.text}")
                            
                    except Exception as e:
                        logger.warning(f"Search attempt failed: {e}")
                        continue
            
            logger.warning(f"No opportunity found for ID: {opportunity_id}")
            return None
                
        except Exception as e:
            logger.error(f"Error fetching opportunity by ID {opportunity_id}: {e}")
            return None
    
    def analyze_by_url(self, sam_url: str) -> Dict[str, Any]:
        """
        Analyze solicitation by SAM.gov URL
        
        Args:
            sam_url: SAM.gov opportunity URL
            
        Returns:
            Analysis results dictionary
        """
        # Extract opportunity ID from URL
        import re
        match = re.search(r'/opp/([a-f0-9]{32})/view', sam_url)
        if not match:
            raise ValueError("Could not extract opportunity ID from URL")
        
        opportunity_id = match.group(1)
        logger.info(f"Extracted opportunity ID: {opportunity_id}")
        
        # Fetch opportunity data
        opportunity = self.fetch_opportunity_by_id(opportunity_id)
        if not opportunity:
            return {
                "error": f"Could not fetch opportunity data for ID: {opportunity_id}",
                "opportunity_id": opportunity_id,
                "url": sam_url
            }
        
        # Analyze the opportunity
        return self.analyze_solicitation(opportunity)

    def analyze_solicitation(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Complete analysis of a solicitation using only API data
        
        Args:
            opportunity: Opportunity data from API
            
        Returns:
            Analysis results dictionary
        """
        logger.info(f"Analyzing solicitation: {opportunity.get('title')}")
        
        # Extract detailed information from API data
        detailed_description = self.fetch_detailed_description(opportunity)
        additional_info = self.extract_additional_info(opportunity)
        documents_info = self.extract_documents_info(opportunity)
        
        # Generate AI response (optional)
        ai_response = None
        if self.openai_client:
            try:
                ai_response = self.generate_ai_response(
                    opportunity, 
                    detailed_description, 
                    additional_info,
                    documents_info
                )
            except Exception as e:
                logger.warning(f"AI response generation failed: {e}")
                ai_response = f"AI response unavailable: {str(e)}"
        
        return {
            "opportunity": opportunity,
            "detailed_description": detailed_description,
            "additional_info": additional_info,
            "documents_info": documents_info,
            "ai_response": ai_response,
            "analysis_timestamp": datetime.now().isoformat()
        }