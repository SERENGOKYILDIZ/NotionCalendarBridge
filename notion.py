from notion_client import Client
from config import Config

config = Config()

# Notion API Key and Database ID
NOTION_API_KEY = config.get_key("NOTION_API")
DATABASE_ID = config.get_key("DATABASE_ID")

notion = Client(auth=NOTION_API_KEY)


def get_notion_data():
    # Query the database
    results = notion.databases.query(database_id=DATABASE_ID)
    events = []
    # Process and print the retrieved data
    for page in results["results"]:
        properties = page["properties"]
        # Retrieve Name and Date fields

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


# Fetch and print the data
events = get_notion_data()
for event in events:
    print(f"Event: {event["name"]}, Date: {event["date"]}")
