from pymongo import MongoClient
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/flood_db")
client = MongoClient(MONGO_URI)
db = client["flood_db"]
users_collection = db["users"]

def cleanup_duplicates():
    # Get all unique emails
    unique_emails = users_collection.distinct("email")
    total_removed = 0
    
    for email in unique_emails:
        # Get all users with this email, sorted by creation date (newest first)
        users = list(users_collection.find({"email": email}).sort("created_at", -1))
        
        if len(users) > 1:
            print(f"\nFound {len(users)} duplicates for email: {email}")
            # Keep the newest one, remove the rest
            newest_user = users[0]
            duplicate_ids = [user["_id"] for user in users[1:]]
            
            result = users_collection.delete_many({"_id": {"$in": duplicate_ids}})
            total_removed += result.deleted_count
            print(f"Kept user: {newest_user.get('name')} (created: {newest_user.get('created_at')})")
            print(f"Removed {result.deleted_count} duplicate entries")
    
    print(f"\nTotal duplicates removed: {total_removed}")
    
    # Create unique index on email field to prevent future duplicates
    users_collection.create_index("email", unique=True)
    print("Created unique index on email field to prevent future duplicates")

if __name__ == "__main__":
    cleanup_duplicates() 