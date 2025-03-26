import os
import datetime
import pickle
import sys
import time

import google
import googleapiclient
from notion_client import Client
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from zoneinfo import ZoneInfo
import tzdata  # Required for zoneinfo to work

from config import Config

config = Config()

# Load API keys and IDs from the configuration file
NOTION_API_KEY = config.get_key("NOTION_API")
DATABASE_ID = config.get_key("DATABASE_ID")
SCOPES = config.get_key("SCOPES")  # Google Calendar API scope

# Initialize Notion API client
notion = Client(auth=NOTION_API_KEY)

def retry_on_failure(func, retries=3, wait=5):
    """
    Retries a function if it fails due to an authentication error.
    :param func: The function to execute.
    :param retries: Number of times to retry.
    :param wait: Time in seconds to wait before retrying.
    """
    for attempt in range(retries):
        try:
            return func()
        except RefreshError as e:
            print(f"(APP) Authentication error: {e}. Retrying {attempt + 1}/{retries}...")
            time.sleep(wait)
    print("(APP) Failed after multiple attempts.")
    return None

def google_calendar_service():
    """Authenticate and return the Google Calendar API service."""
    creds = None
    token_path = "token.pickle"

    # Load existing credentials if available
    if os.path.exists(token_path):
        with open(token_path, "rb") as token:
            creds = pickle.load(token)

    # Refresh or get new credentials if necessary
    if not creds or not creds.valid:
        try:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
                creds = flow.run_local_server(port=0)

            # Save the credentials for future use
            with open(token_path, "wb") as token:
                pickle.dump(creds, token)

        except google.auth.exceptions.RefreshError as e:
            print(f"(APP) ⚠️ Google Auth Error: {e}")
            print("(APP) 🔄 Deleting 'token.pickle' and retrying authentication.")
            if os.path.exists(token_path):
                os.remove(token_path)
            return google_calendar_service()

    return build("calendar", "v3", credentials=creds)

def get_existing_events():
    """ Retrieves existing events from Google Calendar. """
    service = retry_on_failure(google_calendar_service)
    if service is None:
        return []
    events_result = service.events().list(calendarId='primary', maxResults=50, singleEvents=True,
                                          orderBy='startTime').execute()
    return [
        {'name': event.get('summary', 'No Name'), 'date': event['start'].get('dateTime', event['start'].get('date')), 'id': event.get('id')}
        for event in events_result.get('items', [])
    ]

def delete_past_events():
    """ Deletes past events from Google Calendar. """
    service = retry_on_failure(google_calendar_service)
    if service is None:
        return
    existing_events = get_existing_events()
    today = datetime.datetime.now(ZoneInfo("UTC")).date()
    for event in existing_events:
        event_date = datetime.datetime.fromisoformat(event['date'].replace('Z', '+00:00')).date()
        if event_date < today:
            try:
                service.events().delete(calendarId='primary', eventId=event['id']).execute()
                print(f"(APP) Deleted past event: {event['name']}")
            except Exception as e:
                print(f"(APP) Error deleting event {event['name']}: {e}")

def delete_events_not_in_notion():
    """ Deletes events from Google Calendar that are no longer in Notion. """
    service = retry_on_failure(google_calendar_service)
    if service is None:
        return
    existing_google_events = get_existing_events()
    notion_events = get_notion_data()
    for event in existing_google_events:
        if not any(notion_event['name'] == event['name'] for notion_event in notion_events):
            try:
                service.events().delete(calendarId='primary', eventId=event['id']).execute()
                print(f"(APP) Deleted event from Google Calendar: {event['name']}")
            except Exception as e:
                print(f"(APP) Error deleting event {event['name']}: {e}")

def get_notion_data():
    """ Fetches events from Notion database. """
    results = notion.databases.query(database_id=DATABASE_ID)
    return [
        {
            "name": properties["Name"]["title"][0]["text"]["content"] if "Name" in properties and properties["Name"]["title"] else "Unnamed Event",
            "date": properties["Date"]["date"]["start"] if "Date" in properties and properties["Date"]["date"] else None
        }
        for properties in (page["properties"] for page in results["results"]) if properties["Date"]["date"] is not None
    ]

def add_event_to_google_calendar(event):
    """ Adds new events from Notion to Google Calendar. """
    try:
        event_start = datetime.datetime.fromisoformat(event['date'])
        today = datetime.datetime.now(ZoneInfo("UTC"))

        # If event is in the past, skip it
        if event_start.date() < today.date():
            print(f"(APP) Skipping past event: {event['name']}")
            return

        existing_events = get_existing_events()
        if any(existing_event['name'] == event['name'] for existing_event in existing_events):
            print(f"(APP) Event '{event['name']}' already exists. Skipping...")
            return

        service = retry_on_failure(google_calendar_service)
        if service is None:
            return

        event_body = {
            'summary': event['name'],
            'start': {'dateTime': event_start.isoformat(), 'timeZone': 'UTC'},
            'end': {'dateTime': (event_start + datetime.timedelta(hours=1)).isoformat(), 'timeZone': 'UTC'},
        }

        response = service.events().insert(calendarId='primary', body=event_body).execute()
        print(f"(APP) Event '{event['name']}' has been added to Google Calendar.")

    except ValueError as ve:
        print(f"(APP) ValueError: {ve} - Check if the event date format is correct.")
    except googleapiclient.errors.HttpError as he:
        print(f"(APP) Google Calendar API Error: {he}")
    except Exception as e:
        print(f"(APP) Unexpected error: {e}")


def main():
    """ Main execution function. """
    delete_past_events()
    for event in get_notion_data():
        add_event_to_google_calendar(event)
    delete_events_not_in_notion()

if __name__ == "__main__":
    main()