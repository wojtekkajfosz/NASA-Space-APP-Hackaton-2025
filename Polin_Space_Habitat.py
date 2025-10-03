import tkinter as tk
from PIL import Image, ImageTk
import requests
from io import BytesIO
from datetime import datetime, timedelta
import random
import streamlit
import numpy
import statistics
# Function to open the APOD window
def open_apod_window(location):
    global root, label, text_label, generate_btn, go_to_btn1, go_to_btn2
    root.destroy()  # Close the initial window
    root = tk.Tk()
    root.title(f"{location} Image Example")
    root.configure(bg="#222")
    root.geometry("900x900")  # Ustawienie stałego rozmiaru okna

    # Initialize labels
    label = tk.Label(root, bg="#222")
    label.place(x=0, y=0)  # Position at top-left corner
    text_label = tk.Label(
        root,
        text="",
        bg="#222",
        fg="#fff",
        font=("Arial", 18)
    )
    text_label.place(x=0, y=700)  # Position below image

    # Set background based on location
    if location == "Moon":
        set_moon_background()
    elif location == "Outer Space":
        set_apod_background()
        # Add Generate new image button only for Outer Space
        generate_btn = tk.Button(
            root,
            text="Generate new image",
            command=lambda: set_apod_background(),
            bg="#0074D9",
            fg="#fff",
            font=("Arial", 14),
            relief=tk.RAISED,
            padx=20,
            pady=5
        )
        generate_btn.place(x=0, y=750)  # Position below text
    elif location == "Mars":
        set_mars_background()

    # Add button to open second window
    open_second_btn = tk.Button(
        root,
        text="Open Second Window",
        command=open_second_window,
        bg="#0074D9",
        fg="#fff",
        font=("Arial", 14),
        relief=tk.RAISED,
        padx=20,
        pady=5
    )
    open_second_btn.place(x=0, y=800)

    # Add close button
    close_button = tk.Button(
        root,
        text="Close",
        command=root.destroy,
        bg="#444",
        fg="#fff",
        font=("Arial", 14),
        relief=tk.RAISED,
        padx=20,
        pady=5
    )
    close_button.place(x=0, y=850)

    # Add navigation buttons in the bottom-right corner
    if location == "Outer Space":
        go_to_btn1 = tk.Button(
            root,
            text="Go to: Moon",
            command=lambda: open_apod_window("Moon"),
            bg="#0074D9",
            fg="#fff",
            font=("Arial", 12),
            relief=tk.RAISED,
            padx=10,
            pady=5
        )
        go_to_btn1.place(x=750, y=850)  # Bottom-right corner
        go_to_btn2 = tk.Button(
            root,
            text="Go to: Mars",
            command=lambda: open_apod_window("Mars"),
            bg="#0074D9",
            fg="#fff",
            font=("Arial", 12),
            relief=tk.RAISED,
            padx=10,
            pady=5
        )
        go_to_btn2.place(x=850, y=850)  # Bottom-right corner
    elif location == "Moon":
        go_to_btn1 = tk.Button(
            root,
            text="Go to: Mars",
            command=lambda: open_apod_window("Mars"),
            bg="#0074D9",
            fg="#fff",
            font=("Arial", 12),
            relief=tk.RAISED,
            padx=10,
            pady=5
        )
        go_to_btn1.place(x=750, y=850)  # Bottom-right corner
        go_to_btn2 = tk.Button(
            root,
            text="Go to: Outer Space",
            command=lambda: open_apod_window("Outer Space"),
            bg="#0074D9",
            fg="#fff",
            font=("Arial", 12),
            relief=tk.RAISED,
            padx=10,
            pady=5
        )
        go_to_btn2.place(x=850, y=850)  # Bottom-right corner
    elif location == "Mars":
        go_to_btn1 = tk.Button(
            root,
            text="Go to: Moon",
            command=lambda: open_apod_window("Moon"),
            bg="#0074D9",
            fg="#fff",
            font=("Arial", 12),
            relief=tk.RAISED,
            padx=10,
            pady=5
        )
        go_to_btn1.place(x=750, y=850)  # Bottom-right corner
        go_to_btn2 = tk.Button(
            root,
            text="Go to: Outer Space",
            command=lambda: open_apod_window("Outer Space"),
            bg="#0074D9",
            fg="#fff",
            font=("Arial", 12),
            relief=tk.RAISED,
            padx=10,
            pady=5
        )
        go_to_btn2.place(x=850, y=850)  # Bottom-right corner

    root.mainloop()

