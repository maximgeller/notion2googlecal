from __future__ import print_function
import datetime
import pickle
import os.path
import os
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from notion.client import NotionClient
from notion.collection import NotionDate
import re
import os
from os.path import join, dirname
from dotenv import load_dotenv

load_dotenv()

if os.path.exists('token.pickle'):
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
else:
    creds = None

def authenticate():
    global creds

    ###TODO: put the name of your credentials file here (it's probably credentials.json)
    credentials_file = "credentials.json" 

    SCOPES = ['https://www.googleapis.com/auth/calendar']

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        # Saves the credentials for future runs
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    main("request")

def main(request):
    global creds

    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    ###TODO: setup vars
    notion_token = os.getenv('NOTION_TOKEN')
    notion_cal = os.getenv('NOTION_CALENDAR')
    timezone = os.getenv('TIMEZONE')
    # os.environ["TZ"] = os.getenv('TIMEZONE') # ensures synchronized timezone
    calendar_id = os.getenv('CALENDAR_ID')

    # Call Google Calendar
    service = build('calendar', 'v3', credentials=creds)

    events_result = service.events().list(calendarId=calendar_id, 
    singleEvents=True, orderBy='updated').execute()

    events = events_result.get('items', [])

    for result in events:
        if 'description' not in result:
            result["description"] = ""

    google_event_list = [(event["summary"], event["id"], event["updated"], 
                          event["start"], event["end"], event["description"]) 
                        for event in events]

    # Call the Notion API
    client = NotionClient(token_v2=notion_token)
    calendar = client.get_collection_view(notion_cal)

    # Grab events in Notion cal
    notion_events = calendar.collection.get_rows()
    for i in notion_events:
        # consolidate notion event data into variables - used later to construct events pushed to google

        name = i.name
        identifier = i.id.replace("-","1") # cannot use dashes in ID so we replace them with 1's

        notion_start = i.date.start
        start = str(notion_start).replace(" ", "T")
        last_edited_notion = str(i.last_edited).replace(" ", "T") + "Z"
        
        notion_end = i.date.end
        end = str(notion_end).replace(" ", "T")
        if " " not in str(notion_end): # if it's just a date without a time
            end = str(notion_end + datetime.timedelta(days=1)) if notion_end != None else str(notion_end)
        else: # if the exact end time is also included
            end = str(notion_end).replace(" ", "T") 
            
        try:
            ###TODO: Put your other event properties in here and set them to be blank in except in case they're not found
            description = i.url
        except: 
            description = ""

        all_events = service.events().list(calendarId=calendar_id, 
                                           showDeleted=True, 
                                           maxResults=2500).execute() 
        all_events = all_events.get('items', [])
        total_event_list = [(event["id"], event["status"]) for event in all_events]

        try:
            # check for events deleted from gcal
            for event in total_event_list:
                if event[0] == identifier and event[1] == "cancelled":
                    # delete event from notion since event has been deleted from google
                    i.remove()
                    raise Exception

            for google_event in google_event_list:
                last_edited_google = datetime.datetime.strptime(google_event[2], "%Y-%m-%dT%H:%M:%S.%fZ")
                if google_event[1] == identifier:
                    # update events in notion if they were more recently edited in google
                    if last_edited_google > i.last_edited: 
                        i.name = google_event[0]
                            # print(google_event[6].entryPoints.uri)
                        if 'entryPoints' in google_event[6]:
                            print(google_event[6].entryPoints.uri)
                            # i.link = google_event[6][0]["uri"]
                        # i.url = google_event[5]
                        # determine if we need date or datetime object for start and end times
                        # we construct a NotionDate object to use
                        try:
                            updated_start = re.sub(r"-[0-9]{2}:[0-9]{2}$", "", str(google_event[3]["dateTime"]).replace("T", " "))
                            updated_start = datetime.datetime.strptime(updated_start[:-3], r"%Y-%m-%d %H:%M")
                            new_date = NotionDate(updated_start)
                            # i.date = new_date
                        except:
                            updated_start = datetime.datetime.strptime(google_event[3]["date"], r"%Y-%m-%d")
                            updated_start = datetime.date(updated_start.year, updated_start.month, updated_start.day)
                            new_date = NotionDate(updated_start)
                            # i.date = new_date
                        # the start date is created, so now we just set the end using the NotionDate object already created
                        try:
                            updated_end = re.sub(r"-[0-9]{2}:[0-9]{2}$", "", str(google_event[4]["dateTime"]).replace("T", " "))
                            updated_end = datetime.datetime.strptime(updated_end[:-3], r"%Y-%m-%d %H:%M")
                            new_date.end = updated_end
                            i.date = new_date
                        except:
                            updated_end = (datetime.datetime.strptime(google_event[4]["date"], r"%Y-%m-%d")).date()
                            if updated_end == updated_start:
                                # if an event in Notion doesn't have an end date, it's treated as an all day event on Google
                                # so Notion just wants it to have "None" for the end
                                new_date.end = "None" 
                            else:
                                # this is what we want to run when an event starts and ends on different days!
                                print(f"changing end date for more recently edited in google: {i.name}")
                                updated_end = (updated_end - datetime.timedelta(days=1)).date()
                                new_date.end = updated_end
                            i.date = new_date
                    
                        raise Exception

        except Exception:
            # when event gets updated or deleted, we don't want the event to be re-added to google cal
            # so we skip to the next iteration of the loop i.e. the next notion event
            continue

        else:
            # create event to add to gcal
            if ("T" in start) and ("T" in end): 
            # case 1: specified start date & time and end date & time (ideal case)
                event = {
                    "end": {
                        "dateTime": end,
                        "timeZone": timezone
                    },
                    "start": {
                        "dateTime": start,
                        "timeZone": timezone
                    },
                    "description": description,
                    "summary": name,
                    "id": identifier
                }
            elif "T" in start:
            # case 2: specified start date & time and no end date & time (reminder)
                event = {
                    "end": {
                        "dateTime": start,
                        "timeZone": timezone
                    },
                    "start": {
                        "dateTime": start,
                        "timeZone": timezone
                    },
                    "description": description,
                    "summary": name,
                    "id": identifier
                }
            elif end == "None":
            #case 3: specified start date but no time (& no end)
                event = {
                    "end": {
                        "date": start,
                        "timeZone": timezone
                    },
                    "start": {
                        "date": start,
                        "timeZone": timezone
                    },
                    "description": description,
                    "summary": name,
                    "id": identifier
                }  
            else:
            #case 4: specified start and end dates (no times)
                event = {
                    "end": {
                        "date": end,
                        "timeZone": timezone
                    },
                    "start": {
                        "date": start,
                        "timeZone": timezone
                    },
                    "description": description,
                    "summary": name,
                    "id": identifier
                }
            try:
                # event is inserted into gcal if it's a new event
                event = service.events().insert(calendarId=calendar_id, body=event).execute()
            except:
                # otherwise the pre-existing event is updated with the new event body
                try:
                    event = service.events().update(calendarId=calendar_id, eventId=identifier, body=event).execute()
                except:
                    # the only way to end up here is by clearing your trash 
                    # (do not do because it eliminates Notion IDs from the usable pool)
                    #print(f"Please make a new event in notion for {name}, it won't work since you emptied your trash!")
                    continue
    
    # Get Google Events now to create on Notion Cal

    # Reformatting the Notion Id list to fit our format of replacing the '-' with '1'
    notion_id_list = [event.id for event in notion_events]
    for i in range(len(notion_id_list)):
        notion_id_list[i] = list(notion_id_list[i])
        notion_id_list[i][8] = "1"
        notion_id_list[i][13] = "1"
        notion_id_list[i][18] = "1"
        notion_id_list[i][23] = "1"
        notion_id_list[i] = "".join(notion_id_list[i])

    for google_event in google_event_list:
        # summary: 0
        # id: 1
        # updated time: 2
        # start: 3
        # end: 4 
        # description: 5 

        # check if an event has been deleted from notion
        if len(google_event[1]) == 36 and google_event[1] not in notion_id_list: # 36 = len of notion event id
            event = service.events().delete(calendarId=calendar_id, eventId=google_event[1]).execute()

        elif google_event[1] not in notion_id_list:
            # event has been created in gcal, add the event to notion
            # note: this only works if there only exists one view for your notion database
            notion_event = calendar.collection.add_row() 
            notion_event.name = google_event[0]

            ###TODO: set your custom parameters
            notion_event.url = google_event[5]

            # Rebuilding the date the same way as before
            try:
                updated_start = re.sub(r"-[0-9]{2}:[0-9]{2}$", "", str(google_event[3]["dateTime"]).replace("T", " "))
                updated_start = datetime.datetime.strptime(updated_start[:-3], r"%Y-%m-%d %H:%M")
                new_date = NotionDate(updated_start)
                # notion_event.date = new_date
            except:
                updated_start = datetime.datetime.strptime(google_event[3]["date"], r"%Y-%m-%d")
                updated_start = datetime.date(updated_start.year, updated_start.month, updated_start.day)
                new_date = NotionDate(updated_start)
                # notion_event.date = new_date

            try:
                updated_end = re.sub(r"-[0-9]{2}:[0-9]{2}$", "", str(google_event[4]["dateTime"]).replace("T", " "))
                updated_end = datetime.datetime.strptime(updated_end[:-3], r"%Y-%m-%d %H:%M")
                new_date.end = updated_end
                notion_event.date = new_date
            except:
                updated_end = datetime.datetime.strptime(google_event[4]["date"], r"%Y-%m-%d")

                if updated_end == updated_start:
                    new_date.end = "None"
                else:
                    # this is what we want to run when an event starts and ends on different days!
                    print(f"changing end date for creating on notion cal: {notion_event.name}")
                    updated_end = (updated_end - datetime.timedelta(days=1)).date()
                    new_date.end = updated_end
                notion_event.date = new_date
            
            # create Notion Id variable using the same method as before to handle usage of dashes
            notion_event_id = str(notion_event.id.replace("-","1")) 
            
            # retrieving the event body to overwrite with the ID we want to use (Notion's)
            event_body = service.events().get(calendarId=calendar_id, eventId=google_event[1]).execute()
            
            event_body["id"] = notion_event_id

            # iCalUID gets added by default, but we cannot add an event with both id & iCalUID
            del event_body["iCalUID"]

            # this unlinks recurring events
            if 'recurringEventId' in event_body:
                del event_body['recurringEventId']
            
            # we cannot update gcal event ID with one from notion, so we delete and reinsert events instead
            event = service.events().delete(calendarId=calendar_id, eventId=google_event[1]).execute()
            event = service.events().insert(calendarId=calendar_id, body=event_body).execute()
            
    return "Done"

if __name__ == '__main__':
    if os.path.exists('token.pickle'):
        main("request")
    else:
        authenticate()
