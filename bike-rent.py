from tkinter import *
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
import sqlite3

root = Tk()
root.title("Bike Rental App")
root.geometry("500x500")

conn = sqlite3.connect("bike-rental.db")
cursor = conn.cursor()

cursor.execute(
    """CREATE TABLE IF NOT EXISTS Users (
                    username TEXT PRIMARY KEY, 
                    password TEXT NOT NULL,
                    role TEXT NOT NULL
                    )"""
)

cursor.execute(
    """CREATE TABLE IF NOT EXISTS Bikes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    type TEXT,
                    price_per_hour INTEGER,
                    available TEXT)"""
)

cursor.execute(
    """CREATE TABLE IF NOT EXISTS Rentals (
                    bike_id INTEGER,
                    customer_name TEXT,
                    hours INTEGER,
                    total_cost REAL
                )"""
)

conn.commit()

# Global Variables
bikes = []
rentals = []


def load_bikes_from_db():
    global bikes, rentals
    cursor.execute("SELECT id, name, type, price_per_hour, available FROM bikes")
    for row in cursor.fetchall():
        bike = {
            "id": row[0],
            "name": row[1],
            "type": row[2],
            "price_per_hour": row[3],
            "available": bool(int(row[4])),
        }
        bikes.append(bike)

        # If bike is not available, add it to rentals
        # if not bike["available"]:
        #     rentals.append(bike)

    cursor.execute("SELECT bike_id, customer_name, hours, total_cost FROM Rentals")
    for row in cursor.fetchall():
        rentals.append(
            {
                "bike_id": row[0],
                "customer_name": row[1],
                "hours": row[2],
                "total_cost": row[3],
            }
        )


load_bikes_from_db()


def update_bike_list(bike_tree):
    for row in bike_tree.get_children():
        bike_tree.delete(row)

    # Create a style for available and rented bikes
    style = ttk.Style()

    # Apply foreground colors using map (works better than tag_configure)
    style.map("Treeview", foreground=[("selected", "white")])
    style.map("Treeview", background=[("selected", "#0078D7")])  # Blue when selected

    for bike in bikes:
        status = "Available" if bike["available"] else "Rented"
        tag = "available" if bike["available"] else "rented"

        bike_tree.insert(
            "",
            "end",
            values=(
                bike["id"],
                bike["name"],
                bike["type"],
                f"${bike['price_per_hour']}/hour",
                status,
            ),
            tags=(tag,),
        )

    # Set tag-specific foreground colors
    bike_tree.tag_configure(
        "available", foreground="#0F5F07", background="#D2FBD0"
    )  # Green for Available
    bike_tree.tag_configure(
        "rented", foreground="#5F071D", background="#FBD0DA"
    )  # Red for Rented


def clear_rent_form(bike_id_entry, customer_name_entry, rental_hours_entry):
    bike_id_entry.delete(0, END)
    customer_name_entry.delete(0, END)
    rental_hours_entry.delete(0, END)


def clear_return_form(return_bike_id_entry):
    return_bike_id_entry.delete(0, END)


def show_rentals(root):
    if not hasattr(root, "rental_table_frame"):
        root.rental_table_frame = LabelFrame(
            root,
            text="Rental List",
            font=("Helvetica", 12, "bold"),
            bg="#f0f0f0",
            padx=10,
            pady=10,
        )
        root.rental_table_frame.pack(fill="x", padx=20, pady=5)

        columns = ("Bike ID", "Customer Name", "Rental Hours", "Total Cost")
        root.rental_tree = ttk.Treeview(
            root.rental_table_frame, columns=columns, show="headings"
        )

        for col in columns:
            root.rental_tree.heading(col, text=col)
            root.rental_tree.column(col, width=100)

        root.rental_tree.pack()


def update_rental_list(root):
    for row in root.rental_tree.get_children():
        root.rental_tree.delete(row)

    for rental in rentals:
        root.rental_tree.insert(
            "",
            "end",
            values=(
                rental["bike_id"],
                rental["customer_name"],
                rental["hours"],
                f"${rental['total_cost']}",
            ),
        )


