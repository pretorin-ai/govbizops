"""
Simple viewer for federal_opportunities.json
"""

from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime
from dotenv import load_dotenv

try:
    from .solicitation_analyzer import SolicitationAnalyzer
except ImportError:
    from solicitation_analyzer import SolicitationAnalyzer

load_dotenv()

app = Flask(__name__)

@app.route('/')
def index():
    """Display opportunities from federal_opportunities.json"""
    json_file = 'federal_opportunities.json'
    
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

@app.route('/analyze/<notice_id>', methods=['POST'])
def analyze_solicitation(notice_id):
    """Analyze a specific solicitation and generate AI response"""
    
    # Check if API keys are configured
    sam_api_key = os.getenv("SAM_GOV_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not sam_api_key:
        return jsonify({"error": "SAM_GOV_API_KEY not configured"}), 400
    
    if not openai_key:
        return jsonify({"error": "OPENAI_API_KEY not configured"}), 400
    
    # Load the opportunity data
    json_file = 'federal_opportunities.json'
    if not os.path.exists(json_file):
        return jsonify({"error": "No opportunities data found"}), 400
    
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        if notice_id not in data:
            return jsonify({"error": "Opportunity not found"}), 404
        
        opportunity = data[notice_id]['data']
        
        # Initialize analyzer
        analyzer = SolicitationAnalyzer(sam_api_key)
        
        # Perform analysis
        analysis_result = analyzer.analyze_solicitation(opportunity)
        
        # Save analysis result to a separate file
        analysis_file = f"analysis_{notice_id}.json"
        with open(analysis_file, 'w') as f:
            json.dump(analysis_result, f, indent=2, default=str)
        
        return jsonify({
            "success": True,
            "message": "Analysis completed successfully",
            "analysis_file": analysis_file,
            "has_ai_response": bool(analysis_result.get("ai_response")),
            "documents_found": len(analysis_result.get("documents_info", []))
        })
        
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500

@app.route('/view_analysis/<notice_id>')
def view_analysis(notice_id):
    """View analysis results for a solicitation"""
    analysis_file = f"analysis_{notice_id}.json"
    
    if not os.path.exists(analysis_file):
        return "<h1>Analysis Not Found</h1><p>Run analysis first.</p>"
    
    try:
        with open(analysis_file, 'r') as f:
            analysis = json.load(f)
        
        return render_template('analysis_view.html', analysis=analysis, notice_id=notice_id)
        
    except Exception as e:
        return f"<h1>Error</h1><p>Error loading analysis: {str(e)}</p>"

if __name__ == '__main__':
    sam_key = os.getenv("SAM_GOV_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    print("Simple Viewer Configuration:")
    print(f"SAM.gov API Key: {'✓' if sam_key else '✗'}")
    print(f"OpenAI API Key: {'✓' if openai_key else '✗'}")
    
    app.run(debug=True, port=5000)