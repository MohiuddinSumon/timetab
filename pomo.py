import base64
import datetime
import hashlib
import json
import os
import sys
import threading
import tkinter as tk
import webbrowser
from io import BytesIO
from tkinter import messagebox, simpledialog, ttk

import pytz
import requests
from cryptography.fernet import Fernet
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from PIL import Image, ImageDraw, ImageOps, ImageTk

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/userinfo.profile",
]

# Define the color dictionary
COLORS = {
    "1": "#A4BDFC",  # Lavender
    "2": "#7AE7BF",  # Sage
    "3": "#DBADFF",  # Grape
    "4": "#FF887C",  # Flamingo
    "5": "#FBD75B",  # Banana
    "6": "#FFB878",  # Tangerine
    "7": "#46D6DB",  # Peacock
    "8": "#E1E1E1",  # Graphite
    "9": "#5484ED",  # Blueberry
    "10": "#51B749",  # Basil
    "11": "#DC2127",  # Tomato
    None: "#000000",  # Default color (white)
}


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller bundle."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def get_config_path():
    """Get the path to the configuration directory."""
    if sys.platform == "win32":
        return os.path.join(os.environ["APPDATA"], "TimeTab")
    elif sys.platform == "darwin":
        return os.path.join(
            os.path.expanduser("~"), "Library", "Application Support", "TimeTab"
        )
    else:  # linux or other unix-like
        return os.path.join(os.path.expanduser("~"), ".config", "timetab")


class Encryptor:
    def __init__(self, key):
        self.key = base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest())
        self.f = Fernet(self.key)

    def encrypt(self, data):
        return self.f.encrypt(json.dumps(data).encode()).decode()

    def decrypt(self, data):
        return json.loads(self.f.decrypt(data.encode()).decode())


