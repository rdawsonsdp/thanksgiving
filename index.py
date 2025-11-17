"""
Vercel entry point - root level
Imports the Flask app from app.py
"""
import sys
import os

# Ensure we can import from the current directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app
    
    # Export handler for Vercel - Vercel looks for 'handler' or 'app'
    handler = app
    
    # Debug: Print routes if possible
    if hasattr(app, 'url_map'):
        print(f"Flask app loaded with {len(list(app.url_map.iter_rules()))} routes")
        
except Exception as e:
    # Create a minimal error app if import fails
    from flask import Flask, jsonify
    error_app = Flask(__name__)
    
    @error_app.route('/', defaults={'path': ''})
    @error_app.route('/<path:path>')
    def error_handler(path):
        import traceback
        return jsonify({
            "error": f"Failed to load Flask app: {str(e)}",
            "type": type(e).__name__,
            "traceback": traceback.format_exc()
        }), 500
    
    handler = error_app
    app = error_app