def rent_bike(bike_id_entry, customer_name_entry, rental_hours_entry, bike_tree, root):
    # Remove from rentals list in memory
    global rentals, bikes
    bike_id_text = bike_id_entry.get().strip()
    rental_hours_text = rental_hours_entry.get().strip()

    if not bike_id_text.isdigit() or not rental_hours_text.isdigit():
        messagebox.showerror(
            "Input Error",
            "Please enter valid numeric values for Bike ID and Rental Hours.",
        )
        return

    bike_id = int(bike_id_text)
    customer_name = customer_name_entry.get().strip()
    hours = int(rental_hours_text)

    if not customer_name:
        messagebox.showerror("Input Error", "Customer Name cannot be empty.")
        return

    # Check if the bike is available
    cursor.execute(
        "SELECT name, price_per_hour, available FROM bikes WHERE id = ?", (bike_id,)
    )
    bike = cursor.fetchone()

    if bike and int(bike[2]) == 1:
        total_cost = bike[1] * hours
        rentals.append(
            {
                "bike_id": bike_id,
                "customer_name": customer_name,
                "hours": hours,
                "total_cost": total_cost,
            }
        )
        # Insert rental record into rentals table
        cursor.execute(
            "INSERT INTO rentals (bike_id, customer_name, hours, total_cost) VALUES (?, ?, ?, ?)",
            (bike_id, customer_name, hours, total_cost),
        )

        # Update bike availability
        cursor.execute("UPDATE Bikes SET available = 0 WHERE id = ?", (bike_id,))

        conn.commit()  # Commit changes, but DO NOT close the connection

        clear_rent_form(bike_id_entry, customer_name_entry, rental_hours_entry)

        # Reload bikes from database and update UI
        bikes = []
        rentals = []
        load_bikes_from_db()  # Fetch updated bike list
        update_bike_list(bike_tree)  # Refresh UI
        show_rentals(root)
        update_rental_list(root)

        messagebox.showinfo(
            "Success",
            f"{customer_name} rented {bike[0]} for {hours} hours.\nTotal Cost: ${total_cost}",
        )
    else:
        conn.close()
        messagebox.showerror("Error", "Bike not available or invalid ID.")


def return_bike_func(return_bike_id_entry, bike_tree, root):
    bike_id_text = return_bike_id_entry.get().strip()

    if not bike_id_text.isdigit():
        messagebox.showerror("Input Error", "Please enter a valid numeric Bike ID.")
        return

    bike_id = int(bike_id_text)

    # Check if the bike exists and is currently rented
    cursor.execute("SELECT name, available FROM Bikes WHERE id = ?", (bike_id,))
    bike = cursor.fetchone()

    if not bike:
        messagebox.showerror("Error", "Bike ID not found.")
        return

    if int(bike[1]) == 1:
        messagebox.showerror("Error", "Bike is already available.")
        return

    # Remove the rental record
    cursor.execute("DELETE FROM Rentals WHERE bike_id = ?", (bike_id,))

    # Mark the bike as available
    cursor.execute("UPDATE Bikes SET available = 1 WHERE id = ?", (bike_id,))

    conn.commit()  # Save changes

    # Remove from rentals list in memory
    global rentals, bikes

    # Reload bikes from database and update UI
    bikes = []
    rentals = []
    load_bikes_from_db()  # Fetch updated bike list
    update_bike_list(bike_tree)  # Refresh UI
    update_rental_list(root)

    clear_return_form(return_bike_id_entry)

    messagebox.showinfo("Success", f"Bike '{bike[0]}' returned successfully.")


def add_bike(bike_name_entry, bike_type_entry, price_entry, bike_tree):
    name = bike_name_entry.get().strip()
    bike_type = bike_type_entry.get().strip()
    price_text = price_entry.get().strip()

    if not name or not bike_type or not price_text.isdigit():
        messagebox.showerror("Input Error", "Please enter valid bike details.")
        return

    price = int(price_text)

    # Insert data into the database
    cursor.execute(
        "INSERT INTO Bikes (name, type, price_per_hour, available) VALUES (?, ?, ?, 1)",
        (name, bike_type, price),
    )
    conn.commit()

    messagebox.showinfo("Success", "Bike added successfully!")

    # Clear input fields after adding a bike
    bike_name_entry.delete(0, END)
    bike_type_entry.delete(0, END)
    price_entry.delete(0, END)

    # Reload bikes from database and update UI
    load_bikes_from_db()  # Fetch updated bike list
    update_bike_list(bike_tree)  # Refresh UI


