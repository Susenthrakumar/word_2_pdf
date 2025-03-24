# app.py
from flask import Flask, request, render_template, send_file, jsonify
import os
from docx2pdf import convert
import uuid
import time

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'

# Create necessary directories if they don't exist
for folder in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER']]:
    if not os.path.exists(folder):
        os.makedirs(folder)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and file.filename.endswith(('.docx', '.doc')):
        # Generate unique filename to prevent collisions
        unique_id = str(uuid.uuid4())
        timestamp = int(time.time())
        file_id = f"{timestamp}_{unique_id}"
        
        # Save uploaded file with the unique ID
        input_filename = f"{file_id}_{file.filename}"
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], input_filename)
        file.save(input_path)
        
        # Create output filename and path
        output_filename = f"{file_id}_{os.path.splitext(file.filename)[0]}.pdf"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        
        try:
            # Convert Word document to PDF
            convert(input_path, output_path)
            
            # Clean up the uploaded file
            os.remove(input_path)
            
            # Return the download URL
            return jsonify({
                'success': True,
                'filename': os.path.splitext(file.filename)[0] + '.pdf',
                'download_url': f'/download/{output_filename}'
            })
            
        except Exception as e:
            # If conversion fails, clean up and return error
            if os.path.exists(input_path):
                os.remove(input_path)
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'Invalid file format. Please upload a Word document (.doc or .docx)'}), 400

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(app.config['OUTPUT_FOLDER'], filename), 
                     as_attachment=True, 
                     download_name=filename.split('_', 2)[2])  # Remove the unique ID prefix

# Clean up old files periodically (you might want to implement this as a background task)
@app.route('/cleanup', methods=['POST'])
def cleanup():
    threshold_time = time.time() - (24 * 60 * 60)  # 24 hours ago
    
    deleted_count = 0
    for folder in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER']]:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                # Extract timestamp from filename
                timestamp = int(filename.split('_')[0])
                if timestamp < threshold_time:
                    os.remove(file_path)
                    deleted_count += 1
            except (ValueError, IndexError, OSError):
                # Skip files that don't follow the naming convention or can't be deleted
                continue
    
    return jsonify({'success': True, 'deleted_count': deleted_count})

if __name__ == '__main__':
    app.run(debug=True)
