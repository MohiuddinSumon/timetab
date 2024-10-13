# TimeTab

TimeTab is a desktop application that combines Google Calendar integration with a Pomodoro timer. It displays your current and upcoming events from Google Calendar and helps you manage your work sessions with a built-in Pomodoro timer.

## Features

- Google Calendar integration
- Display of current and upcoming events
- Personalized greeting based on the time of day
- Pomodoro timer with 25-minute work sessions and 5-minute breaks
- Encrypted storage of Google OAuth tokens

## Requirements

- Python 3.7+
- Required Python packages:
  - google-auth
  - google-auth-oauthlib
  - google-auth-httplib2
  - google-api-python-client
  - cryptography
  - pytz

## Installation

1. Clone this repository or download the source code.
2. Install the required packages:

```
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client cryptography pytz
```

3. Download the `credentials.json` file from the Google Developer Console and place it in the same directory as the script.

## Usage

To run the application from source:

```
python timetab.py
```

To build an executable:

```
pyinstaller --onefile --windowed --icon=timetab_win.ico --add-data "credentials.json;." --hidden-import cryptography --hidden-import pytz --name=timetab.exe timetab.py
```

Replace `timetab.py` with the name of your Python script if it's different.

## First Run

On the first run, the application will open a web browser for Google OAuth authentication. Follow the prompts to grant the necessary permissions. After successful authentication, the application will display your calendar events and the Pomodoro timer.

## Notes

- The Google OAuth token is encrypted and stored locally for future use.
- The Pomodoro timer runs for 25-minute work sessions, followed by a 5-minute break.
- The break notification will appear on top of other windows to ensure you don't miss it.

## Troubleshooting

If you encounter any issues with missing modules when building the executable, you may need to add more `--hidden-import` flags to the PyInstaller command.

## License

[Specify your license here]

## Contributing

[Specify how others can contribute to your project]

## Contact

[Your contact information or how to reach you for questions/support]