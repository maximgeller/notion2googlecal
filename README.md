# Notion to Google Calendar Integration

This script utilizes the unofficial [Notion API](https://github.com/jamalex/notion-py) and the [Google Calendar API](https://developers.google.com/calendar) to sync a calendar directly between Notion and Google Calendar. Set this up as a cron job to have it sync changes between calendars automatically!
<br><br>

## Set-up the Script:

1. Clone the [github repo](notion://www.notion.so/new-title-23eff1430311409db97ee0f08972eef7) and open up `main.py`. In here, you'll find a list of set-up variables you'll want to provide values for: your Notion token (retrieved from a cookie), the URL of the Notion calendar you'd like to use, your timezone, and the calendar ID of the Google Calendar you want to use.
Here's how to get these things:

    a) **Notion token:**
    Open the notion workspace for the calendar you want to sync in your browser. Open the developer console using `Inspect`. Tab over to `Application` and select the `Cookies` sub-menu. Look for the cookie named `token_v2` and copy its value. In `main.py`, set `notion_token` equal to this value as a string.<br>
    b) **Notion calendar:**
    Navigate to the notion calendar you want to sync and copy the link. Make sure it's shareable so that it's viewable by anyone. In `main.py`, set `notion_cal` equal to this value as a string.<br>
    c) **Timezone:**
    Again in `main.py`, set `timezone` equal to the timezone of your Notion calendar. Format your timezone according to your timezone's `TZ database name`, found [here](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones).<br>
    d) **Google Calendar:**
    Navigate to the settings page for the google calendar that you have edit access to that you want to sync. Scroll down to the `Integrate calendar` section, and find the `Calendar ID`. In `main.py`, set `calendar_id` equal to this value as a string.<br>

2. In your Notion, open the menu bar (indicated by three dots in the top right corner of the calendar view. Click `properties`, and add a property titled `last edited` with an advanced type of `last edited time`.
3. Add any additional event properties you have in the script in the try-catch block around line 100 if you want to include extra things like location, description, etc.
4. Follow the first step of this [google calendar quickstart](https://developers.google.com/calendar/quickstart/python) by clicking `Enable the Google Calendar API`. Name your project and click `NEXT`. Select `Desktop App` to Configure your OAuth Client. Then, obtain your `credentials.json` file by clicking `DOWNLOAD CLIENT CONFIGURATION`. Add the file to your project workspace, and set the value of `credentials_file` to the name of this file as a string. You will need this in order to later authenticate your account and obtain your Google Calendar data.
5. Run the script locally on your computer. The first time this script is run, you will be taken through Google's authentication flow. Sign in with the account that owns the Google Calendar whose ID you used.

Your calendars should now be **sucessfully synced!** You can continue to run your script whenever you want the calendars to resync, or continue with setting up a cron job to have this process happen **automatically!**

<br>

## Set-up the Cron Job:

1. **Install Google Cloud Command Line Tools (skip if you already have)**

    You will need to initialize GCloud's SDK in order to deploy the script. [Download the SDK here and follow the instructions to initialize](https://cloud.google.com/sdk/docs/quickstarts). 

2. **Create a Cloud Function:**<br>
Navigate to [Google Cloud Platform](https://console.cloud.google.com/getting-started?ref=https:%2F%2Fwww.google.com%2F). On the dashboard for your new project, open `Go to APIs Overview`, and click `ENABLE APIS AND SERVICES`. Search for and enable the `Google Build API` and `Google Calendar API`. Next, navigate back to the API & Services home page, and into the `Credentials` tab. In the `Service Accounts` section, there should be an App Engine default service account already created. Copy the email address, go to `Settings and sharing` for the Google Calendar you want synced, and share the calendar with the service account, providing it permission to `Make changes`. <br><br>
Open the terminal on your computer and navigate to the folder the `main.py` script is located in. Run the following command in your terminal: `gcloud functions deploy main --trigger-http --runtime=python37 --project=INSERT_PROJECT_ID`, replacing `INSERT_PROJECT_ID` with your project's ID. This value should be available in the `Project info` section of your Google Cloud Platform Dashboard.
When the command runs, it should provide you the option to run *authenticated/allow unauthenticated*. Make sure to `allow unauthenticated`, and the function should take a few minutes to deploy to your Google Cloud Console.
Once it has successfully deployed, you can schedule it to run as often as you'd like!

3. **Schedule Cloud Function as a Cron Job:**
Again, open the menu bar on the left side of the page and navigate to `Cloud Scheduler` under `TOOLS`. Click `CREATE JOB`. <br><br>
a) Fill out the space for `Name`.<br>
b) Fill out the rule for `Frequency` according to how often you want the script to be run. We use "* * * * *" to indicate the cron job would run every minute.<br>
c) Fill out the space for `Timezone`. For our frequency, it didn't matter what the timezone was, but if you want your script to run at a more specific time (ie. everyday @ 3pm), consider this in selecting your timezone.<br>
d) Change `Target` to be `HTTP`.<br>
e) Insert the `URL` to send a request to. This is the `URL` that was returned from deploying the cloud function. <br>
f) Click `CREATE`.<br>
<br>It may take a few minutes to set-up, but the script should now automatically run according to the frequency rule you selected.<br><br>


## Warnings

1. **Timezones:** From testing, using `os.environ["TZ"]` does not work on windows computers. If you plan to use this calendar with people in other timezones, they must manually configure the timezone of the event that they add in the Notion calendar to **match the timezone** of the person who created the calendar. 
2. **Recurring Events:**
Syncing a calendar with recurring events will remove the recurrence rule property from events in google calendar. Since notion does not allow for specifying IDs, we are unable to maintain sync while also upholding the requirements for google calendar IDs and RecurringEventIDs. Syncing will still display all recurring and non-recurring events on your calendar, but will not maintain the recurrence rule property of recurring google calendar events.
<br><br>
## We Need Help!

This script is far from perfect, and we're trying to make the script as efficient as possible to minimize the rate at which Google Calendar's API is called as well as the number of times it needs to be called. 

Setting up the script as a cron job will cause a violation in the rate limit beyond a calendar of ~120 events, which is not a lot.
<!--stackedit_data:
eyJoaXN0b3J5IjpbODUzOTQ2NTk4LDkxMzA2MDQxNV19
-->
