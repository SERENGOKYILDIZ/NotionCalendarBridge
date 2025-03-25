import os
import datetime
import pickle
from notion_client import Client
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from zoneinfo import ZoneInfo
import tzdata  # Required for zoneinfo to work

from config import Config

config = Config()

# Load API keys and IDs from the configuration file
NOTION_API_KEY = config.get_key("NOTION_API")
DATABASE_ID = config.get_key("DATABASE_ID")

# Google Calendar API scope
SCOPES = config.get_key("SCOPES")  # Allows read and write access to Google Calendar

# Initialize Notion API client
notion = Client(auth=NOTION_API_KEY)


# Google Calendar service initialization
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


# Get existing events from Google Calendar
def get_existing_events():
    service = google_calendar_service()
    events_result = service.events().list(calendarId='primary', maxResults=50, singleEvents=True,
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])

    existing_events = []
    for event in events:
        name = event.get('summary', 'No Name')
        date = event['start'].get('dateTime', event['start'].get('date'))
        event_id = event.get('id')
        existing_events.append({'name': name, 'date': date, 'id': event_id})

    return existing_events


# Get events data from Notion
def get_notion_data():
    results = notion.databases.query(database_id=DATABASE_ID)
    events = []

    for page in results["results"]:
        properties = page["properties"]

        name = "Unnamed Event"
        if "Name" in properties and properties["Name"]["title"]:
            name = properties["Name"]["title"][0]["text"]["content"]

        date = None
        if "Date" in properties and properties["Date"]["date"] is not None:
            date = properties["Date"]["date"]["start"]

        if date:
            events.append({"name": name, "date": date})

    return events


# Add events to Google Calendar, skipping past events
def add_event_to_google_calendar(event):
    event_start = datetime.datetime.fromisoformat(event['date']).date()

    # Ignore past events
    today = datetime.datetime.now(ZoneInfo("UTC")).date()
    if event_start < today:
        print(f"(APP) Skipping past event: {event['name']}")
        return

    existing_events = get_existing_events()

    # Check if event already exists in Google Calendar
    if any(existing_event['name'] == event['name'] for existing_event in existing_events):
        print(f"(APP) Event '{event['name']}' already exists. Skipping...")
        return

    service = google_calendar_service()
    event_end = event_start + datetime.timedelta(hours=1)

    # Create event body to add to Google Calendar
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

    # Insert event into Google Calendar
    service.events().insert(calendarId='primary', body=event_body).execute()
    print(f"(APP) Event '{event['name']}' has been added to Google Calendar.")


# Delete past events from Google Calendar
def delete_past_events():
    service = google_calendar_service()
    existing_events = get_existing_events()

    today = datetime.datetime.now(ZoneInfo("UTC")).date()

    # Delete past events from Google Calendar
    for event in existing_events:
        event_date = datetime.datetime.fromisoformat(event['date'].replace('Z', '+00:00')).date()
        if event_date < today:
            try:
                service.events().delete(calendarId='primary', eventId=event['id']).execute()
                print(f"(APP) Deleted past event: {event['name']}")
            except Exception as e:
                print(f"(APP) Error deleting event {event['name']}: {e}")


# Delete events that are no longer present in Notion
def delete_events_not_in_notion():
    service = google_calendar_service()
    existing_google_events = get_existing_events()

    notion_events = get_notion_data()

    # Delete events from Google Calendar that are not in Notion
    for event in existing_google_events:
        event_in_notion = False
        for notion_event in notion_events:
            if event['name'] == notion_event['name']:
                event_in_notion = True
                break

        # If event is not found in Notion, delete it from Google Calendar
        if not event_in_notion:
            try:
                service.events().delete(calendarId='primary', eventId=event['id']).execute()
                print(f"(APP) Deleted event from Google Calendar: {event['name']}")
            except Exception as e:
                print(f"(APP) Error deleting event {event['name']}: {e}")


# Main execution to delete past events and add new ones
delete_past_events()

# Add events from Notion to Google Calendar
events = get_notion_data()
for event in events:
    add_event_to_google_calendar(event)

# Delete events from Google Calendar that are no longer present in Notion
delete_events_not_in_notion()