def delete_bike(bike_id_entry, bike_tree):
    try:
        bike_id = bike_id_entry.get().strip()

        if not bike_id.isdigit():
            messagebox.showerror("Error", "Please enter a valid numeric Bike ID.")
            return

        bike_id = int(bike_id)

        # Verify if the bike exists before deleting
        cursor.execute("SELECT * FROM bikes WHERE id = ?", (bike_id,))
        bike = cursor.fetchone()

        if bike is None:
            messagebox.showerror("Error", "Bike ID not found.")
            return

        # Confirm before deleting
        confirm = messagebox.askyesno(
            "Confirm Deletion", f"Are you sure you want to delete bike ID {bike_id}?"
        )
        if not confirm:
            return

        # Delete bike
        cursor.execute("DELETE FROM bikes WHERE id = ?", (bike_id,))
        conn.commit()

        messagebox.showinfo("Success", "Bike deleted successfully.")

        # Reload bikes from database and update UI
        load_bikes_from_db()  # Fetch updated bike list
        update_bike_list(bike_tree)  # Refresh UI

        # Clear input field after deleting a bike
        bike_id_entry.delete(0, END)

    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {str(e)}")


def createAdminPage():
    admin_root = Toplevel()
    admin_root.title("Admin Panel")
    admin_root.geometry("600x650")

    # Title Label
    title_label = Label(
        admin_root,
        text="🚴‍♂️ Admin || Bike Rental Management System",
        font=("Helvetica", 16, "bold"),
        bg="#f0f0f0",
        fg="#333333",
    )
    title_label.pack(pady=10)

    # Bike List Treeview
    bike_tree = ttk.Treeview(
        admin_root,
        columns=("ID", "Name", "Type", "Price", "Status"),
        show="headings",
        height=8,
    )
    bike_tree.heading("ID", text="ID")
    bike_tree.heading("Name", text="Name")
    bike_tree.heading("Type", text="Type")
    bike_tree.heading("Price", text="Price")
    bike_tree.heading("Status", text="Status")
    bike_tree.column("ID", width=50, anchor="center")
    bike_tree.column("Name", width=150, anchor="center")
    bike_tree.column("Type", width=100, anchor="center")
    bike_tree.column("Price", width=100, anchor="center")
    bike_tree.column("Status", width=100, anchor="center")
    bike_tree.pack(pady=10)

    # Initialize Bike List
    update_bike_list(bike_tree)

    # Rent Bike Section
    input_frame = LabelFrame(
        admin_root, text="Add a Bike for rent", bg="#f0f0f0", padx=10, pady=10
    )
    input_frame.pack(fill="x", padx=20, pady=5)

    Label(input_frame, text="Bike Name:").grid(row=0, column=0, padx=10, pady=5)
    bike_name_entryy = Entry(input_frame)
    bike_name_entryy.grid(row=0, column=1, padx=10, pady=5)

    Label(input_frame, text="Bike Type:").grid(row=1, column=0, padx=10, pady=5)
    bike_type_entry = Entry(input_frame)
    bike_type_entry.grid(row=1, column=1, padx=10, pady=5)

    Label(input_frame, text="Price per Hour:").grid(row=2, column=0, padx=10, pady=5)
    price_entry = Entry(input_frame)
    price_entry.grid(row=2, column=1, padx=10, pady=5)

    # Add Bike Button
    add_bike_button = Button(
        input_frame,
        text="Add Bike",
        font=("Helvetica", 12, "bold"),
        bg="#4CAF50",
        fg="white",
        command=lambda: add_bike(
            bike_name_entryy, bike_type_entry, price_entry, bike_tree
        ),
    )
    add_bike_button.grid(row=3, column=0, columnspan=2, pady=10)

    # Delete Bike Section
    delete_frame = LabelFrame(
        admin_root, text="Delete a Bike for rent", bg="#f0f0f0", padx=10, pady=10
    )
    delete_frame.pack(fill="x", padx=20, pady=5)

    Label(delete_frame, text="Bike ID:").grid(row=0, column=0, padx=10, pady=5)
    bike_name_entry = Entry(delete_frame)
    bike_name_entry.grid(row=0, column=1, padx=10, pady=5)

    # Add Bike Button
    add_bike_button = Button(
        delete_frame,
        text="Delete Bike",
        font=("Helvetica", 12, "bold"),
        fg="#5F071D",
        bg="#FBD0DA",
        command=lambda: delete_bike(bike_name_entry, bike_tree),
    )
    add_bike_button.grid(row=3, column=0, columnspan=2, pady=10)


