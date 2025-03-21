# NotionCalendarBridge

NotionCalendarBridge is a Python-based tool that synchronizes events from a Notion database to Google Calendar. It ensures that your schedules stay up to date by checking for existing events and avoiding duplicate entries.

## Features

- Fetch events (name and date) from a Notion database
- Add events to Google Calendar automatically
- Prevent duplicate events from being added
- Use a configuration file to manage API keys securely

## Installation

### Prerequisites

Ensure you have the following installed:

- Python 3.x
- Required Python packages (see `requirements.txt`)
- Notion API access
- Google Calendar API credentials

### Clone the Repository

```sh
git clone https://github.com/yourusername/NotionCalendarBridge.git
cd NotionCalendarBridge
```

### Install Dependencies

```sh
pip install -r requirements.txt
```

## Configuration

### Notion API Setup
1. Go to [Notion Developers](https://developers.notion.com/).
2. Create an integration and get your **Notion API Key**.
3. Share your Notion database with the integration.
4. Get your **Database ID** from the Notion URL.

### Google Calendar API Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Enable the **Google Calendar API**.
3. Create **OAuth 2.0 credentials** and download the `credentials.json` file.
4. Place `credentials.json` in the project root directory.

### Environment Configuration
Store API keys in a `config.txt` file in the following format:

```
NOTION_API=your_notion_api_key
DATABASE_ID=your_notion_database_id
SCOPES=['https://www.googleapis.com/auth/calendar']
```

## Usage

Run the script to sync Notion events to Google Calendar:

```sh
python main.py
```

If it's the first time running the script, it will prompt you to authenticate with Google Calendar.

## Notes
- Events are checked for duplication based on their name before adding them to Google Calendar.
- The default event duration is set to 1 hour.
- If an event in Notion has no date, it will be skipped.

## License

This project is licensed under the MIT License.

## Contributions

Contributions are welcome! Feel free to submit a pull request or open an issue.

---

### Contact
For any questions or suggestions, reach out via GitHub issues.

