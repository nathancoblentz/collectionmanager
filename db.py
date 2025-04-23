# %%
#!/usr/bin/env python3

# Jonathan Coblentz, April 2025, CPT168-W18, Collections App
# Program:          databse module
# Associated file:  db.py
# Purpose:          This module stores functions for setting up the database connection and authenticating
#                   users to log into the app.

##### TABLE SCHEMAS #####

# CREATE TABLE "Collection" (
# 	"User"	TEXT NOT NULL,
# 	"CollectionName"	TEXT NOT NULL,
# 	"Status"	TEXT NOT NULL,
# 	FOREIGN KEY("User") REFERENCES ""
# )

# CREATE TABLE "Item" (
# 	"ItemID"	INTEGER NOT NULL,
# 	"Collection"	TEXT,
# 	"User"	TEXT,
# 	"ItemName"	TEXT NOT NULL UNIQUE,
# 	"Source"	TEXT,
# 	"Description"	TEXT,
# 	"PricePaid"	NUMERIC,
# 	"CurrentValue"	NUMERIC,
# 	"Location"	TEXT,
# 	"Notes"	TEXT,
# 	PRIMARY KEY("ItemID" AUTOINCREMENT),
# 	FOREIGN KEY("Collection") REFERENCES "Collection"("CollectionName"),
# 	FOREIGN KEY("Source") REFERENCES "Source"("BusinessName"),
# 	FOREIGN KEY("User") REFERENCES "User"("Username")
# )

# CREATE TABLE "Source" (
# 	"SourceID"	INTEGER,
# 	"BusinessName"	TEXT,
# 	"FirstName"	TEXT,
# 	"LastName"	TEXT,
# 	"Phone"	TEXT,
# 	"Address"	TEXT,
# 	"City"	TEXT,
# 	"State"	TEXT,
# 	"Zip"	TEXT,
# 	"Email"	TEXT,
#   "Status", TEXT,
# 	PRIMARY KEY("SourceID" AUTOINCREMENT)
# )

# CREATE TABLE "User" (
# 	"UserID"	INTEGER,
# 	"Username"	TEXT,
# 	"Password"	TEXT,
# 	"Role"	TEXT,
# 	"Status"	TEXT DEFAULT "Active",
# 	PRIMARY KEY("UserID" AUTOINCREMENT)
# )

import os
import sqlite3
from tkinter import messagebox

# Global variables

# tracks currently logged-in user
logged_in_user = None

# updated the logged_in_user tracker
def set_logged_in_user(username):
    global logged_in_user
    logged_in_user = username

# returns the logged_in_user
def get_logged_in_user():
    return logged_in_user


# initialize database connection variable
conn = None

DATABASE = "collections.sqlite"

def connect():
    global conn
    if conn is None:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        print("Connected to collections.sqlite")
    else:
        try:
            conn.execute("SELECT 1")  # Ping to test if connection is still valid
        except sqlite3.ProgrammingError:
            print("[DEBUG] Connection was closed. Reconnecting...")
            conn = sqlite3.connect(DATABASE)
            conn.row_factory = sqlite3.Row
            print("Reconnected to collections.sqlite")

    return conn




def get_cursor():  # return cursor object for SQL queries
    global conn
    if conn is None:
        conn = connect()
    return conn.cursor()


def close_db():
    global conn
    if conn:  # if connected, close the connection
        conn.close()
        print("Disconnected from database")
        conn = None  # reset the global conn variable

# validate a username and password input; returns a boolean value

# Login database connection function
def login(username, password):
    conn = connect()
    cursor = conn.cursor()
    query = "SELECT * FROM User WHERE Username = ? AND Password = ?"
    cursor.execute(query, (username, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        set_logged_in_user(user)  # Store globally for later access
        return True
    return False



# def login(username: str, password: str) -> bool:
#     global logged_in_user  # check to see who is trying to log in

#     conn = connect()
#     print(f"[DEBUG] Connection object: {conn}")
#     if conn is None:
#         raise Exception("Failed to connect to the database.")

#     with conn:
#         cursor = conn.cursor()

#         # Query the database to fetch the user record by username and password
#         cursor.execute(
#             "SELECT * FROM User WHERE Username=? AND Password=?", (username, password))
#         user = cursor.fetchone()

#         if user:  # if a matching record is found, validate the login and return True
#             # Unpack all columns (adjust this if necessary)
#             user_id, stored_username, stored_password, role, status = user

#             if stored_username == username and stored_password == password:
#                 if status == "Inactive":  # verify that the user profile is active.
#                     print(
#                         f"User '{stored_username}' has been deactivated. Please contact your system administrator.")
#                     return False
#                 logged_in_user = stored_username
#                 print(f"User '{logged_in_user}' logged in successfully!")
#                 return True
#             else:
#                 print("Invalid username or password!")
#                 return False
#         else:  # no matching user found
#             print("Invalid username or password!")
#             return False





def logout():
    global logged_in_user
    if logged_in_user:  # if someone is logged in, log them out.
        print(f"User '{logged_in_user}' logged out successfully!")
        logged_in_user = None


# LOGGED IN USER UTILITIES

# return a boolean for whether or not logged in user has an Admin role
def is_admin() -> bool:
    return logged_in_user == "admin"

# check whether a user is active
def get_user_status(username):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT Status FROM User WHERE Username = ?", (username,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row["Status"] if row else None


# OLD TEST FUNCTIONS 
# def check_user():
#     conn = connect()
#     print(f"[DEBUG] Connection object: {conn}")
#     if conn is None:
#         raise Exception("Failed to connect to the database.")

#     with conn:
#         cursor = conn.cursor()

#         # Print all users to make sure "admin" is in the table
#         cursor.execute("SELECT * FROM User;")
#         users = cursor.fetchall()  # Fetch all rows
#         print("Users in database:", users)

#         # Now, debug the exact query and compare entered vs stored values
#         entered_username = 'admin'
#         entered_password = 'admin'
#         cursor.execute(
#             "SELECT Username, Password FROM User WHERE Username=? COLLATE NOCASE", (entered_username,))
#         user = cursor.fetchone()

#         if user:
#             stored_username, stored_password = user
#             print(f"Stored Username: {stored_username}")
#             print(f"Stored Password: {stored_password}")
#             print(f"Entered Username: {entered_username}")
#             print(f"Entered Password: {entered_password}")

#             # Check if stored password matches entered password
#             if stored_password.strip() == entered_password.strip():
#                 print("Login successful!")
#             else:
#                 print("Password mismatch!")
#         else:
#             print("User not found!")


# def check_connection():
#     db_path = os.path.abspath("collections.sqlite")
#     print(f"Connecting to database at: {db_path}")

#     conn = connect()
#     print(f"[DEBUG] Connection object: {conn}")
#     if conn is None:
#         raise Exception("Failed to connect to the database.")

#     with conn:
#         cursor = conn.cursor()

#         # Print all users to verify the admin user exists
#         cursor.execute("SELECT * FROM User;")
#         users = cursor.fetchall()
#         print("Users in database:", users)


# check_connection()