def loginPage():
    username = userEntry.get().strip()
    password = userPassword.get().strip()

    if not username or not password:
        messagebox.showerror("Login Error", "Username and Password cannot be empty!")
    else:
        cursor.execute(
            "SELECT username, role FROM Users WHERE username=? AND password=?",
            (username, password),
        )
        user = cursor.fetchone()

        if user:
            username, role = user
            if role == "admin":
                messagebox.showinfo("Login Success", "Welcome to Admin Dashboard!")
                createAdminPage()
            else:
                messagebox.showinfo("Login Success", "Welcome to Bike Rental!")
                createHomePage()
        else:
            messagebox.showerror("Login Error", "Invalid username or password!")


def createHomePage():
    root = Toplevel()
    root.title("Bike Rental Management System")
    root.geometry("800x500")
    root.configure(bg="#f0f0f0")

    # Custom Fonts
    title_font = ("Helvetica", 16, "bold")
    label_font = ("Helvetica", 12)
    button_font = ("Helvetica", 12, "bold")

    # Title Label
    title_label = Label(
        root,
        text="🚴‍♂️ Bike Rental Management System",
        font=title_font,
        bg="#f0f0f0",
        fg="#333333",
    )
    title_label.pack(pady=10)

    # Bike List Treeview
    bike_tree = ttk.Treeview(
        root,
        columns=("ID", "Name", "Type", "Price", "Status"),
        show="headings",
        height=8,
    )
    bike_tree.heading("ID", text="ID")
    bike_tree.heading("Name", text="Name")
    bike_tree.heading("Type", text="Type")
    bike_tree.heading("Price", text="Price")
    bike_tree.heading("Status", text="Status")
    bike_tree.column("ID", width=50, anchor="center")
    bike_tree.column("Name", width=150, anchor="center")
    bike_tree.column("Type", width=100, anchor="center")
    bike_tree.column("Price", width=100, anchor="center")
    bike_tree.column("Status", width=100, anchor="center")
    bike_tree.pack(pady=10)

    # Initialize Bike List
    update_bike_list(bike_tree)

    # Rent Bike Section
    rent_frame = LabelFrame(
        root, text="Rent a Bike", font=label_font, bg="#f0f0f0", padx=10, pady=10
    )
    rent_frame.pack(pady=10)  # Use pack() instead of grid()

    Label(rent_frame, text="Bike ID:", font=label_font, bg="#f0f0f0").grid(
        row=0, column=0, padx=5, pady=5
    )
    bike_id_entry = Entry(rent_frame, font=label_font)
    bike_id_entry.grid(row=0, column=1, padx=5, pady=5)

    Label(rent_frame, text="Customer Name:", font=label_font, bg="#f0f0f0").grid(
        row=1, column=0, padx=5, pady=5
    )
    customer_name_entry = Entry(rent_frame, font=label_font)
    customer_name_entry.grid(row=1, column=1, padx=5, pady=5)

    Label(rent_frame, text="Rental Hours:", font=label_font, bg="#f0f0f0").grid(
        row=2, column=0, padx=5, pady=5
    )
    rental_hours_entry = Entry(rent_frame, font=label_font)
    rental_hours_entry.grid(row=2, column=1, padx=5, pady=5)

    rent_button = Button(
        rent_frame,
        text="Rent Bike",
        font=button_font,
        bg="#4CAF50",
        fg="white",
        command=lambda: rent_bike(
            bike_id_entry, customer_name_entry, rental_hours_entry, bike_tree, root
        ),
    )
    rent_button.grid(row=3, column=0, columnspan=2, pady=10)

    # Return Bike Section
    return_bike = LabelFrame(
        root, text="Return a Bike", font=label_font, bg="#f0f0f0", padx=10, pady=10
    )
    return_bike.pack(pady=10)  # Use pack() instead of grid()

    Label(return_bike, text="Bike ID:", font=label_font, bg="#f0f0f0").grid(
        row=0, column=0, padx=5, pady=5
    )
    return_bike_id_entry = Entry(return_bike, font=label_font)
    return_bike_id_entry.grid(row=0, column=1, padx=5, pady=5)

    return_button = Button(
        return_bike,
        text="Return a Bike",
        font=button_font,
        bg="#4CAF50",
        fg="white",
        command=lambda: return_bike_func(return_bike_id_entry, bike_tree, root),
    )
    return_button.grid(row=1, column=0, columnspan=2, pady=10)

    show_rentals(root)
    update_rental_list(root)


