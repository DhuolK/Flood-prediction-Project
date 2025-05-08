from flask import Flask, current_app, flash, render_template, request, session, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from pymongo import MongoClient
import joblib
import numpy as np
import pandas as pd
import requests
import datetime
import os
from flask_caching import Cache
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from login import auth  # Import the auth blueprint
from email_service import init_email_service, mail
from bson import ObjectId
from functools import wraps

# Load environment variables first
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here-1234567890')

# Initialize email service
init_email_service(app)

# Register the auth blueprint
app.register_blueprint(auth)

# Configure Flask-Caching
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 600})

# Load API key from .env
API_KEY = os.getenv("VISUAL_CROSSING_API_KEY", "your_actual_api_key_here")  # Replace with your actual API key

# Configure the scheduler
jobstores = {
    'default': MemoryJobStore()
}
executors = {
    'default': ThreadPoolExecutor(20)
}
job_defaults = {
    'coalesce': False,
    'max_instances': 3
}

scheduler = BackgroundScheduler(
    jobstores=jobstores,
    executors=executors,
    job_defaults=job_defaults,
    timezone='UTC'
)

# Load trained model and city encoder
model = joblib.load("flood_model.pkl")
city_encoder = joblib.load("city_encoder.pkl")

# Ensure API key is available and configure it in the app
if not API_KEY:
    print("Warning: VISUAL_CROSSING_API_KEY not found in environment variables!")
    API_KEY = "YOUR_API_KEY_HERE"  # Replace this with your actual API key if needed

app.config['WEATHER_API_KEY'] = API_KEY

# API URL for fetching weather data
WEATHER_URL = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{location}?unitGroup=metric&key={api_key}&contentType=json"

# MongoDB Connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/flood_db") 
client = MongoClient(MONGO_URI)
db = client["flood_db"]  # Database name
weather_collection = db["weather_data"]  # Collection for weather data
prediction_collection = db["flood_predictions"]  # Collection for storing predictions

def get_weather(city):
    """Fetch weather data from MongoDB first, then API if missing."""
    today = datetime.date.today().strftime("%Y-%m-%d")
    
    # Check if data is already in MongoDB
    existing_data = weather_collection.find_one({"city": city, "date": today})
    if existing_data:
        print(f"Using cached weather data for {city}")
        return existing_data["weather"]

    # Fetch from API
    url = WEATHER_URL.format(location=city, api_key=API_KEY)
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if "days" not in data or not data["days"]:
            return None

        current_data = data["days"][0]
        temperature = current_data.get("temp", 0)
        humidity = current_data.get("humidity", 0)
        rainfall = current_data.get("precip", current_data.get("precipitationSum", 0))

        weather_data = {"temperature": temperature, "humidity": humidity, "rainfall": rainfall}

        # Store in MongoDB for future requests
        weather_collection.insert_one({"city": city, "date": today, "weather": weather_data})

        return weather_data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None

def delete_old_data():
    """Automatically delete predictions older than 7 days."""
    days_to_keep = 7  # Change this value if needed
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_to_keep)

    # Delete records older than the cutoff date
    result = prediction_collection.delete_many({"date": {"$lt": cutoff_date.strftime("%Y-%m-%d %H:%M:%S")}})
    print(f"Deleted {result.deleted_count} old records (automated cleanup).")

# Add the delete_old_data job to the existing scheduler
scheduler.add_job(delete_old_data, 'interval', days=1)  # Run every 24 hours

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('auth.login_page'))  # Ensure correct route name
        return f(*args, **kwargs)
    return decorated_function

def admin_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print('admin_login_required called. Session:', dict(session))
        if not session.get('admin_logged_in'):
            print('Admin not logged in. Redirecting to admin_login.')
            return redirect(url_for('admin_login'))
        print('Admin is logged in. Proceeding to view.')
        return f(*args, **kwargs)
    return decorated_function

# Add after the imports:
class User(UserMixin):
    def __init__(self, username):
        self.id = username
        self.username = username

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

@app.route('/')
def home():
    user = session.get('user', {'name': 'Guest', 'email': 'Not logged in', 'initials': '?'})
    return render_template('home.html', user=user)

@app.route('/index', methods=['GET'])
@login_required
def index():
    if 'user' not in session:
        return redirect(url_for('auth.login_page'))
    user = session.get('user', {'name': 'Guest', 'email': 'Not logged in', 'initials': '?'})
    return render_template('index.html', user=user)

@app.route('/info', methods=['GET'])
def info():
    user = session.get('user', {'name': 'Guest', 'email': 'Not logged in', 'initials': '?'})
    return render_template('info.html', user=user)

