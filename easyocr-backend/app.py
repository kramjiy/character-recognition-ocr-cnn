#print("hi")
import os
import time
import uuid
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from ocr_service import OCRService

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ocr_service = OCRService(languages=['en'])

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'message': 'OCR Service is running'})

@app.route('/api/ocr', methods=['POST'])
def process_image():
    """Process an uploaded image with OCR"""
    if 'image' not in request.files:
        return jsonify({'status': 'error', 'message': 'No image provided'}), 400
    
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No image selected'}), 400
    
    # Read optional parameters
    confidence_threshold = float(request.form.get('confidence_threshold', 0.2))
    
    # Generate a unique filename to avoid collisions
    filename = str(uuid.uuid4()) + secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        # Save the uploaded file temporarily
        file.save(filepath)
        
        # Process the image with OCR
        start_time = time.time()
        result = ocr_service.extract_text(filepath, confidence_threshold=confidence_threshold)
        processing_time = time.time() - start_time
        
        # Add processing time to the result
        result['processing_time'] = round(processing_time, 2)
        
        # Clean up - remove the uploaded file
        if os.path.exists(filepath):
            os.remove(filepath)
        
        return jsonify(result)
    
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/ocr/advanced', methods=['POST'])
def advanced_image_processing():
    """Process an image with advanced options"""
    if 'image' not in request.files:
        return jsonify({'status': 'error', 'message': 'No image provided'}), 400
    
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No image selected'}), 400
    
    confidence_threshold = float(request.form.get('confidence_threshold', 0.2))
    save_debug_images = request.form.get('save_debug_images', 'false').lower() == 'true'
    
    filename = str(uuid.uuid4()) + secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        file.save(filepath)
        
        start_time = time.time()
        result = ocr_service.extract_text(filepath, confidence_threshold=confidence_threshold)
        processing_time = time.time() - start_time
        
        result['processing_time'] = round(processing_time, 2)
        
        if os.path.exists(filepath) and not save_debug_images:
            os.remove(filepath)
        
        return jsonify(result)
    
    except Exception as e:
        if os.path.exists(filepath) and not save_debug_images:
            os.remove(filepath)
        
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)