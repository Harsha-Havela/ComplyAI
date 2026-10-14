"""
Email Service
Handles all email operations including activation emails
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_activation_email(to_email, full_name, username, activation_token):
    """
    Send account activation email to new user.
    
    Args:
        to_email: Recipient email address
        full_name: User's full name
        username: Username for login
        activation_token: Unique activation token
        
    Returns:
        bool: True if sent successfully
    """
    # Generate activation URL
    activation_url = f"http://127.0.0.1:5000/activate/{activation_token}"
    
    subject = "Welcome to ComplyAI - Activate Your Account"
    
    # HTML email body
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 5px 5px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border: 1px solid #ddd; border-top: none; }}
            .button {{ display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
            .info {{ background: #e3f2fd; padding: 15px; border-left: 4px solid #2196f3; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🛡️ ComplyAI</h1>
                <p>Tax Compliance Management</p>
            </div>
            <div class="content">
                <h2>Welcome, {full_name}!</h2>
                <p>Your account has been created by your administrator.</p>
                <div class="info">
                    <strong>Username:</strong> {username}
                </div>
                <p>Click below to activate your account and set your password:</p>
                <center>
                    <a href="{activation_url}" class="button">Activate My Account</a>
                </center>
                <p><small>Or copy this link: {activation_url}</small></p>
                <p><strong>Note:</strong> This link expires in 48 hours.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Plain text version
    text_body = f"""
Welcome to ComplyAI!

Hi {full_name},

Your account has been created.
Username: {username}

To activate your account and set your password, visit:
{activation_url}

This link expires in 48 hours.

Best regards,
ComplyAI Team
    """
    
    # Check if SMTP is configured
    smtp_configured = (
        os.environ.get('MAIL_USERNAME') and 
        os.environ.get('MAIL_PASSWORD')
    )
    
    if smtp_configured:
        # PRODUCTION MODE: Actually send email via SMTP
        try:
            smtp_server = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
            smtp_port = int(os.environ.get('MAIL_PORT', 587))
            smtp_user = os.environ.get('MAIL_USERNAME')
            smtp_pass = os.environ.get('MAIL_PASSWORD')
            from_email = os.environ.get('MAIL_DEFAULT_SENDER', smtp_user)
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = from_email
            msg['To'] = to_email
            
            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            
            print(f"✅ Activation email sent to {to_email}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            print(f"📧 Activation URL (fallback): {activation_url}")
            return False
    else:
        # DEVELOPMENT MODE: Print to console
        print("\n" + "=" * 70)
        print("📧 ACTIVATION EMAIL (Development Mode - SMTP Not Configured)")
        print("=" * 70)
        print(f"To: {to_email}")
        print(f"Name: {full_name}")
        print(f"Username: {username}")
        print(f"\n🔗 ACTIVATION LINK (Copy and share with user):")
        print(f"   {activation_url}")
        print("=" * 70)
        print("\n💡 To enable automatic email sending:")
        print("   1. Set MAIL_USERNAME and MAIL_PASSWORD in .env file")
        print("   2. Use Gmail App Password or SendGrid API")
        print("   3. See FIREBASE_SETUP.md for details\n")
        
        return True


def send_task_notification(to_email, employee_name, task_title, client_name, due_date):
    """
    Send task assignment notification email.
    
    Args:
        to_email: Recipient email
        employee_name: Name of employee
        task_title: Task title
        client_name: Client name
        due_date: Task due date
        
    Returns:
        bool: True if sent successfully
    """
    subject = f"New Task Assigned: {task_title}"
    
    body = f"""
    Dear {employee_name},
    
    A new task has been assigned to you:
    
    Task: {task_title}
    Client: {client_name}
    Due Date: {due_date}
    
    Please login to ComplyAI to view details and get started.
    
    Best regards,
    ComplyAI Team
    """
    
    # Print to console for now
    print(f"\n📧 Task notification for {to_email}: {task_title}")
    return True


def send_compliance_reminder(to_email, compliance_type, due_date, client_name):
    """
    Send compliance deadline reminder.
    
    Args:
        to_email: Recipient email
        compliance_type: Type of compliance
        due_date: Due date
        client_name: Client name
        
    Returns:
        bool: True if sent successfully
    """
    subject = f"Reminder: {compliance_type} Due on {due_date}"
    
    body = f"""
    Dear Team,
    
    Reminder for upcoming compliance deadline:
    
    Compliance: {compliance_type}
    Client: {client_name}
    Due Date: {due_date}
    
    Please ensure timely completion.
    
    Best regards,
    ComplyAI Team
    """
    
    # Print to console for now
    print(f"\n📧 Compliance reminder for {to_email}: {compliance_type}")
    return True