@app.route('/predict', methods=['GET', 'POST'])
@login_required
def predict():
    if 'user' not in session:
        return redirect(url_for('auth.login_page'))
    user = session.get('user', {'name': 'Guest', 'email': 'Not logged in', 'initials': '?'})

    if request.method == 'GET':
        return render_template('index.html', user=user)
    
    if not API_KEY:
        flash('Weather API key is not configured. Please contact the administrator.', 'error')
        return redirect(url_for('index'))
    
    results = []
    cities = request.form.get('city', '').split(',')  # Get cities from the form input
    
    if not cities or all(not city.strip() for city in cities):
        flash('Please enter at least one city.', 'error')
        return redirect(url_for('index'))
    
    for city in cities:
        try:
            city = city.strip().title()
            if not city:
                continue
                
            weather_data = get_weather(city)
            
            if not weather_data:
                flash(f'Weather data not available for {city}. Please try again later.', 'warning')
                results.append({
                    "city": city,
                    "weather": "Weather data unavailable",
                    "prediction": "Error",
                    "temperature": 0,
                    "humidity": 0,
                    "rainfall": 0,
                    "risk_level": "Data Unavailable"
                })
                continue

            # Extract weather data with defaults
            temperature = weather_data.get("temperature", 0)
            humidity = weather_data.get("humidity", 0)
            rainfall = weather_data.get("rainfall", 0)

            # Encode city
            city_encoded = -1  # Default for unknown cities
            if city in map(str.title, city_encoder.classes_):
                city_encoded = city_encoder.transform([city])[0]
            else:
                flash(f'Warning: {city} is not in our training data. Prediction may be less accurate.', 'warning')

            # Prepare input features
            feature_names = ["Encoded City", "Temperature", "Humidity", "Rainfall"]
            input_data = pd.DataFrame([[city_encoded, temperature, humidity, rainfall]], 
                                    columns=feature_names)

            # Make prediction
            try:
                predicted_risk = model.predict(input_data)[0]
                risk_labels = {0: "Low Risk", 1: "Moderate Risk", 2: "High Risk"}
                risk_label = risk_labels.get(predicted_risk, "Unknown")
            except Exception as e:
                current_app.logger.error(f"Prediction error for {city}: {str(e)}")
                flash(f'Error making prediction for {city}. Please try again.', 'error')
                risk_label = "Prediction Error"

            # Prepare result for template
            result = {
                "city": city,
                "temperature": temperature,
                "humidity": humidity,
                "rainfall": rainfall,
                "risk_level": risk_label,
                "weather": f"Temp: {temperature}°C, Humidity: {humidity}%, Rainfall: {rainfall}mm",
                "prediction": risk_label
            }
            
            # Save to database
            prediction_record = {
                "city": city,
                "user_id": user.get('id'),
                "date": datetime.datetime.now(),
                "temperature": temperature,
                "humidity": humidity,
                "rainfall": rainfall,
                "predicted_risk": risk_label
            }
            
            try:
                prediction_collection.insert_one(prediction_record)
            except Exception as e:
                current_app.logger.error(f"Database error for {city}: {str(e)}")
                flash(f'Error saving prediction for {city}.', 'warning')

            results.append(result)

        except Exception as e:
            current_app.logger.error(f"Error processing {city}: {str(e)}")
            flash(f'Error processing {city}: {str(e)}', 'error')
            results.append({
                "city": city,
                "weather": "Processing error",
                "prediction": "Error",
                "temperature": 0,
                "humidity": 0,
                "rainfall": 0,
                "risk_level": "Error"
            })

    if not results:
        flash('No valid predictions could be made. Please try again.', 'error')
        return redirect(url_for('index'))

    # For chart display - assuming single city selection for chart
    chart_data = results[0] if results else None
    
    return render_template('result.html', 
                         results=results,
                         chart_data=chart_data,
                         user=user)

@app.route('/result', methods=['GET'])
def result():
    user = session.get('user', {'name': 'Guest', 'email': 'Not logged in', 'initials': '?'})
    return render_template('result.html', user=user)

@app.route('/history', methods=['GET'])
@login_required
def history():
    if 'user' not in session:
        return redirect(url_for('auth.login_page'))
    
    user = session.get('user', {'name': 'Guest', 'email': 'Not logged in', 'initials': '?'})
    city = request.args.get("city", "").strip().title()
    date = request.args.get("date", "").strip()

    # Build search query
    query = {}
    if city:
        query["city"] = city
    if date:
        query["date"] = {"$regex": f"^{date}"}  # Search for matching date prefix

    past_predictions = list(prediction_collection.find(query, {"_id": 0}))
    
    return render_template('history.html', predictions=past_predictions, user=user)

@app.route('/delete_old_data')
def manual_delete_old_data():
    """Manually delete predictions older than 7 days."""
    days_to_keep = 7
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_to_keep)

    result = prediction_collection.delete_many({"date": {"$lt": cutoff_date.strftime("%Y-%m-%d %H:%M:%S")}})
    
    return f"Deleted {result.deleted_count} old records."

API_KEY = os.getenv("VISUAL_CROSSING_API_KEY")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123") 

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            admin_user = User(username)
            login_user(admin_user)
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials', 'error')
    return render_template('admin_login.html')

@app.route('/admin/logout')
@admin_login_required
def admin_logout():
    session.pop('admin_logged_in', None)
    logout_user()
    return redirect(url_for('home'))

@app.route('/admin/dashboard')
@admin_login_required
def admin_dashboard():
    print('Accessing admin_dashboard route.')
    predictions = list(prediction_collection.find({}, {"_id": 0}).sort("date", -1))
    return render_template('admin_dashboard.html', predictions=predictions)

@app.route('/admin/delete_prediction/<date>', methods=['POST'])
@admin_login_required
def delete_prediction(date):
    try:
        result = prediction_collection.delete_many({"date": {"$regex": f"^{date}"}})
        flash(f'Successfully deleted {result.deleted_count} predictions', 'success')
    except Exception as e:
        flash(f'Error deleting predictions: {str(e)}', 'error')
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    try:
        if not scheduler.running:
            scheduler.start()
        app.run(debug=True, use_reloader=False)  # Disable reloader to prevent duplicate scheduler instances
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

