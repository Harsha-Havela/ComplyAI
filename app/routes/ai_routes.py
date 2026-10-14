"""
AI Assistant Routes
AI-powered features using Google Gemini
"""
from flask import Blueprint, render_template, request, jsonify, session
from app.utils.auth import login_required
from app.services.ai_service import (
    answer_tax_question, explain_gst_term, summarize_document,
    generate_reminder_email, generate_task_description, generate_professional_note
)

ai_bp = Blueprint('ai', __name__)


@ai_bp.route('/')
@login_required
def index():
    """AI Assistant main page."""
    return render_template('ai/index.html')


@ai_bp.route('/ask', methods=['POST'])
@login_required
def ask_question():
    """Handle tax question via AI."""
    data = request.get_json()
    question = data.get('question', '')
    
    if not question:
        return jsonify({'error': 'Question is required'}), 400
    
    response = answer_tax_question(question)
    return jsonify(response)


@ai_bp.route('/explain-term', methods=['POST'])
@login_required
def explain_term():
    """Explain GST terminology."""
    data = request.get_json()
    term = data.get('term', '')
    
    if not term:
        return jsonify({'error': 'Term is required'}), 400
    
    response = explain_gst_term(term)
    return jsonify(response)


@ai_bp.route('/summarize', methods=['POST'])
@login_required
def summarize():
    """Summarize document."""
    data = request.get_json()
    document_text = data.get('document_text', '')
    
    if not document_text:
        return jsonify({'error': 'Document text is required'}), 400
    
    response = summarize_document(document_text)
    return jsonify(response)


@ai_bp.route('/generate-email', methods=['POST'])
@login_required
def generate_email():
    """Generate reminder email."""
    data = request.get_json()
    client_name = data.get('client_name', '')
    compliance_type = data.get('compliance_type', '')
    due_date = data.get('due_date', '')
    
    response = generate_reminder_email(client_name, compliance_type, due_date)
    return jsonify(response)


@ai_bp.route('/generate-task', methods=['POST'])
@login_required
def generate_task():
    """Generate task description."""
    data = request.get_json()
    task_title = data.get('task_title', '')
    client_name = data.get('client_name', '')
    compliance_type = data.get('compliance_type', '')
    
    response = generate_task_description(task_title, client_name, compliance_type)
    return jsonify(response)


@ai_bp.route('/generate-note', methods=['POST'])
@login_required
def generate_note():
    """Generate professional note."""
    data = request.get_json()
    context = data.get('context', '')
    note_type = data.get('note_type', 'general')
    
    response = generate_professional_note(context, note_type)
    return jsonify(response)
