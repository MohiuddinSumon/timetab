# TimeTab

TimeTab is a desktop application that combines Google Calendar integration with a Pomodoro timer. It displays your current and upcoming events from Google Calendar and helps you manage your work sessions with a built-in Pomodoro timer.

## Features

- Google Calendar integration
- Display of current and upcoming events
- Personalized greeting based on the time of day
- Pomodoro timer with customizable work sessions and breaks
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
pip install -r requirements.txt
```

3. Download the `credentials.json` file from the Google Developer Console and place it in the same directory as the script. Be sure to select Desktop client.

## Usage

To run the application from source:

```
python pomo.py
```

To build an executable:

```
pyinstaller --onefile --windowed --icon=timetab_win.ico --add-data "credentials.json;." --add-data "timetab_win.ico;." --hidden-import cryptography --hidden-import pytz --name=timetab.exe pomo.py
```

Replace `pomo.py` with the name of your Python script if it's different.

## First Run

On the first run, the application will open a web browser for Google OAuth authentication. Follow the prompts to grant the necessary permissions. After successful authentication, the application will display your calendar events and the Pomodoro timer.

## Notes

- The Google OAuth token is encrypted and stored locally for future use.
- The Pomodoro timer runs for customizable work sessions, followed by breaks.
- The break notification will appear on top of other windows to ensure you don't miss it.

## Troubleshooting

If you encounter any issues with missing modules when building the executable, you may need to add more `--hidden-import` flags to the PyInstaller command.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

We welcome contributions to TimeTab! Here are some ways you can contribute:

1. Report bugs or suggest features by opening an issue.
2. Improve documentation by submitting pull requests.
3. Write code to fix issues or add new features.

To contribute code:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Write your code and add tests if possible.
4. Ensure your code follows the project's coding style.
5. Submit a pull request with a clear description of your changes.

## Support

If you have any questions or need help with TimeTab, please open an issue on the GitHub repository.

## Acknowledgements

TimeTab uses the Google Calendar API and several open-source Python libraries. We're grateful to all the developers who contribute to these projects.
