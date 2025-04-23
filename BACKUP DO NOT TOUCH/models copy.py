# %%
import sqlite3
from dataclasses import dataclass, field
from typing import Optional
from tkinter import messagebox
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

    def get_fields_and_values(self):
        # Exclude internal or irrelevant attributes
        excluded = ["table_name", "identifier_column"]
        fields = [key for key in vars(self) if key not in excluded]
        values = [getattr(self, key) for key in fields]
        return fields, values    

    def save(self):
        fields, values = self.get_fields_and_values()
        placeholders= ', '.join(['?'] * len(fields))
        sql = f"INSERT INTO {self.table_name} ({', '.join(fields)}) VALUES ({placeholders})"
        self.execute_query(sql, values)

    
        """Set Status to 'Active' based on identifier column."""
        conn = connect()
        cursor = conn.cursor()
        query = f"UPDATE {self.table_name} SET Status = 'Active' WHERE {self.identifier_column} = ?"
        cursor.execute(query, (getattr(self, self.identifier_column),))
        conn.commit()
        cursor.close()        
    
    def update_status(self, new_status: str):
        conn = connect()
        cursor = conn.cursor()
        try:
            query = f"UPDATE {self.table_name} SET Status = ? WHERE {self.identifier_column} = ?"
            cursor.execute(query, (new_status, getattr(self, self.identifier_column)))
            conn.commit()
            setattr(self, 'Status', new_status)  # Update the in-memory value
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()


    def update(self):
        fields, values = self.get_fields_and_values()
        set_clause = ', '.join([f"{f} = ?" for f in fields if f != self.identifier_column])
        update_values = [v for i, v in enumerate(values) if fields[i] != self.identifier_column]
        identifier_value = getattr(self, self.identifier_column)
        sql = f"UPDATE {self.table_name} SET {set_clause} WHERE {self.identifier_column} = ?"
        update_values.append(identifier_value)
        self.execute_query(sql, update_values)

    def delete(self):
        identifier_value = getattr(self, self.identifier_column)
        sql = f"DELETE FROM {self.table_name} WHERE {self.identifier_column} = ?"
        self.execute_query(sql, (identifier_value,))

    @staticmethod
    def execute_query(sql, params=None):
        conn=get_connection()
        cursor=conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        
        conn.commit()
        conn.close()

    @classmethod
    def get_by_identifier(cls, identifier_value: str):
        """Retrieve a single instance of the class by its identifier."""
        temp_instance = cls.__new__(cls)
        if hasattr(temp_instance, '__post_init__'):
            temp_instance.__post_init__()

        conn = connect()
        cursor = conn.cursor()

        query = f"SELECT * FROM {temp_instance.table_name} WHERE {temp_instance.identifier_column} = ?"
        cursor.execute(query, (identifier_value,))
        row = cursor.fetchone()
        cursor.close()

        if row:
            # Dynamically construct the object using column names and row values
            column_names = [desc[0] for desc in cursor.description]
            return cls(**dict(zip(column_names, row)))
        return None
    
    
    @classmethod
    def get_all(cls, **filters):
        print("Calling connect from get_all()")
        conn = connect()
        print("Get connection:", conn)
        cursor = conn.cursor()



        if filters:
            conditions = [f"{key} = ?" for key in filters]
            sql = f"SELECT * FROM {cls.table_name} WHERE {' AND '.join(conditions)}"
            values = tuple(filters.values())
        else:
            sql = f"SELECT * FROM {cls.table_name}"
            values = ()

        print(f"[DEBUG] SQL Query: {sql}")
        print(f"[DEBUG] Values: {values}")

        cursor.execute(sql, values)
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        return [cls(**row) for row in rows]
    

    @staticmethod
    def validate_and_convert_numeric(value, field_name):
        """Validate and convert a numeric field."""
        try:
            return float(value) if value else 0.0
        except ValueError:
            raise ValueError(f"{field_name} must be a valid number.")

    def show_item_details(self, item_identifier):
        try:
            # Retrieve the item using the base model's get_by_identifier method
            item = BaseModel.get_by_identifier(item_identifier)  # Make this generic for any model

            if not item:
                messagebox.showerror("Error", f"Item with identifier '{item_identifier}' not found.")
                return

            # Get fields and values for the item
            fields, values = item.get_fields_and_values()

            # Format the item details into a readable string
            item_details = "\n".join([f"{field}: {value}" for field, value in zip(fields, values)])

            # Display the item details in a messagebox
            messagebox.showinfo("Item Details", item_details)

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def to_display_string(self):
        """Return a string representation of the model for display."""
        fields, values = self.get_fields_and_values()
        return "\n".join(f"{field}: {value}" for field, value in zip(fields, values))

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
