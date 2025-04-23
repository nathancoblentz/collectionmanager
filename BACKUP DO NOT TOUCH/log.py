import sqlite3
from dataclasses import dataclass
from datetime import datetime
# from db import get_logged_in_user  # or wherever you store that function

def get_logged_in_user():
    # If there's no logged-in user, default to 'admin'
    logged_in_user = None  # Replace this with the actual logic to check the logged-in user
    return logged_in_user if logged_in_user else "admin"

@dataclass
class LogEntry:
    user: str
    message: str
    timestamp: str

    def __post_init__(self):
        self.timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Automatically set the timestamp

    def log_action(self):
        try:
            # Connect to the SQLite database
            conn = sqlite3.connect("collections.sqlite")
            cursor = conn.cursor()

            # Insert the log entry into the Log table
            cursor.execute("""
                INSERT INTO Log (User, Message, Timestamp)
                VALUES (?, ?, ?)
            """, (self.user, self.message, self.timestamp))
            
            conn.commit()  # Commit the transaction
            conn.close()  # Close the connection

            print(f"Logged action for user '{self.user}': {self.message}")

        except Exception as e:
            print(f"Error logging action: {e}")

# Function to create and log an action

import sqlite3

def log(message, user=None):
    # Use 'admin' as default if no user is logged in
    user = user or 'admin'
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        conn = sqlite3.connect("collections.sqlite")
        cursor = conn.cursor()

        # Insert log entry into the Log table
        cursor.execute("""
            INSERT INTO Log (User, Message, Timestamp) 
            VALUES (?, ?, ?)
        """, (user, message, timestamp))
        print(message) # also print to the console.

        conn.commit()
        conn.close()
        print(f"Action logged: {message}")
    except Exception as e:
        log(f"Error logging action: {e}")

# # Example usage
# log("User logged in", user="test_user")

# log("It's my first log entry!")