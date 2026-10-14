"""
Report Generation Routes
PDF report generation functionality
"""
from flask import Blueprint, send_file, session, flash, redirect, url_for
from app.utils.auth import login_required, role_required
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
import io
from datetime import datetime
from app.controllers.client_controller import get_all_clients
from app.controllers.task_controller import get_all_tasks
from app.controllers.compliance_controller import get_all_deadlines

report_bp = Blueprint('reports', __name__)


def create_pdf_report(title, headers, data, filename):
    """Generic PDF report generator."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_para = Paragraph(f"<b>{title}</b>", styles['Title'])
    elements.append(title_para)
    elements.append(Spacer(1, 0.3 * inch))
    
    # Generated date
    date_para = Paragraph(f"Generated: {datetime.now().strftime('%d %B %Y %H:%M')}", styles['Normal'])
    elements.append(date_para)
    elements.append(Spacer(1, 0.3 * inch))
    
    # Table
    table_data = [headers] + data
    table = Table(table_data)
    
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    doc.build(elements)
    
    buffer.seek(0)
    return buffer


@report_bp.route('/clients')
@login_required
@role_required('admin', 'manager')
def client_report():
    """Generate client report PDF."""
    clients = get_all_clients()
    
    headers = ['ID', 'Company Name', 'PAN', 'GSTIN', 'Status']
    data = [[
        str(c['id']),
        c['company_name'],
        c['pan'],
        c['gstin'] or 'N/A',
        c['status']
    ] for c in clients]
    
    pdf_buffer = create_pdf_report('Client Report', headers, data, 'client_report.pdf')
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'client_report_{datetime.now().strftime("%Y%m%d")}.pdf'
    )


@report_bp.route('/tasks')
@login_required
def task_report():
    """Generate task report PDF."""
    if session['role'] == 'employee':
        tasks = get_all_tasks(assigned_to=session['user_id'])
    else:
        tasks = get_all_tasks()
    
    headers = ['ID', 'Title', 'Client', 'Assigned To', 'Status', 'Due Date']
    data = [[
        str(t['id']),
        t['title'][:30],
        t['client_name'][:20],
        t['assigned_to_name'][:20],
        t['status'],
        t['due_date'] or 'N/A'
    ] for t in tasks]
    
    pdf_buffer = create_pdf_report('Task Report', headers, data, 'task_report.pdf')
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'task_report_{datetime.now().strftime("%Y%m%d")}.pdf'
    )


@report_bp.route('/compliance')
@login_required
@role_required('admin', 'manager')
def compliance_report():
    """Generate compliance report PDF."""
    deadlines = get_all_deadlines()
    
    headers = ['ID', 'Compliance Type', 'Client', 'Due Date', 'Status']
    data = [[
        str(d['id']),
        d['compliance_type'][:30],
        d['client_name'][:20] if d['client_name'] else 'General',
        d['due_date'],
        d['status']
    ] for d in deadlines]
    
    pdf_buffer = create_pdf_report('Compliance Report', headers, data, 'compliance_report.pdf')
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'compliance_report_{datetime.now().strftime("%Y%m%d")}.pdf'
    )