# Function to open a second window
def open_second_window():
    second_win = tk.Toplevel(root)
    second_win.title("Second Window")
    second_win.configure(bg="#0074D9")
    second_win.geometry("400x300")
    close_btn = tk.Button(
        second_win,
        text="Close",
        command=second_win.destroy,
        bg="#444",
        fg="#fff",
        font=("Arial", 14),
        relief=tk.RAISED,
        padx=20,
        pady=5
    )
    close_btn.pack(expand=True)

# Function to set a random APOD image as background
def set_apod_background():
    global label, text_label
    start_date = datetime(2015, 1, 1)  # Start date for random selection
    end_date = datetime.now()
    random_date = start_date + (end_date - start_date) * random.random()
    current_date = random_date.strftime("%Y-%m-%d")
    api_url = f"https://api.nasa.gov/planetary/apod?api_key=3VJRJsAkHwn6fskCnsqVeqv3aZtfFHEx7686Gsin&date={current_date}"
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"API Response: {data}")  # Debug: Print response to console
        if data.get("media_type") == "image":
            img_url = data["url"]
            img_response = requests.get(img_url, timeout=10)
            img_response.raise_for_status()
            img_data = img_response.content
            img = Image.open(BytesIO(img_data))
            img.thumbnail((900, 700))
            photo = ImageTk.PhotoImage(img)
            if 'label' not in globals():
                label = tk.Label(root, bg="#222")
                label.place(x=0, y=0)
            label.config(image=photo)
            label.image = photo
            text_label.config(text=f"NASA Picture of day: {data.get('date', current_date)}")
        else:
            text_label.config(text=f"No image available for {current_date}")
    except requests.RequestException as e:
        text_label.config(text=f"Error fetching APOD: {str(e)}")
        print(f"Error: {str(e)}")

# Function to set a Moon image as background
def set_moon_background():
    global label, text_label
    # Updated URL to a known Moon image from NASA
    moon_url = "https://images-assets.nasa.gov/image/PIA00405/PIA00405~large.jpg"
    try:
        img_response = requests.get(moon_url, timeout=10)
        img_response.raise_for_status()
        img_data = img_response.content
        img = Image.open(BytesIO(img_data))
        img.thumbnail((900, 700))
        photo = ImageTk.PhotoImage(img)
        if 'label' not in globals():
            label = tk.Label(root, bg="#222")
            label.place(x=0, y=0)
        label.config(image=photo)
        label.image = photo
        text_label.config(text="NASA Moon Image")
    except requests.RequestException as e:
        text_label.config(text=f"Error fetching Moon image: {str(e)}")
        print(f"Error: {str(e)}")

# Function to set a Mars image as background
def set_mars_background():
    global label, text_label
    # Updated URL to a known Mars image from NASA
    mars_url = "https://mars.nasa.gov/msl-raw-images/msss/01000/mcam/1000ML0044631300305227E03_DXXX.jpg"
    try:
        img_response = requests.get(mars_url, timeout=10)
        img_response.raise_for_status()
        img_data = img_response.content
        img = Image.open(BytesIO(img_data))
        img.thumbnail((900, 700))
        photo = ImageTk.PhotoImage(img)
        if 'label' not in globals():
            label = tk.Label(root, bg="#222")
            label.place(x=0, y=0)
        label.config(image=photo)
        label.image = photo
        text_label.config(text="NASA Mars Image")
    except requests.RequestException as e:
        text_label.config(text=f"Error fetching Mars image: {str(e)}")
        print(f"Error: {str(e)}")

# Function to handle button clicks
def select_location(location):
    if location in ["Moon", "Outer Space", "Mars"]:
        open_apod_window(location)

# Initial window
root = tk.Tk()
root.title("Space Habitat Selection")
root.configure(bg="#222")
root.geometry("400x200")

# Question label
question_label = tk.Label(root, text="Where do You want to build Your space habitat?", bg="#222", fg="#fff", font=("Arial", 20))
question_label.pack(pady=20)

# Buttons frame
button_frame = tk.Frame(root, bg="#222")
button_frame.pack(pady=10)

# Buttons
outer_space_btn = tk.Button(button_frame, text="Outer Space", command=lambda: select_location("Outer Space"), bg="#0074D9", fg="#fff", font=("Arial", 14), relief=tk.RAISED, padx=20, pady=5)
outer_space_btn.pack(side=tk.LEFT, padx=10)

moon_btn = tk.Button(button_frame, text="Moon", command=lambda: select_location("Moon"), bg="#0074D9", fg="#fff", font=("Arial", 14), relief=tk.RAISED, padx=20, pady=5)
moon_btn.pack(side=tk.LEFT, padx=10)

mars_btn = tk.Button(button_frame, text="Mars", command=lambda: select_location("Mars"), bg="#0074D9", fg="#fff", font=("Arial", 14), relief=tk.RAISED, padx=20, pady=5)
mars_btn.pack(side=tk.LEFT, padx=10)

root.mainloop()