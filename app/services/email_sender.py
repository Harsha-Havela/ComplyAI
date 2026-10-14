"""
Email Sender — Isolated SMTP module.

This is a NEW file. It does NOT replace email_service.py.
It provides a proper SMTP send function and professional HTML templates
for task assignment and compliance reminder emails.

Called by: notification_triggers.py (also new)
"""
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


def _smtp_configured():
    """Return True only when all required SMTP env vars are present."""
    return bool(os.environ.get('MAIL_USERNAME') and os.environ.get('MAIL_PASSWORD'))


def _send_smtp(to_email: str, subject: str, html_body: str, text_body: str) -> bool:
    """
    Core SMTP send.  Returns True on success, False on failure.
    Never raises — callers must not crash because of email.
    """
    if not _smtp_configured():
        logger.info("SMTP not configured — skipping email to %s | subject: %s", to_email, subject)
        return False

    smtp_server = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    smtp_port   = int(os.environ.get('MAIL_PORT', 587))
    smtp_user   = os.environ.get('MAIL_USERNAME')
    smtp_pass   = os.environ.get('MAIL_PASSWORD')
    from_addr   = os.environ.get('MAIL_DEFAULT_SENDER') or smtp_user

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = f"ComplyAI <{from_addr}>"
        msg['To']      = to_email
        msg.attach(MIMEText(text_body, 'plain'))
        msg.attach(MIMEText(html_body,  'html'))

        with smtplib.SMTP(smtp_server, smtp_port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        logger.info("Email sent to %s | subject: %s", to_email, subject)
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed — check MAIL_USERNAME/MAIL_PASSWORD")
    except smtplib.SMTPException as exc:
        logger.error("SMTP error sending to %s: %s", to_email, exc)
    except Exception as exc:
        logger.error("Unexpected error sending email to %s: %s", to_email, exc)

    return False


# ─────────────────────────────────────────────
#  Public send functions
# ─────────────────────────────────────────────

def send_task_assignment_email(to_email: str, employee_name: str,
                                task_title: str, client_name: str,
                                due_date: str, task_id: str = None) -> bool:
    """
    Send task-assignment email to the assigned employee.
    Safe to call even when SMTP is not configured.
    """
    app_url = os.environ.get('APP_URL', 'http://127.0.0.1:5000')
    task_url = f"{app_url}/tasks/{task_id}" if task_id else f"{app_url}/tasks"

    subject = f"New Task Assigned: {task_title}"

    html_body = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body{{font-family:Arial,sans-serif;background:#f4f6f8;margin:0;padding:0}}
  .wrap{{max-width:600px;margin:32px auto;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08)}}
  .hdr{{background:linear-gradient(135deg,#1a56db,#0f172a);padding:28px 32px;color:#fff}}
  .hdr h1{{margin:0;font-size:22px}}.hdr p{{margin:4px 0 0;opacity:.8;font-size:13px}}
  .body{{padding:28px 32px}}
  .row{{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #f1f5f9;font-size:14px}}
  .row .lbl{{color:#64748b;font-weight:600}}.row .val{{color:#1e293b}}
  .btn{{display:inline-block;margin-top:24px;padding:12px 28px;background:#1a56db;color:#fff;text-decoration:none;border-radius:8px;font-size:14px;font-weight:600}}
  .ftr{{background:#f8fafc;padding:16px 32px;font-size:12px;color:#94a3b8;text-align:center}}
</style>
</head>
<body>
<div class="wrap">
  <div class="hdr">
    <h1>🛡️ ComplyAI</h1>
    <p>Task Compliance Platform</p>
  </div>
  <div class="body">
    <h2 style="margin-top:0;color:#1e293b">New Task Assigned</h2>
    <p style="color:#64748b;font-size:14px">Hi {employee_name}, a new task has been assigned to you.</p>
    <div class="row"><span class="lbl">Task</span><span class="val">{task_title}</span></div>
    <div class="row"><span class="lbl">Client</span><span class="val">{client_name}</span></div>
    <div class="row"><span class="lbl">Due Date</span><span class="val">{due_date or 'Not set'}</span></div>
    <a href="{task_url}" class="btn">View Task →</a>
  </div>
  <div class="ftr">&copy; 2025 ComplyAI. This is an automated notification.</div>
</div>
</body>
</html>"""

    text_body = (
        f"Hi {employee_name},\n\n"
        f"A new task has been assigned to you:\n\n"
        f"  Task   : {task_title}\n"
        f"  Client : {client_name}\n"
        f"  Due    : {due_date or 'Not set'}\n\n"
        f"View it here: {task_url}\n\n"
        f"— ComplyAI"
    )

    return _send_smtp(to_email, subject, html_body, text_body)


def send_compliance_deadline_email(to_email: str, recipient_name: str,
                                    compliance_type: str, client_name: str,
                                    due_date: str, days_remaining: int,
                                    compliance_id: str = None) -> bool:
    """
    Send upcoming-deadline reminder email.
    Safe to call even when SMTP is not configured.
    """
    app_url = os.environ.get('APP_URL', 'http://127.0.0.1:5000')
    comp_url = f"{app_url}/compliance/{compliance_id}" if compliance_id else f"{app_url}/compliance"

    urgency = "URGENT" if days_remaining <= 2 else ("Due Soon" if days_remaining <= 7 else "Upcoming")
    subject = f"[{urgency}] {compliance_type} deadline in {days_remaining} day(s)"

    badge_color = "#ef4444" if days_remaining <= 2 else ("#f59e0b" if days_remaining <= 7 else "#1a56db")

    html_body = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body{{font-family:Arial,sans-serif;background:#f4f6f8;margin:0;padding:0}}
  .wrap{{max-width:600px;margin:32px auto;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08)}}
  .hdr{{background:linear-gradient(135deg,#1a56db,#0f172a);padding:28px 32px;color:#fff}}
  .hdr h1{{margin:0;font-size:22px}}.hdr p{{margin:4px 0 0;opacity:.8;font-size:13px}}
  .body{{padding:28px 32px}}
  .badge{{display:inline-block;padding:6px 14px;background:{badge_color};color:#fff;border-radius:20px;font-size:13px;font-weight:600;margin-bottom:20px}}
  .row{{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #f1f5f9;font-size:14px}}
  .row .lbl{{color:#64748b;font-weight:600}}.row .val{{color:#1e293b}}
  .btn{{display:inline-block;margin-top:24px;padding:12px 28px;background:#1a56db;color:#fff;text-decoration:none;border-radius:8px;font-size:14px;font-weight:600}}
  .ftr{{background:#f8fafc;padding:16px 32px;font-size:12px;color:#94a3b8;text-align:center}}
</style>
</head>
<body>
<div class="wrap">
  <div class="hdr">
    <h1>🛡️ ComplyAI</h1>
    <p>Tax Compliance Platform</p>
  </div>
  <div class="body">
    <h2 style="margin-top:0;color:#1e293b">Compliance Deadline Reminder</h2>
    <span class="badge">{days_remaining} day(s) remaining</span>
    <div class="row"><span class="lbl">Compliance</span><span class="val">{compliance_type}</span></div>
    <div class="row"><span class="lbl">Client</span><span class="val">{client_name or 'General'}</span></div>
    <div class="row"><span class="lbl">Due Date</span><span class="val">{due_date}</span></div>
    <a href="{comp_url}" class="btn">View Compliance →</a>
  </div>
  <div class="ftr">&copy; 2025 ComplyAI. This is an automated notification.</div>
</div>
</body>
</html>"""

    text_body = (
        f"Hi {recipient_name},\n\n"
        f"Compliance deadline reminder:\n\n"
        f"  Type    : {compliance_type}\n"
        f"  Client  : {client_name or 'General'}\n"
        f"  Due     : {due_date}\n"
        f"  In      : {days_remaining} day(s)\n\n"
        f"View it here: {comp_url}\n\n"
        f"— ComplyAI"
    )

    return _send_smtp(to_email, subject, html_body, text_body)


def send_overdue_compliance_email(to_email: str, recipient_name: str,
                                   compliance_type: str, client_name: str,
                                   due_date: str, compliance_id: str = None) -> bool:
    """
    Send overdue-compliance alert email.
    Safe to call even when SMTP is not configured.
    """
    app_url = os.environ.get('APP_URL', 'http://127.0.0.1:5000')
    comp_url = f"{app_url}/compliance/{compliance_id}" if compliance_id else f"{app_url}/compliance"

    subject = f"[OVERDUE] {compliance_type} — {client_name or 'General'}"

    html_body = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body{{font-family:Arial,sans-serif;background:#f4f6f8;margin:0;padding:0}}
  .wrap{{max-width:600px;margin:32px auto;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08)}}
  .hdr{{background:linear-gradient(135deg,#ef4444,#991b1b);padding:28px 32px;color:#fff}}
  .hdr h1{{margin:0;font-size:22px}}.hdr p{{margin:4px 0 0;opacity:.8;font-size:13px}}
  .body{{padding:28px 32px}}
  .alert{{background:#fef2f2;border-left:4px solid #ef4444;padding:14px 16px;border-radius:0 8px 8px 0;margin-bottom:20px;font-size:14px;color:#991b1b}}
  .row{{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #f1f5f9;font-size:14px}}
  .row .lbl{{color:#64748b;font-weight:600}}.row .val{{color:#1e293b}}
  .btn{{display:inline-block;margin-top:24px;padding:12px 28px;background:#ef4444;color:#fff;text-decoration:none;border-radius:8px;font-size:14px;font-weight:600}}
  .ftr{{background:#f8fafc;padding:16px 32px;font-size:12px;color:#94a3b8;text-align:center}}
</style>
</head>
<body>
<div class="wrap">
  <div class="hdr">
    <h1>🛡️ ComplyAI</h1>
    <p>Tax Compliance Platform</p>
  </div>
  <div class="body">
    <h2 style="margin-top:0;color:#991b1b">Compliance Overdue Alert</h2>
    <div class="alert">⚠️ This compliance item is past its due date and requires immediate attention.</div>
    <div class="row"><span class="lbl">Compliance</span><span class="val">{compliance_type}</span></div>
    <div class="row"><span class="lbl">Client</span><span class="val">{client_name or 'General'}</span></div>
    <div class="row"><span class="lbl">Was Due</span><span class="val">{due_date}</span></div>
    <a href="{comp_url}" class="btn">View & Resolve →</a>
  </div>
  <div class="ftr">&copy; 2025 ComplyAI. This is an automated notification.</div>
</div>
</body>
</html>"""

    text_body = (
        f"Hi {recipient_name},\n\n"
        f"OVERDUE compliance alert:\n\n"
        f"  Type   : {compliance_type}\n"
        f"  Client : {client_name or 'General'}\n"
        f"  Was due: {due_date}\n\n"
        f"Please resolve immediately: {comp_url}\n\n"
        f"— ComplyAI"
    )

    return _send_smtp(to_email, subject, html_body, text_body)
