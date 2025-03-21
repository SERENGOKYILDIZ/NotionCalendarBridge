import os
import datetime
import pickle
from notion_client import Client
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

from config import Config

config = Config()

# Load API keys and IDs from the configuration file
NOTION_API_KEY = config.get_key("NOTION_API")
DATABASE_ID = config.get_key("DATABASE_ID")

# Google Calendar API scope
SCOPES = config.get_key("SCOPES")  # Allows read and write access to Google Calendar

# Initialize Notion API client
notion = Client(auth=NOTION_API_KEY)


# Function to authenticate and connect to Google Calendar API
def google_calendar_service():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)
    return service


# Function to fetch existing events from Google Calendar
def get_existing_events():
    service = google_calendar_service()

    events_result = service.events().list(calendarId='primary', maxResults=10, singleEvents=True,
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])

    existing_events = []
    for event in events:
        name = event['summary']
        date = event['start'].get('dateTime', event['start'].get('date'))
        existing_events.append({'name': name, 'date': date})

    return existing_events


# Function to fetch event data from Notion
def get_notion_data():
    results = notion.databases.query(database_id=DATABASE_ID)
    events = []

    for page in results["results"]:
        properties = page["properties"]

        if "Name" in properties:
            name = properties["Name"]["title"][0]["text"]["content"]
        else:
            name = "No Name"

        if "Date" in properties and properties["Date"]["date"] is not None:
            date = properties["Date"]["date"]["start"]
        else:
            date = "No Date"

        events.append({"name": name, "date": date})

    return events


# Function to add an event to Google Calendar if it doesn't already exist
def add_event_to_google_calendar(event):
    existing_events = get_existing_events()

    # Check if an event with the same name already exists
    if any(existing_event['name'] == event['name'] for existing_event in existing_events):
        print(f"(APP) Event '{event['name']}' already exists. Skipping...")
        return

    service = google_calendar_service()

    event_start = datetime.datetime.fromisoformat(event['date'])
    event_end = event_start + datetime.timedelta(hours=1)

    event_body = {
        'summary': event['name'],
        'start': {
            'dateTime': event_start.isoformat(),
            'timeZone': 'UTC',
        },
        'end': {
            'dateTime': event_end.isoformat(),
            'timeZone': 'UTC',
        },
    }

    service.events().insert(calendarId='primary', body=event_body).execute()
    print(f"(APP) Event '{event['name']}' has been added to Google Calendar.")


# Fetch events from Notion and add them to Google Calendar
events = get_notion_data()
for event in events:
    add_event_to_google_calendar(event)
