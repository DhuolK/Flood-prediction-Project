from flask import Blueprint, render_template, request, jsonify, session, url_for, redirect, send_from_directory, current_app
from werkzeug.security import generate_password_hash, check_password_hash
import os
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
from flask_mail import Mail, Message
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import datetime
from dotenv import load_dotenv
from datetime import datetime, timedelta
import secrets
import jwt
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ssl
import logging
import traceback
from email_service import mail, send_password_reset_email
from pymongo import MongoClient
import uuid
from functools import wraps
import pymongo

# Load environment variables
load_dotenv()

# Create a Blueprint instead of a Flask app
auth = Blueprint('auth', __name__)

# MongoDB setup
client = MongoClient('mongodb://localhost:27017/login')
db = client.user_login
users_collection = db.users

# Create serializer using the secret key with a fallback
secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here-1234567890')
serializer = URLSafeTimedSerializer(secret_key)

# Store tokens with expiry (in memory for demonstration)
reset_tokens = {}

def get_initials(name):
    if not name:
        return ''
    name_parts = name.split()
    initials = ''.join([part[0].upper() for part in name_parts])  # Extract initials from name parts
    return initials

def login_required(f):
    @wraps(f)  
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('auth.login_page'))  # Ensure correct route name
        return f(*args, **kwargs)
    return decorated_function

# Add test user if it doesn't exist
test_user = users_collection.find_one({"email": "kmuli7313@gmail.com"})
if not test_user:
    users_collection.insert_one({
        "name": "Test User",
        "email": "kmuli7313@gmail.com",
        "mobilenumber": "1234567890",
        'initials': get_initials("Test User"),
        "password": generate_password_hash("test")
    })

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@auth.route('/signup')
def signup_page():
    return render_template('signup.html')

@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        # Handle GET request with query parameters
        name = request.args.get('name')
        email = request.args.get('email')
        mobilenumber = request.args.get('mobilenumber')
        password = request.args.get('password')
        
        if not all([name, email, mobilenumber, password]):
            return render_template('signup.html')
            
        data = {
            "name": name,
            "email": email,
            "mobilenumber": mobilenumber,
            "password": password
        }
    else:
        # Handle POST request with JSON data
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

    try:
        # Check if required fields exist
        required_fields = ["name", "mobilenumber", "email", "password"]
        for field in required_fields:
            if field not in data:
                if request.method == 'GET':
                    return render_template('signup.html', error=f"Missing field: {field}")
                return jsonify({"error": f"Missing field: {field}"}), 400

        # Check if user already exists
        if users_collection.find_one({"email": data['email']}):
            if request.method == 'GET':
                return render_template('signup.html', error="Email already registered")
            return jsonify({"error": "Email already registered"}), 400

        # Hash password
        hashed_password = generate_password_hash(data['password'])

        # Create new user document
        new_user = {
            "name": data['name'],
            "email": data['email'],
            "mobilenumber": data['mobilenumber'],
            "password": hashed_password,
            "initials": get_initials(data['name'])
        }

        # Insert user into database
        users_collection.insert_one(new_user)

        # Store full user info in session
        session['user'] = {
            "name": data['name'],
            "email": data['email'],
            "mobilenumber": data['mobilenumber'],
            "initials": get_initials(data['name'])
        }

        if request.method == 'GET':
            # Set a success message in the session
            session['signup_success'] = "Registration successful! Please log in."
            return redirect(url_for('auth.login_page'))
        return jsonify({"message": "User registered successfully"}), 201

    except pymongo.errors.DuplicateKeyError:
        print(f"Duplicate email error: {data['email']}")
        if request.method == 'GET':
            return render_template('signup.html', error="Email already registered")
        return jsonify({"error": "Email already registered"}), 400
    except Exception as e:
        print(f"Signup error: {str(e)}")
        if request.method == 'GET':
            return render_template('signup.html', error="Failed to register user. Please try again.")
        return jsonify({"error": "Failed to register user"}), 500

@auth.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'GET':
        return render_template('login.html')

    try:
        data = request.get_json()
        user = users_collection.find_one({"email": data.get('email')})

        if user and check_password_hash(user['password'], data.get('password')):
            session['user'] = {
                'name': user.get('name', ''),
                'email': user.get('email', ''),
                'mobilenumber': user.get('mobilenumber', ''),
                'initials': user.get('initials', ''),  # Ensure initials are stored
                'instance': user.get('instance', None),
            }
            return jsonify({"message": "Logged in successfully"})

        return jsonify({"error": "Invalid Email or Password"}), 401

    except Exception as e:
        print(f"Login error: {str(e)}")
        return jsonify({"error": "Login failed"}), 500

@auth.route('/api/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'GET':
        return render_template('forgot_password.html')

    try:
        email = request.get_json().get('email') if request.is_json else request.form.get('email')

        if not email:
            return jsonify({"error": "Email is required"}), 400

        user = users_collection.find_one({"email": email})
        message = "If an account exists with this email, a password reset link will be sent."

        if user:
            try:
                # Generate token with expiry
                token = serializer.dumps(email, salt='password-reset-salt')
                reset_link = f"http://localhost:5000/reset_password?token={token}"

                # Use the email service to send the reset email
                if send_password_reset_email(email, user.get('name', 'User'), reset_link):
                    return jsonify({"message": "Password reset email sent successfully"}), 200
                else:
                    return jsonify({"error": "Failed to send reset email"}), 500

            except Exception as e:
                print(f"Email sending error: {str(e)}")
                return jsonify({"error": "Failed to send reset email"}), 500

        return jsonify({"message": message}), 200

    except Exception as e:
        print(f"Password reset error: {str(e)}")
        return jsonify({"error": "Failed to process request"}), 500

@auth.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'GET':
        token = request.args.get('token')
        return render_template('reset_password.html', token=token)
    
    try:
        token = request.form.get('token')
        new_password = request.form.get('password')
        
        if not token or not new_password:
            return jsonify({"error": "Token and new password are required"}), 400
            
        try:
            email = serializer.loads(token, salt='password-reset-salt', max_age=3600)
        except SignatureExpired:
            return jsonify({"error": "Reset link has expired"}), 400
        except:
            return jsonify({"error": "Invalid reset link"}), 400
            
        user = users_collection.find_one({"email": email})
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        # Update password
        users_collection.update_one(
            {"email": email},
            {"$set": {"password": generate_password_hash(new_password)}}
        )
        
        return jsonify({"message": "Password reset successfully"}), 200
        
    except Exception as e:
        print(f"Reset password error: {str(e)}")
        return jsonify({"error": "Failed to reset password"}), 500

@auth.route('/logout')
@login_required
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))
