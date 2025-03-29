# Job Scraper Telegram Bot

A Telegram bot that scrapes job postings from websites and notifies users based on their qualification preferences.

## Features

* Interactive commands: `/start`, `/help`, `/categories`, `/getjobs`
* Qualification-based job filtering (Diploma, BCA, MCA, B.Tech, M.Tech, B.Sc, M.Sc, BA, MA, MBA/PGDM, B.Com, M.Com, B.Ed, M.Ed, LLB, LLM, MBBS, BDS, MS/MD, BAMS, BHMS, BUMS, B.Pharma, M.Pharma, D.Pharma, BPEd, MPEd, B.Lib, M.Lib, BSW, MSW, CA, ICWA, CS, ITI, 12TH, 10TH, MCA, GNM, ANM, DMLT, MLT, DNB, M.Phil/Ph.D, All.)
* Shows only jobs posted in the last 24 hours
* Auto-deletion of messages after 30 minutes
* User preference saving

## Setup

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create a `config.json` file with the following structure:
   ```json
   {  "telegram_bot_token": "YOUR_BOT_TOKEN",  "target_url": "https://www.freejobalert.com/latest-notifications/",  "date_format": "%d-%m-%Y",  "lookback_hours": 24}
   ```
4. Run the bot: `python main.py`

## Usage

1. Start the bot with `/start`
2. Click on "Show Categories" to view available qualification categories
3. Select a category to see relevant job postings
4. Use `/getjobs` to quickly check new jobs with your saved preference

## Deployment

This bot can be deployed on Railway.app:

1. Push code to GitHub
2. Connect Railway to your GitHub repo
3. Set the environment variables
4. Set the start command to `python main.py`

## License

MIT
