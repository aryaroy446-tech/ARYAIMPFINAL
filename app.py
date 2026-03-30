import os
import time
import random
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import json
import time
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

app = Flask(__name__, static_folder='public', static_url_path='')
CORS(app)

# JSON Database Persistence Setup
DATABASE_DIR = os.path.join(os.path.dirname(__file__), 'database')
USERS_FILE = os.path.join(DATABASE_DIR, 'users.json')
HISTORY_FILE = os.path.join(DATABASE_DIR, 'history.json')

if not os.path.exists(DATABASE_DIR):
    os.makedirs(DATABASE_DIR)

def load_data(file_path, default_data):
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f:
            json.dump(default_data, f, indent=4)
        return default_data
    with open(file_path, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return default_data

def save_data(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

# Persistent DB loads
history_db = load_data(HISTORY_FILE, [])
users_db = load_data(USERS_FILE, {"admin": "admin123"})

@app.route('/')
def serve_index():
    return send_from_directory('public', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    if os.path.exists(os.path.join('public', path)):
        return send_from_directory('public', path)
    return send_from_directory('public', 'index.html')

def perform_ai_analysis(image_stream):
    try:
        img = Image.open(image_stream)
        
        prompt = """
        Analyze this image of a medicine packaging to determine its authenticity. Provide the result strictly as a valid JSON object matching this exact structure:
        {
          "score": <number from 0 to 100 representing authenticity score>,
          "riskLevel": "<either 'Low', 'Medium', or 'High'>",
          "details": {
            "packagingQuality": "<concise observation>",
            "brandAuthenticity": "<concise observation>",
            "safetyMarkers": "<concise observation>"
          },
          "medicineInfo": {
            "companyName": "<extracted company/manufacturer name or 'Unknown'>",
            "usage": "<primary medical use or indication or 'Unknown'>",
            "storageInstructions": "<how to store it or 'Unknown'>"
          }
        }
        Do not include markdown formatting or any other text outside the JSON.
        """
        
        response = model.generate_content([prompt, img])
        result_text = response.text.strip()
        
        # Remove potential markdown block wrappers
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
            
        return json.loads(result_text.strip())
    except Exception as e:
        print(f"Gemini API Error: {e}")
        # Fallback response on error
        return {
            "score": 50,
            "riskLevel": "Medium",
            "details": {
                "packagingQuality": "Unable to verify. AI Error.",
                "brandAuthenticity": "Unable to verify. AI Error.",
                "safetyMarkers": "Unable to verify. AI Error.",
            },
            "medicineInfo": {
                "companyName": "Unknown",
                "usage": "Unknown",
                "storageInstructions": "Unknown"
            }
        }

@app.route('/api/scan', methods=['POST'])
def scan_medicine():
    if 'medicineImage' not in request.files:
        return jsonify({"error": "No image file provided."}), 400
        
    file = request.files['medicineImage']
    if file.filename == '':
        return jsonify({"error": "No selected file."}), 400

    print(f"Received file: {file.filename}")

    # Real AI analysis using Gemini API
    analysis_result = perform_ai_analysis(file.stream)

    # Create history record
    record = {
        "id": str(int(time.time() * 1000)),
        "date": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
        "filename": secure_filename(file.filename),
        "result": analysis_result
    }
    
    history_db.insert(0, record) # Prepend
    save_data(HISTORY_FILE, history_db) # Commit to disk
    return jsonify({"success": True, "data": record})

@app.route('/api/history', methods=['GET'])
def get_history():
    return jsonify({"success": True, "data": history_db})

@app.route('/api/history/<item_id>', methods=['DELETE'])
def delete_history_item(item_id):
    global history_db
    history_db = [item for item in history_db if item['id'] != item_id]
    save_data(HISTORY_FILE, history_db) # Commit to disk
    return jsonify({"success": True})

@app.route('/api/history', methods=['DELETE'])
def delete_all_history():
    global history_db
    history_db = []
    save_data(HISTORY_FILE, history_db) # Commit to disk
    return jsonify({"success": True})

@app.route('/api/database', methods=['GET'])
def query_database():
    medicine_name = request.args.get('q', '').strip()
    if not medicine_name:
        return jsonify({"error": "Search query required."}), 400
        
    try:
        prompt = f"""
        Provide detailed, factual database information about the medicine '{medicine_name}'. 
        Return the result strictly as a valid JSON object matching this exact framework:
        {{
          "companyName": "<Primary manufacturer or company associated>",
          "primaryUses": "<What it is chiefly used to treat>",
          "activeIngredients": "<Main active chemical components>",
          "sideEffects": "<Common side effects>",
          "storageInstructions": "<How to store>"
        }}
        Do not include markdown or formatting outside the JSON block. Do not apologize or add any other text.
        """
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
            
        return jsonify({"success": True, "data": json.loads(result_text.strip())})
    except Exception as e:
        print(f"Database API Error: {e}")
        return jsonify({"error": "Failed to retrieve medicine data from AI Database."}), 500

@app.route('/api/help', methods=['GET'])
def analyze_symptoms():
    symptoms = request.args.get('symptoms', '').strip()
    if len(symptoms) < 10:
        return jsonify({"error": "Please provide more detail about your symptoms (minimum 10 characters)."}), 400
        
    try:
        prompt = f"""
        Act as a medical triage AI. The user describes their symptoms as follows:
        "{symptoms}"
        
        Evaluate the symptoms strictly according to these rules and return the result as a valid JSON object matching this structure:
        {{
          "riskLevel": "<Either 'High', 'Medium', or 'Low'>",
          "advice": "<Detailed paragraph on what actions they should take based on the symptoms>",
          "requiresDoctor": <true or false>,
          "suggestedMedicines": ["<OTC Medicine 1>", "<OTC Medicine 2>", ...]
        }}
        
        CRITICAL RULES:
        1. If the symptoms indicate ANY potential emergency or high risk (e.g., chest pain, severe bleeding, difficulty breathing, neurological deficits, severe infection), set "riskLevel" to "High", "requiresDoctor" to true, and leave "suggestedMedicines" as an empty list []. Your advice must prioritize seeking immediate emergency care.
        2. Only suggest general over-the-counter (OTC) medicines if "riskLevel" is "Low" or "Medium". Do not prescribe prescription medications.
        
        Do not include markdown or formatting outside the JSON block. Do not apologize or add any other text.
        """
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
            
        return jsonify({"success": True, "data": json.loads(result_text.strip())})
    except Exception as e:
        print(f"Help API Error: {e}")
        return jsonify({"error": "Failed to process symptoms symptom analysis engine is currently unavailable."}), 500

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    username = data.get('identifier', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({"error": "Username/Mobile and password are required."}), 400

    if username in users_db:
        return jsonify({"error": "An account with this username or mobile number already exists."}), 400

    users_db[username] = password
    save_data(USERS_FILE, users_db) # Commit user to disk permanently
    return jsonify({"success": True, "token": f"token_{username}_{int(time.time())}"})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('identifier', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({"error": "Username/Mobile and password are required."}), 400

    if users_db.get(username) == password:
         return jsonify({"success": True, "token": f"token_{username}_{int(time.time())}"})
    
    return jsonify({"error": "Invalid credentials. Please try again."}), 401

if __name__ == '__main__':
    print("MedicineGuard AI backend running continuously on http://localhost:5001")
    if not os.path.exists('public'):
        os.makedirs('public')
    app.run(host='0.0.0.0', port=5001, debug=False)