class LoginScreen(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.pack()

        self.label = ttk.Label(self, text="Authentication Required", font=("Arial", 14))
        self.label.pack(pady=10)

        self.auth_button = ttk.Button(
            self, text="Authenticate", command=self.start_auth
        )
        self.auth_button.pack(pady=10)

        self.auth_code_label = ttk.Label(self, text="Enter the authorization code:")
        self.auth_code_label.pack(pady=5)

        self.auth_code_entry = ttk.Entry(self, width=50)
        self.auth_code_entry.pack(pady=5)

        self.submit_button = ttk.Button(
            self, text="Submit", command=self.submit_auth_code
        )
        self.submit_button.pack(pady=10)

    def start_auth(self):
        threading.Thread(target=self.parent.start_authentication, daemon=True).start()

    def submit_auth_code(self):
        auth_code = self.auth_code_entry.get()
        if auth_code:
            self.parent.complete_authentication(auth_code)
        else:
            messagebox.showerror("Error", "Please enter the authorization code.")


class CalendarWidgetMain(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.pack(fill=tk.BOTH, expand=True)
        self.configure(bg="#f0f4f8")

        self.focus_time = 25  # Default focus time in minutes
        self.create_styles()
        self.create_header()
        self.create_events_area()
        self.create_pomodoro_area()

        self.update_widget()
        self.update_pomodoro()

    def create_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Header styles
        style.configure("Header.TFrame", background="#3498db")
        style.configure(
            "HeaderText.TLabel",
            background="#3498db",
            foreground="white",
            font=("Helvetica", 12),
        )
        style.configure(
            "HeaderTime.TLabel",
            background="#3498db",
            foreground="white",
            font=("Helvetica", 18, "bold"),
        )

        # Event styles
        style.configure("Event.TFrame", background="#ffffff")
        style.configure(
            "EventTitle.TLabel",
            background="#ffffff",
            foreground="black",
            font=("Helvetica", 10, "bold"),
        )
        style.configure(
            "EventTime.TLabel",
            background="#ffffff",
            foreground="black",
            font=("Helvetica", 9),
        )

        # Pomodoro styles
        style.configure("Pomodoro.TFrame", background="#f0f4f8")
        style.configure(
            "PomodoroText.TLabel",
            background="#f0f4f8",
            font=("Helvetica", 12, "bold", "italic"),
        )
        style.configure(
            "PomodoroTime.TLabel", background="#f0f4f8", font=("Helvetica", 24, "bold")
        )

        # Pomodoro button styles
        style.configure(
            "Pomodoro.TButton",
            background="#4CAF50",
            foreground="white",
            font=("Helvetica", 10, "bold"),
            padding=5,
        )
        style.map(
            "Pomodoro.TButton",
            background=[("active", "#45a049")],
            relief=[("pressed", "sunken")],
        )

        style.configure(
            "SetTime.TButton",
            background="#2196F3",
            foreground="white",
            font=("Helvetica", 10),
            padding=5,
        )
        style.map(
            "SetTime.TButton",
            background=[("active", "#1E88E5")],
            relief=[("pressed", "sunken")],
        )

        # Dropdown menu style
        style.configure(
            "TMenubutton",
            background="#3498db",
            foreground="white",
            font=("Helvetica", 10),
            padding=5,
        )
        style.map(
            "TMenubutton",
            background=[("active", "#2980b9")],
            relief=[("pressed", "sunken")],
        )

    def create_header(self):
        self.header_frame = ttk.Frame(self, style="Header.TFrame")
        self.header_frame.pack(fill=tk.X, padx=10, pady=10)

        # User info (left side)
        self.user_frame = ttk.Frame(self.header_frame, style="Header.TFrame")
        self.user_frame.pack(side=tk.LEFT)

        self.user_image = self.load_user_image()
        self.user_image_label = ttk.Label(
            self.user_frame, image=self.user_image, background="#3498db"
        )
        self.user_image_label.pack(side=tk.LEFT, padx=(0, 10))

        self.user_info_frame = ttk.Frame(self.user_frame, style="Header.TFrame")
        self.user_info_frame.pack(side=tk.LEFT)

        self.greeting_label = ttk.Label(
            self.user_info_frame, text="Good morning,", style="HeaderText.TLabel"
        )
        self.greeting_label.pack(anchor=tk.W)

        self.name_label = ttk.Label(
            self.user_info_frame, text=self.parent.user_name, style="HeaderText.TLabel"
        )
        self.name_label.pack(anchor=tk.W)

        # Time and menu (right side)
        self.time_menu_frame = ttk.Frame(self.header_frame, style="Header.TFrame")
        self.time_menu_frame.pack(side=tk.RIGHT)

        self.time_label = ttk.Label(
            self.time_menu_frame, text="", style="HeaderTime.TLabel"
        )
        self.time_label.pack(side=tk.TOP)

        self.create_menu()

    def create_menu(self):
        self.menu_var = tk.StringVar()
        self.menu = ttk.OptionMenu(
            self.time_menu_frame,
            self.menu_var,
            "Menu",
            "Settings",
            "Logout",
            command=self.handle_menu_selection,
        )
        self.menu.config(style="TMenubutton")
        self.menu.pack(side=tk.BOTTOM)

    def handle_menu_selection(self, selection):
        if selection == "Logout":
            self.parent.logout()
        elif selection == "Settings":
            # Add settings functionality here
            pass
        self.menu_var.set("Menu")  # Reset the menu to default text

    def create_events_area(self):
        self.events_canvas = tk.Canvas(self, bg="#ffffff", height=250, width=280)
        self.events_canvas.pack(padx=10, pady=10)

    def create_pomodoro_area(self):
        self.pomodoro_frame = ttk.Frame(self, style="Pomodoro.TFrame")
        self.pomodoro_frame.pack(fill=tk.X, padx=10, pady=5)

        self.pomodoro_label = ttk.Label(
            self.pomodoro_frame, text="Focus Timer", style="PomodoroText.TLabel"
        )
        self.pomodoro_label.pack(side=tk.TOP)

        timer_frame = ttk.Frame(self.pomodoro_frame, style="Pomodoro.TFrame")
        timer_frame.pack(side=tk.TOP, pady=5)

        self.start_pomodoro_button = ttk.Button(
            timer_frame,
            text="Start Focus",
            command=self.start_pomodoro,
            style="Pomodoro.TButton",
        )
        self.start_pomodoro_button.pack(side=tk.LEFT, padx=(0, 10))

        self.pomodoro_time = ttk.Label(
            timer_frame,
            text=f"{self.focus_time}:00",
            style="PomodoroTime.TLabel",
        )
        self.pomodoro_time.pack(side=tk.LEFT)

        self.set_time_button = ttk.Button(
            timer_frame,
            text="Set Time",
            command=self.set_focus_time,
            style="SetTime.TButton",
        )
        self.set_time_button.pack(side=tk.LEFT, padx=(10, 0))

        self.pomodoro_active = False
        self.pomodoro_time_left = self.focus_time * 60

    def load_user_image(self):
        if hasattr(self.parent, "user_image_url") and self.parent.user_image_url:
            try:
                response = requests.get(self.parent.user_image_url)
                image = Image.open(BytesIO(response.content))
                image = image.resize((40, 40), Image.LANCZOS)
                image = self.create_circular_image(image)
                return ImageTk.PhotoImage(image)
            except Exception as e:
                print(f"Error loading user image: {e}")

        # Fallback to placeholder if no URL or loading fails
        image = Image.new("RGB", (40, 40), color="#2980b9")
        image = self.create_circular_image(image)
        return ImageTk.PhotoImage(image)

    def create_circular_image(self, image):
        mask = Image.new("L", image.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + image.size, fill=255)
        output = ImageOps.fit(image, mask.size, centering=(0.5, 0.5))
        output.putalpha(mask)
        return output

    def update_widget(self):
        current_time = datetime.datetime.now()
        time_str = current_time.strftime("%H:%M")
        self.time_label.config(text=time_str)

        greeting = self.get_greeting(current_time)
        self.greeting_label.config(text=f"{greeting},")

        self.update_events()

        self.after(1000 * 60, self.update_widget)  # Update every minutes

    def update_pomodoro(self):
        if self.pomodoro_active:
            if self.pomodoro_time_left > 0:
                minutes, seconds = divmod(self.pomodoro_time_left, 60)
                self.pomodoro_time.config(text=f"{minutes:02d}:{seconds:02d}")
                self.pomodoro_time_left -= 1
            else:
                self.pomodoro_active = False
                self.start_pomodoro_button.config(text="Start Focus")
                self.show_break_popup()
                self.pomodoro_time_left = self.focus_time * 60
                self.pomodoro_time.config(text=f"{self.focus_time}:00")

        self.after(1000, self.update_pomodoro)

    def get_greeting(self, current_time):
        hour = current_time.hour
        if 5 <= hour < 12:
            return "Good morning"
        elif 12 <= hour < 18:
            return "Good afternoon"
        else:
            return "Good evening"

    def update_events(self):
        self.events_canvas.delete("all")
        current_events, upcoming_events = self.get_upcoming_events()
        y_offset = 10
        colors = ["#4285F4", "#D81B60", "#F4511E", "#F6BF26", "#0B8043"]

        # Display Current Events
        if current_events:
            self.events_canvas.create_text(
                10,
                y_offset + 5,
                text="Current Events:",
                anchor="w",
                font=("Arial", 12, "bold"),
            )
            y_offset += 20
            for event in current_events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                end = event["end"].get("dateTime", event["end"].get("date"))
                start_dt = datetime.datetime.fromisoformat(start.replace("Z", "+00:00"))
                end_dt = datetime.datetime.fromisoformat(end.replace("Z", "+00:00"))

                color = "#0B8043"
                self.events_canvas.create_rectangle(
                    10, y_offset, 270, y_offset + 40, fill=color, outline=""
                )
                self.events_canvas.create_text(
                    25,
                    y_offset + 10,
                    text=f"{start_dt.strftime('%Y-%m-%d %H:%M')} - {end_dt.strftime('%Y-%m-%d %H:%M')}",
                    anchor="w",
                    fill="white",
                    font=("Arial", 9),
                )
                self.events_canvas.create_text(
                    25,
                    y_offset + 25,
                    text=event["summary"],
                    anchor="w",
                    fill="white",
                    font=("Arial", 12, "bold"),
                )
                y_offset += 50
        else:
            self.events_canvas.create_text(
                10,
                y_offset + 5,
                text="No Current Events",
                anchor="w",
                font=("Arial", 12, "bold"),
            )
            y_offset += 20
            self.events_canvas.create_rectangle(
                10, y_offset, 270, y_offset + 40, fill="#4ac1d9", outline=""
            )
            self.events_canvas.create_text(
                25,
                y_offset + 18,
                text="Free time!",
                anchor="w",
                fill="white",
                font=("Arial", 13, "bold"),
            )
            y_offset += 55

        # Display Upcoming Events
        if upcoming_events:
            self.events_canvas.create_text(
                10,
                y_offset + 3,
                text="Upcoming Events:",
                anchor="w",
                font=("Arial", 12, "bold"),
            )
            y_offset += 20

            for i, event in enumerate(
                upcoming_events[:4]
            ):  # Display only 4 upcoming events
                start = event["start"].get("dateTime", event["start"].get("date"))
                start_dt = datetime.datetime.fromisoformat(start.replace("Z", "+00:00"))
                start_str = start_dt.strftime("%Y-%m-%d %H:%M")

                color = colors[i % len(colors)]
                self.events_canvas.create_rectangle(
                    10, y_offset, 270, y_offset + 40, fill=color, outline=""
                )
                self.events_canvas.create_text(
                    25,
                    y_offset + 10,
                    text=start_str,
                    anchor="w",
                    fill="white",
                    font=("Arial", 8),
                )
                self.events_canvas.create_text(
                    25,
                    y_offset + 25,
                    text=event["summary"],
                    anchor="w",
                    fill="white",
                    font=("Arial", 10, "bold"),
                )
                y_offset += 50
        else:
            self.events_canvas.create_text(
                10,
                y_offset,
                text="No Upcoming Events",
                anchor="w",
                font=("Arial", 12, "bold"),
            )

    def get_upcoming_events(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        now_iso = now.isoformat()
        service = self.parent.service  # Reuse the cached service
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now_iso,
                maxResults=10,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        current_events = []
        upcoming_events = []

        for event in events_result.get("items", []):
            start = event["start"].get("dateTime", event["start"].get("date"))
            end = event["end"].get("dateTime", event["end"].get("date"))

            # Parse the datetime strings and set the timezone
            start_dt = datetime.datetime.fromisoformat(
                start.replace("Z", "+00:00")
            ).astimezone(pytz.UTC)
            end_dt = datetime.datetime.fromisoformat(
                end.replace("Z", "+00:00")
            ).astimezone(pytz.UTC)

            if start_dt <= now <= end_dt:
                current_events.append(event)
            elif start_dt > now:
                upcoming_events.append(event)

            # print(f"Now: {now}")
            # print(f"Start: {start_dt}")
            # print(f"End: {end_dt}")
            # print(f"Event: {event['summary']}")
            # print(f"Is current: {start_dt <= now <= end_dt}")
            # print("---")

            # 'start': {'dateTime': '2024-10-13T22:30:00+06:00', 'timeZone': 'Asia/Dhaka'}, 'end': {'dateTime': '2024-10-14T04:30:00+06:00', 'timeZone': 'Asia/Dhaka'},

            if len(current_events) + len(upcoming_events) >= 4:
                break

        return current_events, upcoming_events

    def get_current_event(self, events):
        now = datetime.datetime.now(datetime.timezone.utc)
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            end = event["end"].get("dateTime", event["end"].get("date"))
            start_dt = datetime.datetime.fromisoformat(
                start.replace("Z", "+00:00")
            ).replace(tzinfo=pytz.UTC)
            end_dt = datetime.datetime.fromisoformat(
                end.replace("Z", "+00:00")
            ).replace(tzinfo=pytz.UTC)
            if start_dt <= now <= end_dt:
                return event
        return None

    def set_focus_time(self):
        new_time = simpledialog.askinteger(
            "Set Focus Time",
            "Enter focus time in minutes:",
            minvalue=1,
            maxvalue=120,
            parent=self.parent,
        )
        if new_time:
            self.focus_time = new_time
            self.pomodoro_time_left = new_time * 60
            self.pomodoro_time.config(text=f"{new_time}:00")

    def start_pomodoro(self):
        if not self.pomodoro_active:
            self.pomodoro_active = True
            self.pomodoro_time_left = self.focus_time * 60
            self.start_pomodoro_button.config(text="Stop Focus")
        else:
            self.pomodoro_active = False
            self.pomodoro_time_left = self.focus_time * 60
            self.pomodoro_time.config(text=f"{self.focus_time}:00")
            self.start_pomodoro_button.config(text="Start Focus")

    def update_pomodoro_timer(self):
        if self.pomodoro_time_left > 0:
            minutes, seconds = divmod(self.pomodoro_time_left, 60)
            self.pomodoro_time.config(text=f"{minutes:02d}:{seconds:02d}")
            self.pomodoro_time_left -= 1
        else:
            self.pomodoro_active = False
            self.start_pomodoro_button.config(text="Start Focus")
            self.show_break_popup()
            self.pomodoro_time_left = self.focus_time * 60
            self.pomodoro_time.config(text=f"{self.focus_time}:00")

    def show_break_popup(self):
        popup = tk.Toplevel(self)
        popup.title("Break Time")
        popup.geometry("300x150")
        popup.attributes("-topmost", True)
        popup.focus_force()
        # Set custom icon
        icon_path = get_resource_path("timetab_win.ico")
        popup.iconbitmap(icon_path)

        message = ttk.Label(
            popup,
            text=f"Time's up! Take a {max(self.focus_time // 5, 5)} minute break.",
            font=("Helvetica", 12),
            background="#ffffff",
        )
        message.pack(pady=20)

        ok_button = ttk.Button(popup, text="OK", command=popup.destroy)
        ok_button.pack(pady=10)


class CalendarWidget(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TimeTab")
        self.geometry("300x435")
        self.configure(bg="#ffffff")

        self.service = None
        self.flow = None
        self.user_name = "User"

        # Set custom icon
        icon_path = get_resource_path("timetab_win.ico")
        self.iconbitmap(default=icon_path)

        # Ensure config directory exists
        self.config_dir = get_config_path()
        os.makedirs(self.config_dir, exist_ok=True)

        self.token_path = os.path.join(self.config_dir, "token.enc")
        credentials_path = get_resource_path("credentials.json")

        # Initialize encryptor with a secret key (you should use a more secure key in production)
        self.encryptor = Encryptor("your_secret_key_here")

        if not os.path.exists(credentials_path):
            self.show_error_message(
                "Missing credentials.json file. Please download it from Google Developer Console."
            )
        else:
            self.authenticate()

    def show_error_message(self, message):
        messagebox.showerror("Error", message)
        self.quit()

    def show_login_screen(self):
        self.login_screen = LoginScreen(self)
        self.login_screen.pack()

    def logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            # Clear the stored credentials
            if os.path.exists(self.token_path):
                os.remove(self.token_path)

            # Clear the current session
            self.service = None
            self.user_name = "User"
            self.user_image_url = ""

            # Remove the calendar widget
            if hasattr(self, "calendar_widget"):
                self.calendar_widget.pack_forget()

            # Show the login screen again
            self.show_login_screen()

    def show_calendar_widget(self):
        if hasattr(self, "login_screen"):
            self.login_screen.pack_forget()
        self.calendar_widget = CalendarWidgetMain(self)
        self.calendar_widget.pack()

        # self.calendar_widget = CalendarWidgetMain(self)
        # self.calendar_widget.pack()

        # self.calendar_widget = ModernCalendarWidgetMain(self)
        # self.calendar_widget.pack(fill=tk.BOTH, expand=True)

    def authenticate(self):
        creds = None
        if os.path.exists(self.token_path):
            try:
                with open(self.token_path, "r") as token_file:
                    encrypted_token = token_file.read()
                    token_data = self.encryptor.decrypt(encrypted_token)
                    creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            except Exception as e:
                print(f"Error loading credentials: {e}")
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing credentials: {e}")
                    creds = None

            if not creds:
                self.show_login_screen()
                return

        # Save the refreshed credentials
        self.save_credentials(creds)

        # Set the service after authentication
        self.service = build("calendar", "v3", credentials=creds)

        # Get user's name
        user_info_service = build("oauth2", "v2", credentials=creds)
        user_info = user_info_service.userinfo().get().execute()
        # print(user_info)
        self.user_name = user_info.get("name", "User")
        self.user_image_url = user_info.get("picture", "")

        self.show_calendar_widget()

    def start_authentication(self):
        credentials_path = get_resource_path("credentials.json")
        self.flow = Flow.from_client_secrets_file(
            credentials_path, scopes=SCOPES, redirect_uri="urn:ietf:wg:oauth:2.0:oob"
        )
        auth_url, _ = self.flow.authorization_url(prompt="consent")

        webbrowser.open(auth_url)
        messagebox.showinfo(
            "Authentication",
            "Please complete the authentication in your web browser and copy the authorization code.",
        )

    def complete_authentication(self, auth_code):
        try:
            self.flow.fetch_token(code=auth_code)
            creds = self.flow.credentials

            self.save_credentials(creds)

            self.service = build("calendar", "v3", credentials=creds)
            self.show_calendar_widget()
        except Exception as e:
            messagebox.showerror("Authentication Error", f"An error occurred: {str(e)}")

    def save_credentials(self, creds):
        creds_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
        }
        encrypted_creds = self.encryptor.encrypt(creds_data)
        with open(self.token_path, "w") as token_file:
            token_file.write(encrypted_creds)


if __name__ == "__main__":
    app = CalendarWidget()
    app.mainloop()

# pyinstaller --onefile --windowed --icon=timetab_win.ico --add-data "credentials.json;." --name=pomo.exe pomo.py
# pyinstaller --onefile --windowed --icon=timetab_win.ico --add-data "credentials.json;." --hidden-import cryptography --add-binary "C:\path\to\python\Lib\site-packages\cryptography\hazmat\bindings\\_padding.pyd;cryptography\hazmat\bindings" --add-binary "C:\path\to\python\Lib\site-packages\cryptography\hazmat\bindings\\_openssl.pyd;cryptography\hazmat\bindings" --name=timetab.exe auto.py
