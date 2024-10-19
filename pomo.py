import base64
import datetime
import hashlib
import json
import os
import sys
import threading
import tkinter as tk
from io import BytesIO
from tkinter import messagebox, simpledialog, ttk

import pytz
import requests
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from PIL import Image, ImageDraw, ImageOps, ImageTk

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events.readonly",
    "https://www.googleapis.com/auth/userinfo.profile",
]
REDIRECT_URI = "https://localhost:8080/"

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


class ToolTip(object):
    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0

    def showtip(self, text):
        "Display text in tooltip window"
        self.text = text
        if self.tipwindow or not self.text:
            return
        bbox = self.widget.bbox("insert")
        if not bbox:  # If bbox is None, use the widget's position
            x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
            y = self.widget.winfo_rooty() + self.widget.winfo_height()
        else:
            x, y, _, _ = bbox
            x += self.widget.winfo_rootx() + 25
            y += self.widget.winfo_rooty() + 25

        # creates a toplevel window
        self.tipwindow = tw = tk.Toplevel(self.widget)
        # Leaves only the label and removes the app window
        tw.wm_overrideredirect(1)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw,
            text=self.text,
            justify=tk.LEFT,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            font=("tahoma", "8", "normal"),
        )
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()


def create_tooltip(widget, text):
    toolTip = ToolTip(widget)

    def enter(event):
        toolTip.showtip(text)

    def leave(event):
        toolTip.hidetip()

    widget.bind("<Enter>", enter)
    widget.bind("<Leave>", leave)


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

    def start_auth(self):
        self.parent.authenticate()


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
            "Start.Pomodoro.TButton",
            background="#4CAF50",
            foreground="white",
            font=("Helvetica", 10, "bold"),
            padding=5,
        )
        style.map(
            "Start.Pomodoro.TButton",
            background=[("active", "#b749de")],
            relief=[("pressed", "sunken")],
        )

        style.configure(
            "Stop.Pomodoro.TButton",
            background="#cd50fa",
            foreground="white",
            font=("Helvetica", 10, "bold"),
            padding=5,
        )
        style.map(
            "Stop.Pomodoro.TButton",
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

        # Create a horizontal frame for time and menu
        self.time_menu_horizontal = ttk.Frame(
            self.time_menu_frame, style="Header.TFrame"
        )
        self.time_menu_horizontal.pack(side=tk.TOP)

        self.time_label = ttk.Label(
            self.time_menu_horizontal, text="", style="HeaderTime.TLabel"
        )
        self.time_label.pack(side=tk.LEFT, padx=(0, 5))

        self.create_menu()

    def create_menu(self):
        self.menu_var = tk.StringVar()

        # Create a more compact menu button
        self.menu = ttk.OptionMenu(
            self.time_menu_horizontal,
            self.menu_var,
            "",  # Use dots as menu icon
            "About",
            "Logout",
            command=self.handle_menu_selection,
        )
        self.menu.config(style="TMenubutton")
        # self.menu.pack(side=tk.BOTTOM)
        # Configure the menu button style for minimal width
        style = ttk.Style()
        style.configure(
            "TMenubutton",
            background="#3498db",
            foreground="white",
            font=("Helvetica", 12),
            padding=0,  # Reduced padding
            width=0,  # Set minimal width
        )

        # Pack the menu button to the right of the time
        self.menu.pack(side=tk.LEFT, padx=(0, 0))

    def handle_menu_selection(self, selection):
        if selection == "Logout":
            self.parent.logout()
        elif selection == "About":
            # Add settings functionality here
            pass
        self.menu_var.set("")  # Reset the menu to default text

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
            style="Start.Pomodoro.TButton",
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
                self.create_event_rectangle(event, y_offset, "#0B8043")
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

            for i, event in enumerate(upcoming_events[:4]):
                color = colors[i % len(colors)]
                self.create_event_rectangle(event, y_offset, color)
                y_offset += 50
        else:
            self.events_canvas.create_text(
                10,
                y_offset,
                text="No Upcoming Events",
                anchor="w",
                font=("Arial", 12, "bold"),
            )

    def create_event_rectangle(self, event, y_offset, color):
        start = event["start"].get("dateTime", event["start"].get("date"))
        end = event["end"].get("dateTime", event["end"].get("date"))
        start_dt = datetime.datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_dt = datetime.datetime.fromisoformat(end.replace("Z", "+00:00"))

        rect_id = self.events_canvas.create_rectangle(
            10, y_offset, 270, y_offset + 40, fill=color, outline=""
        )
        text_id1 = self.events_canvas.create_text(
            25,
            y_offset + 10,
            text=f"{start_dt.strftime('%Y-%m-%d %H:%M')} - {end_dt.strftime('%Y-%m-%d %H:%M')}",
            anchor="w",
            fill="white",
            font=("Arial", 9),
        )
        text_id2 = self.events_canvas.create_text(
            25,
            y_offset + 25,
            text=event["summary"],
            anchor="w",
            fill="white",
            font=("Arial", 12, "bold"),
        )

        # Create tooltip for the event
        description = event.get("description", "No description available")
        tooltip_text = f"Summary: {event['summary']}\nDescription: {description}"

        def show_tooltip(event):
            if not hasattr(self, "tip") or not self.tip.winfo_exists():
                x = self.events_canvas.winfo_rootx() + event.x + 10
                y = self.events_canvas.winfo_rooty() + event.y + 10
                self.tip = tk.Toplevel(self.events_canvas)
                self.tip.wm_overrideredirect(True)
                self.tip.wm_geometry(f"+{x}+{y}")
                label = tk.Label(
                    self.tip,
                    text=tooltip_text,
                    justify=tk.LEFT,
                    background="#ffffe0",
                    relief=tk.SOLID,
                    borderwidth=1,
                    font=("tahoma", "8", "normal"),
                )
                label.pack(ipadx=1)

        def hide_tooltip(event):
            if hasattr(self, "tip") and self.tip.winfo_exists():
                self.tip.destroy()

        def on_enter(event):
            # Change color only, skip zooming
            lighter_color = self.lighten_color(color)
            self.events_canvas.itemconfig(rect_id, fill=lighter_color)
            show_tooltip(event)

        def on_leave(event):
            # Restore original color
            self.events_canvas.itemconfig(rect_id, fill=color)
            hide_tooltip(event)

        self.events_canvas.tag_bind(rect_id, "<Enter>", on_enter)
        self.events_canvas.tag_bind(rect_id, "<Leave>", on_leave)
        self.events_canvas.tag_bind(text_id1, "<Enter>", on_enter)
        self.events_canvas.tag_bind(text_id1, "<Leave>", on_leave)
        self.events_canvas.tag_bind(text_id2, "<Enter>", on_enter)
        self.events_canvas.tag_bind(text_id2, "<Leave>", on_leave)

    def lighten_color(self, color):
        # Convert color to RGB
        r, g, b = self.winfo_rgb(color)
        # Lighten the color
        r = min(int(r * 1.2), 65535)
        g = min(int(g * 1.2), 65535)
        b = min(int(b * 1.2), 65535)
        # Convert back to hex
        return f"#{r//256:02x}{g//256:02x}{b//256:02x}"

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
            self.start_pomodoro_button.config(
                text="Stop Focus", style="Stop.Pomodoro.TButton"
            )
        else:
            self.pomodoro_active = False
            self.pomodoro_time_left = self.focus_time * 60
            self.pomodoro_time.config(text=f"{self.focus_time}:00")
            self.start_pomodoro_button.config(
                text="Start Focus", style="Start.Pomodoro.TButton"
            )

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

        # Maximize the window
        popup.state("zoomed")
        # popup.geometry("300x150")
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

        # Load environment variables
        load_dotenv()
        encryption_key = os.getenv("ENCRYPTION_KEY")
        if not encryption_key:
            encryption_key = base64.b64encode(os.urandom(32)).decode()
            # print("No encryption key set, generated a random one:")
            # print(encryption_key)

        # Initialize encryptor with a secret key (you should use a more secure key in production)
        self.encryptor = Encryptor(encryption_key)

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
        credential_path = get_resource_path("credentials.json")
        if os.path.exists(self.token_path):
            try:
                with open(self.token_path, "r") as token_file:
                    encrypted_token = token_file.read()
                    token_data = self.encryptor.decrypt(encrypted_token)
                    creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            except Exception as e:
                print(f"Error loading credentials: {e}")
                creds = None
                if os.path.exists(self.token_path):
                    os.remove(self.token_path)

        if not creds or not creds.valid:
            if creds and creds.expired:  # and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing credentials: {e}")
                    creds = None
                    if os.path.exists(self.token_path):
                        os.remove(self.token_path)

            if not creds:
                if hasattr(self, "auth_thread") and self.auth_thread.is_alive():
                    return  # Don't start another auth flow if one is already running

                flow = InstalledAppFlow.from_client_secrets_file(
                    credential_path, SCOPES
                )
                self.auth_thread = threading.Thread(
                    target=self.run_auth_flow, args=(flow,)
                )
                self.auth_thread.daemon = (
                    True  # Make thread daemon so it closes with main app
                )
                self.auth_thread.start()
                return  # Return here as we'll handle the rest in run_auth_flow

        # If we have valid credentials, proceed with setup
        self.setup_services(creds)

    def run_auth_flow(self, flow):
        """Run the OAuth flow in a separate thread and update the UI on completion."""
        try:
            creds = flow.run_local_server(
                port=0, access_type="offline", prompt="consent"
            )
            self.save_credentials(creds)
            # Use after_idle to safely update UI from the thread
            self.after_idle(lambda: self.setup_services(creds))
        except Exception as e:
            print(f"Authentication error: {e}")
            self.after_idle(
                lambda: self.show_error_message(
                    "Authentication failed. Please try again."
                )
            )

    def setup_services(self, creds):
        """Set up services after successful authentication"""
        try:
            self.service = build("calendar", "v3", credentials=creds)
            user_info_service = build("oauth2", "v2", credentials=creds)
            user_info = user_info_service.userinfo().get().execute()
            self.user_name = user_info.get("name", "User")
            self.user_image_url = user_info.get("picture", "")
            self.show_calendar_widget()
        except Exception as e:
            print(f"Error setting up services: {e}")
            self.show_error_message("Failed to setup services. Please try again.")

    def save_credentials(self, creds):
        creds_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
        }
        # print(creds_data)
        encrypted_creds = self.encryptor.encrypt(creds_data)
        with open(self.token_path, "w") as token_file:
            token_file.write(encrypted_creds)


if __name__ == "__main__":
    app = CalendarWidget()
    app.mainloop()

# pyinstaller --onefile --windowed --icon=timetab_win.ico --add-data "credentials.json;." --add-data "timetab_win.ico;." --name=pomo.exe pomo.py
# pyinstaller --onefile --windowed --icon=timetab_win.ico --add-data "credentials.json;." --hidden-import cryptography --add-binary "C:\path\to\python\Lib\site-packages\cryptography\hazmat\bindings\\_padding.pyd;cryptography\hazmat\bindings" --add-binary "C:\path\to\python\Lib\site-packages\cryptography\hazmat\bindings\\_openssl.pyd;cryptography\hazmat\bindings" --name=timetab.exe auto.py
