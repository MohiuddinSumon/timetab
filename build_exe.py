import os
import sys

import PyInstaller.__main__

# Get the directory where the script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

# Define icon path
icon_path = os.path.join(script_dir, "timetab_win.ico")
# Define credentials path
credentials_path = os.path.join(script_dir, "credentials.json")

# Set the output filename with the .exe extension
output_filename = "timetab.exe"

# pyinstaller -- -- --icon=timetab_win.ico --add-data "credentials.json;." --add-data "timetab_win.ico;." --name=timetab.exe pomo.py

PyInstaller.__main__.run(
    [
        "pomo.py",  # your main script
        "--onefile",  # create a single executable
        "--windowed",  # prevent console window from appearing
        f"--add-data={icon_path}:.",  # include the icon
        f"--add-data={credentials_path}:.",  # include the icon
        "--icon",
        icon_path,  # set executable icon
        "--name",
        output_filename,
        "--clean",  # clean PyInstaller cache
        "--hidden-import",
        "cryptography",
        "--hidden-import",
        "pytz",
    ]
)

print(f"Executable created: {os.path.join('dist', output_filename)}")
