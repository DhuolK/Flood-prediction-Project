from flask_mail import Mail, Message
from flask import current_app
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Mail
mail = Mail()

def init_email_service(app):
    """Initialize email service with app configuration"""
    app.config.update(
        MAIL_SERVER='smtp.gmail.com',
        MAIL_PORT=465,
        MAIL_USE_SSL=True,
        MAIL_USE_TLS=False,
        MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
        MAIL_PASSWORD=os.getenv('MAIL_PASSWORD'),
        MAIL_DEFAULT_SENDER=os.getenv('MAIL_USERNAME')
    )
    mail.init_app(app)

def send_password_reset_email(user_email, user_name, reset_link):
    try:
        msg = Message('Password Reset Request',
                    sender=current_app.config['MAIL_DEFAULT_SENDER'],
                    recipients=[user_email])
        
        msg.body = f'''Hello {user_name},

You requested a password reset for your account.
Please click the following link to reset your password:

{reset_link}

If you did not request this reset, please ignore this email.
This link will expire in 1 hour for security purposes.

Best regards,
Flood Prediction System Team'''
        
        msg.html = f'''
        <h2>Hello {user_name},</h2>
        <p>You requested a password reset for your account.</p>
        <p>Please click the button below to reset your password:</p>
        <p>
            <a href="{reset_link}" style="
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 15px 32px;
                text-align: center;
                text-decoration: none;
                display: inline-block;
                font-size: 16px;
                margin: 4px 2px;
                cursor: pointer;
                border-radius: 4px;">
                Reset Password
            </a>
        </p>
        <p>If the button doesn't work, copy and paste this link in your browser:</p>
        <p>{reset_link}</p>
        <p>If you did not request this reset, please ignore this email.</p>
        <p>This link will expire in 1 hour for security purposes.</p>
        <br>
        <p>Best regards,<br>Flood Prediction System Team</p>
        '''
        
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Email sending error: {str(e)}")
        return False 