# %%
import sqlite3
from dataclasses import dataclass, field
from typing import Optional
from tkinter import messagebox
from log import log
from db import connect, login  # Ensure the login function from db.py is imported


# models/
# │
# ├── BaseModel      ← Optional for reuse (save/delete structure)
    # BaseModel methods:
    # save - inserts a new record into the sqlite database
    # deactivate - changes a record's status to "Inactive"
    # reactivate - changes a record's status to "Active"
    # update - updates a record
    # delete - deletes a record from the database (not recommended)
    # execute query - helper function for executing an SQL query
    # get_by_identifier - selects a record by its identifier (Username BusinessName, CollectionName, ItemName, )
    # get_all - selects every record by the identifier; used for dropdown selection menus
    # validate_and_convert_numeric - converts to an int or a float

# objects
# ├── User           ← Stores users registered for the application
# ├── Item           ← Name, Category, CollectionName, User | with CRUD
# ├── Source         ← BusinessName, PhoneNumber, Email, User | with CRUD
# └── Collection     ← CollectionName, User | with CRUD
    # custom method - status_toggle - deactivates every active item in a collection, or activates every inactive item in a collection



#     Each model should manage its own persistence logic.


DATABASE = "collections.sqlite"


def get_connection():
    return sqlite3.connect(DATABASE)

##### BASE MODEL #####



@dataclass
class BaseModel:
    table_name: str
    identifier_column: str

    @classmethod
    def get_by_values(cls, values_dict):
        conn = connect()
        cursor = conn.cursor()
        conditions = " AND ".join([f"{key} = ?" for key in values_dict])
        query = f"SELECT * FROM {cls.__name__} WHERE {conditions}"
        cursor.execute(query, tuple(values_dict.values()))
        row = cursor.fetchone()
        cursor.close()

    def get_fields_and_values(self):
        excluded = ["table_name", "identifier_column"]
        fields = [k for k in vars(self) if k not in excluded]
        values = [getattr(self, k) for k in fields]
        return fields, values

    def save(self):
        # Check if the record already exists
        # existing = self.get_by_identifier(getattr(self, self.identifier_column))
        # if existing:
        #     print(f"{self.table_name} record already exists with {self.identifier_column} = {getattr(self, self.identifier_column)}. Skipping insert.")
        #     return  # Or raise an exception, or update instead

        # Insert new record
        fields, values = self.get_fields_and_values()
        placeholders = ', '.join('?' for _ in fields)
        sql = f"INSERT INTO {self.table_name} ({', '.join(fields)}) VALUES ({placeholders})"
        self.execute_query(sql, values)

        # Optionally set status to Active
        self.update_status("Active")

    def update(self):
        fields, values = self.get_fields_and_values()
        update_fields = [f"{f} = ?" for f in fields if f != self.identifier_column]
        update_values = [getattr(self, f) for f in fields if f != self.identifier_column]
        update_values.append(getattr(self, self.identifier_column))

        sql = f"UPDATE {self.table_name} SET {', '.join(update_fields)} WHERE {self.identifier_column} = ?"
        self.execute_query(sql, update_values)

    def delete(self):
        sql = f"DELETE FROM {self.table_name} WHERE {self.identifier_column} = ?"
        self.execute_query(sql, (getattr(self, self.identifier_column),))

    def update_status(self, new_status):
        sql = f"UPDATE {self.table_name} SET Status = ? WHERE {self.identifier_column} = ?"
        self.execute_query(sql, (new_status, getattr(self, self.identifier_column)))
        setattr(self, "Status", new_status)

    @staticmethod
    def execute_query(query, params=()):
        with sqlite3.connect("collections.sqlite") as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()

    @classmethod
    def get_by_identifier(cls, identifier_value):
        temp_instance = cls.__new__(cls)
        if hasattr(temp_instance, '__post_init__'):
            temp_instance.__post_init__()

        conn = connect()
        cursor = conn.cursor()

        query = f"SELECT * FROM {temp_instance.table_name} WHERE {temp_instance.identifier_column} = ?"
        cursor.execute(query, (identifier_value,))
        row = cursor.fetchone()
        columns = [desc[0] for desc in cursor.description] if row else []
        cursor.close()
        conn.close()

        return cls(**dict(zip(columns, row))) if row else None

    @classmethod
    def get_by_values(cls, values_dict):
        temp = cls.__new__(cls)
        if hasattr(temp, '__post_init__'):
            temp.__post_init__()

        conn = connect()
        cursor = conn.cursor()
        conditions = " AND ".join(f"{k} = ?" for k in values_dict)
        sql = f"SELECT * FROM {temp.table_name} WHERE {conditions}"
        cursor.execute(sql, tuple(values_dict.values()))
        row = cursor.fetchone()
        columns = [desc[0] for desc in cursor.description] if row else []
        cursor.close()
        conn.close()

        return cls(**dict(zip(columns, row))) if row else None

    @classmethod
    def get_all(cls, **filters):
        conn = connect()
        cursor = conn.cursor()

        if filters:
            condition = " AND ".join(f"{k} = ?" for k in filters)
            sql = f"SELECT * FROM {cls.table_name} WHERE {condition}"
            cursor.execute(sql, tuple(filters.values()))
        else:
            sql = f"SELECT * FROM {cls.table_name}"
            cursor.execute(sql)

        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        cursor.close()
        conn.close()

        return [cls(**dict(zip(columns, row))) for row in rows]

    @staticmethod
    def validate_and_convert_numeric(value, field_name):
        try:
            return float(value) if value else 0.0
        except ValueError:
            raise ValueError(f"{field_name} must be a valid number.")

    def show_item_details(self, item_identifier):
        item = self.get_by_identifier(item_identifier)
        if not item:
            messagebox.showerror("Error", f"Item with identifier '{item_identifier}' not found.")
            return

        fields, values = item.get_fields_and_values()
        details = "\n".join(f"{f}: {v}" for f, v in zip(fields, values))
        messagebox.showinfo("Item Details", details)

    def to_display_string(self):
        fields, values = self.get_fields_and_values()
        return "\n".join(f"{f}: {v}" for f, v in zip(fields, values))

