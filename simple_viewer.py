"""
Simple viewer for opportunities.json
"""

from flask import Flask, render_template, jsonify, request
import json
import os
from dotenv import load_dotenv

try:
    from govbizops.sam_scraper import scrape_sam_opportunity
except ImportError:
    from sam_scraper import scrape_sam_opportunity

load_dotenv()

# Configure Flask to use templates folder for both templates and static files
import pkg_resources
try:
    # When installed as package
    template_folder = pkg_resources.resource_filename('govbizops', 'templates')
    app = Flask(__name__, template_folder=template_folder, static_folder=template_folder)
except:
    # When running directly
    app = Flask(__name__, static_folder='templates')


def get_data_dir():
    """Get data directory"""
    return os.path.join(os.getcwd(), 'data')

@app.route('/')
def index():
    """Display opportunities from opportunities.json"""
    json_file = os.path.join(get_data_dir(), 'opportunities.json')

    if not os.path.exists(json_file):
        return f"<h1>Error</h1><p>File '{json_file}' not found. Run the collector first.</p>"
    
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        # Extract opportunities and sort by collected date
        opportunities = []
        for notice_id, opp_data in data.items():
            opp = opp_data['data']
            opp['_collected_date'] = opp_data['collected_date']
            opportunities.append(opp)
        
        # Sort by posted date (newest first)
        opportunities.sort(key=lambda x: x.get('postedDate', ''), reverse=True)
        
        return render_template('simple_viewer.html', 
                             opportunities=opportunities,
                             total=len(opportunities))
    
    except Exception as e:
        return f"<h1>Error</h1><p>Error reading JSON file: {str(e)}</p>"

@app.route('/export/<notice_id>')
def export_opportunity(notice_id):
    """Export a single opportunity as JSON, optionally with scraped description"""
    json_file = os.path.join(get_data_dir(), 'opportunities.json')
    include_description = request.args.get('description', 'false').lower() == 'true'

    if not os.path.exists(json_file):
        return jsonify({"error": "No opportunities data found"}), 404

    try:
        with open(json_file, 'r') as f:
            data = json.load(f)

        if notice_id not in data:
            return jsonify({"error": "Opportunity not found"}), 404

        opportunity = data[notice_id]['data'].copy()

        # If description is requested and not already cached, scrape it
        if include_description:
            # Check if we already have a scraped description cached
            if 'scraped_description' not in data[notice_id]:
                # Scrape the description
                url = opportunity.get('uiLink')
                if url:
                    try:
                        # scrape_sam_opportunity already handles async internally
                        scraped_data = scrape_sam_opportunity(url)

                        if scraped_data and scraped_data.get('success'):
                            description = scraped_data.get('description')
                            if description:
                                # Cache the scraped description
                                data[notice_id]['scraped_description'] = description

                                # Save updated data back to file
                                with open(json_file, 'w') as f:
                                    json.dump(data, f, indent=2)

                                opportunity['scraped_description'] = description
                            else:
                                opportunity['scraping_note'] = 'No description found on page'
                        else:
                            opportunity['scraping_note'] = 'Failed to scrape page'
                    except Exception as e:
                        # If scraping fails, just continue without description
                        opportunity['scraping_error'] = str(e)
            else:
                # Use cached description
                opportunity['scraped_description'] = data[notice_id]['scraped_description']

        return jsonify(opportunity)

    except Exception as e:
        return jsonify({"error": f"Export failed: {str(e)}"}), 500

if __name__ == '__main__':
    # Ensure data directory exists
    os.makedirs(get_data_dir(), exist_ok=True)

    print("Simple Viewer Configuration:")
    print(f"Data directory: {get_data_dir()}")

    app.run(debug=True, port=5000)