def viewDetails(bike):
    detailsPage = Toplevel()
    detailsPage.title(f"{bike[1]} Details")
    detailsPage.geometry("400x400")

    bike_img = Image.open(bike[2])
    bike_img = bike_img.resize((200, 200))
    bike_img = ImageTk.PhotoImage(bike_img)

    Label(detailsPage, image=bike_img).pack(pady=10)
    Label(detailsPage, text=f"Name: {bike[1]}", font=("Arial", 14)).pack()
    Label(detailsPage, text=f"Price: ${bike[3]}", font=("Arial", 14)).pack()
    Label(detailsPage, text=f"Status: {bike[4]}", font=("Arial", 14)).pack()
    detailsPage.mainloop()


def bookBike(bike):
    if bike[4] == "Booked":
        messagebox.showerror("Booking Error", "This bike is already booked!")
    else:
        cursor.execute("UPDATE Bikes SET status='Booked' WHERE id=?", (bike[0],))
        conn.commit()
        messagebox.showinfo("Success", "Bike booked successfully!")


def signUp():
    signUpPage = Toplevel()
    signUpPage.title("Sign Up Page")
    signUpPage.geometry("400x250")

    Label(signUpPage, text="Username", font=("Arial", 10, "bold")).pack()
    usernameEntry = Entry(signUpPage, width=30, font=("Arial", 10))
    usernameEntry.pack()

    Label(signUpPage, text="Password", font=("Arial", 10, "bold")).pack()
    passwordEntry = Entry(signUpPage, width=30, font=("Arial", 10), show="*")
    passwordEntry.pack()

    admin_var = IntVar()
    admin_checkbox = Checkbutton(
        signUpPage, text="Are you Admin?", variable=admin_var, font=("Helvetica", 10)
    )
    admin_checkbox.pack(pady=5)

    def submitData():
        username = usernameEntry.get().strip()
        password = passwordEntry.get().strip()
        is_admin = admin_var.get()

        if len(username) < 4:
            messagebox.showerror(
                "Error", "Username must be at least 4 characters long!"
            )
            return

        cursor.execute("SELECT username FROM Users WHERE username=?", (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            messagebox.showerror(
                "Error", "Username already exists! Choose a different one."
            )
            return

        cursor.execute(
            "INSERT INTO Users (username, password, role) VALUES (?, ?, ?)",
            (username, password, "admin" if is_admin else "user"),
        )
        conn.commit()
        messagebox.showinfo("Success", "Account Created Successfully!")
        signUpPage.destroy()

    Button(signUpPage, text="Sign Up", bg="green", fg="white", command=submitData).pack(
        pady=10
    )


welcome = Label(root, text="Welcome", font=("Arial", 24, "bold"), fg="blue")
welcome.pack()

loginFrame = LabelFrame(
    root, text="Login", padx=25, pady=25, fg="blue", font=("Arial", 14, "bold")
)
loginFrame.pack()

Label(loginFrame, text="Username", font=("Arial", 10, "bold")).pack()
userEntry = Entry(loginFrame, width=30, font=("Arial", 10))
userEntry.pack()

Label(loginFrame, text="Password", font=("Arial", 10, "bold")).pack()
userPassword = Entry(loginFrame, show="*", width=30, font=("Arial", 10))
userPassword.pack()

Button(loginFrame, text="Login", bg="green", fg="white", command=loginPage).pack(pady=6)
Button(
    loginFrame, text="Create New Account", fg="blue", command=signUp, borderwidth=0
).pack()

root.mainloop()