###### USER #####


@dataclass
class User(BaseModel):
    Username: str
    Password: str
    Role: str
    Status: str = "Active"
    UserID: Optional[int] = field(default=None, repr=False)

    table_name:        str = field(init=False, repr=False, default="User")
    identifier_column: str = field(init=False, default="Username")



    # def get_fields_and_values(self):
    #     fields = ['Username', 'Password', 'Role', 'Status']
    #     values = [self.Username, self.Password, self.Role, self.Status]
    #     return fields, values

    # def save(self):
    #     conn = get_connection()
    #     cursor = conn.cursor()
    #     cursor.execute("""
    #         INSERT INTO User (Username, Password, Role)
    #         VALUES (?, ?, ?)""",
    #                    (self.Username, self.Password, self.Role))
    #     conn.commit()
    #     conn.close()

    # def deactivate(self):
        


@dataclass
class Item(BaseModel):
    Collection: str
    User: str
    ItemName: str
    Source: str

    Status: str = field(default="Active", init=True)

    Description: Optional[str] = field(default=None, init=True, repr=False)
    PricePaid: Optional[float] = field(default=None, init=True, repr=False)
    CurrentValue: Optional[float] = field(default=None, init=True, repr=False)
    Location: Optional[str] = field(default=None, init=True, repr=False)
    Notes: Optional[str] = field(default=None, init=True, repr=False)
    ItemID: Optional[int] = field(default=None, init=True, repr=False)

    table_name: str = field(init=False, default="Item")
    identifier_column: str = field(init=False, default="ItemID")

    def get_fields_and_values(self):
        """Return fields and their values for database operations."""
        fields = ["Collection", "User", "ItemName", "Source", "Status", "Description", "PricePaid", "CurrentValue", "Location", "Notes"]
        values = [self.Collection, self.User, self.ItemName, self.Source, self.Status, self.Description, self.PricePaid, self.CurrentValue, self.Location, self.Notes]
        return fields, values

###### SOURCE #####


@dataclass
class Source(BaseModel):
    BusinessName: str
    FirstName: str
    Phone: str
    Email: str

    Status: str = field(default="Active", init=True)

    LastName: Optional[str] = field(default="", init=True, repr=False)
    City: Optional[str] = field(default="", init=True, repr=False)
    Address: Optional[str] = field(default="", init=True, repr=False)
    State: Optional[str] = field(default="", init=True, repr=False)
    Zip: Optional[str] = field(default="", init=True, repr=False)
    SourceID: Optional[int] = field(init=True, default=None)  # Allow initialization

    table_name: str = field(init=False, default="Source")
    identifier_column: str = field(init=False, default="BusinessName")

    @classmethod
    def get_by_name(cls, business_name):
        conn = connect()
        cursor = conn.cursor()
        sql = f"SELECT * FROM {cls.table_name} WHERE BusinessName = ?"
        cursor.execute(sql, (business_name,))
        row = cursor.fetchone()
        conn.close()
        if row:
            columns = [column[0] for column in cursor.description]
            return cls(**dict(zip(columns, row)))
        return None

    


###### COLLECTION #####


@dataclass
class Collection(BaseModel):

    User: str
    CollectionName: str    
    Status: str = field(default="Active", init=True)

    table_name: str = field(init=False, default="Collection")
    identifier_column: str = field(init=False, default="CollectionName")

    def update_all_items_status(self, new_status: str):
        """Update the status of all items in this collection."""
        conn = connect()
        cursor = conn.cursor()
        try:
            query = "UPDATE Item SET Status = ? WHERE Collection = ?"
            cursor.execute(query, (new_status, self.CollectionName))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

# %%
