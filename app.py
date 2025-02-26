from flask import Flask, request, jsonify, send_file, render_template
import google.generativeai as genai
import os
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# Load API key from .env file
load_dotenv()
api_key = os.getenv("GENAI_API_KEY")

# Verify API key exists
if not api_key:
    raise ValueError("Error: GENAI_API_KEY is missing in .env file!")

genai.configure(api_key=api_key)

# Check available models
try:
    available_models = [model.name for model in genai.list_models()]
    print("Available Models:", available_models)
    
    if "models/gemini-1.5-pro" not in available_models:
        raise ValueError("Error: 'models/gemini-1.5-pro' model is not available for your API key!")
except Exception as e:
    raise ValueError(f"Error fetching available models: {str(e)}")

app = Flask(__name__)

def generate_medical_advice(name, age, gender, symptoms):
    """Generate medical advice using Google Generative AI (gemini-1.5-pro)."""
    prompt = f"""
    Patient Name: {name}
    Age: {age}
    Gender: {gender}
    Symptoms: {symptoms}
    
    Provide a professional medical recommendation, including medicines and solutions.
    """

    try:
        model = genai.GenerativeModel("models/gemini-1.5-pro")
        response = model.generate_content(prompt)
        
        # Handle response structure
        if hasattr(response, "text"):
            return response.text
        elif response and response.candidates:
            return response.candidates[0].content
        else:
            return "No response from AI model."
    except Exception as e:
        return f"Error generating advice: {str(e)}"

def create_prescription_pdf(name, age, gender, symptoms, advice):
    """Generate a well-formatted PDF prescription with proper line breaks."""
    file_path = f"prescription_{name}.pdf"
    
    # Remove existing file to prevent conflicts
    if os.path.exists(file_path):
        os.remove(file_path)

    doc = SimpleDocTemplate(file_path, pagesize=letter)
    styles = getSampleStyleSheet()
    content = []

    # Title
    title = Paragraph("<b>AI Doctor - Medical Prescription</b>", styles['Title'])
    content.append(title)
    content.append(Spacer(1, 20))  # Bigger gap for clarity

    # Patient Details (Each line as a separate paragraph)
    content.append(Paragraph(f"<b>Patient Name:</b> {name}", styles['Normal']))
    content.append(Spacer(1, 5))
    content.append(Paragraph(f"<b>Age:</b> {age}", styles['Normal']))
    content.append(Spacer(1, 5))
    content.append(Paragraph(f"<b>Gender:</b> {gender}", styles['Normal']))
    content.append(Spacer(1, 5))
    content.append(Paragraph(f"<b>Symptoms:</b> {symptoms}", styles['Normal']))
    content.append(Spacer(1, 20))  # Bigger gap before treatment

    # Treatment Section Title
    content.append(Paragraph("<b>Recommended Treatment:</b>", styles['Heading2']))
    content.append(Spacer(1, 12))

    # Medical Advice (Split by new lines)
    for line in advice.split("\n"):
        if line.strip():  # Ignore empty lines
            content.append(Paragraph(line, styles['Normal']))
            content.append(Spacer(1, 8))  # Space after each line

    content.append(Spacer(1, 20))

    # Encouraging Message
    content.append(Paragraph("<b>Stay strong! You will get well soon.</b>", styles['Italic']))

    # Build PDF
    doc.build(content)
    return file_path

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get_advice', methods=['POST'])
def get_advice():
    """Endpoint to get medical advice based on user input."""
    data = request.json
    name = data.get("name", "Patient")
    age = data.get("age", "Unknown")
    gender = data.get("gender", "Unknown")
    symptoms = data.get("symptoms", "").strip()

    if not symptoms:
        return jsonify({"error": "Please provide symptoms."}), 400

    advice = generate_medical_advice(name, age, gender, symptoms)
    pdf_path = create_prescription_pdf(name, age, gender, symptoms, advice)

    return jsonify({"advice": advice, "pdf": f"/download/{name}", "ask_again": True})

@app.route('/download/<name>', methods=['GET'])
def download_pdf(name):
    """Endpoint to download the generated PDF prescription."""
    file_path = f"prescription_{name}.pdf"
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({"error": "File not found"}), 404

@app.route('/ask_again', methods=['POST'])
def ask_again():
    """Endpoint to reset the form."""
    return jsonify({"message": "Previous response cleared. Please enter new details."})

if __name__ == '__main__':
    app.run(debug=True)
