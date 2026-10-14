"""
AI Service using Google Gemini API
Handles all AI-powered features
"""
import google.generativeai as genai
from flask import current_app


def configure_gemini():
    """Configure Gemini API with key."""
    api_key = current_app.config.get('GEMINI_API_KEY')
    if api_key:
        genai.configure(api_key=api_key)
        return True
    return False


def get_gemini_response(prompt, temperature=0.7):
    """Get response from Gemini API."""
    try:
        if not configure_gemini():
            return {"error": "Gemini API key not configured"}
        
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=2048,
            )
        )
        
        return {"success": True, "response": response.text}
    
    except Exception as e:
        return {"error": str(e)}


def answer_tax_question(question):
    """Answer tax-related questions."""
    prompt = f"""You are a tax compliance expert for Indian taxation laws. 
Answer the following question accurately and professionally:

Question: {question}

Provide a clear, concise answer with relevant sections or rules if applicable."""
    
    return get_gemini_response(prompt)


def explain_gst_term(term):
    """Explain GST terminology."""
    prompt = f"""You are a GST expert. Explain the following GST term in simple, professional language 
suitable for chartered accountants and business owners:

Term: {term}

Provide definition, usage, and relevant examples."""
    
    return get_gemini_response(prompt)


def summarize_document(document_text):
    """Summarize compliance documents."""
    prompt = f"""Summarize the following compliance document. Focus on key points, 
deadlines, requirements, and action items:

{document_text[:3000]}

Provide a structured summary with bullet points."""
    
    return get_gemini_response(prompt)


def generate_reminder_email(client_name, compliance_type, due_date):
    """Generate professional reminder email."""
    prompt = f"""Generate a professional reminder email for:
Client: {client_name}
Compliance: {compliance_type}
Due Date: {due_date}

Include:
- Professional greeting
- Purpose of the email
- Clear deadline
- Required actions
- Contact information placeholder
- Professional closing

Keep it concise and formal."""
    
    return get_gemini_response(prompt, temperature=0.5)


def generate_task_description(task_title, client_name, compliance_type):
    """Generate detailed task description."""
    prompt = f"""Generate a detailed task description for:
Task: {task_title}
Client: {client_name}
Compliance Type: {compliance_type}

Include:
- Task overview
- Required documents
- Steps to complete
- Important notes
- Estimated time

Format professionally for a compliance management system."""
    
    return get_gemini_response(prompt, temperature=0.6)


def generate_professional_note(context, note_type="general"):
    """Generate professional notes."""
    prompt = f"""Generate a professional {note_type} note for:
Context: {context}

Create a well-structured, formal note suitable for client communication 
or internal documentation."""
    
    return get_gemini_response(prompt, temperature=0.6)
