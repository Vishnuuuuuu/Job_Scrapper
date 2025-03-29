import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List

import requests
import telegram
from bs4 import BeautifulSoup


class JobScraper:
    def __init__(self, config_path='config.json'):
        # Load configuration
        self.load_config(config_path)
        
        # Initialize Telegram Bot
        self.bot = telegram.Bot(token=self.config['telegram_bot_token'])
        self.chat_id = self.config['telegram_chat_id']
        
        # Track previously scraped jobs
        self.previous_jobs = set()

    def load_config(self, config_path):
        """
        Load configuration from JSON file
        """
        with open(config_path, 'r') as f:
            self.config = json.load(f)

    def update_config(self, updates: Dict):
        """
        Dynamically update configuration
        
        :param updates: Dictionary of configuration updates
        """
        self.config.update(updates)
        
        # Save updated config
        with open('config.json', 'w') as f:
            json.dump(self.config, f, indent=4)

    def scrape_jobs(self) -> List[Dict]:
        """
        Scrape job notifications from the website
        
        :return: List of job dictionaries
        """
        try:
            # Add headers to mimic browser request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Fetch the webpage
            response = requests.get(self.config['target_url'], headers=headers)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all job rows
            job_rows = soup.find_all('tr', class_='lattrbord latoclr')
            
            # Get today's date in the format used by the website (if needed)
            today = datetime.now().strftime(self.config.get('date_format', '%d-%m-%Y'))
            
            # Process and filter jobs
            current_jobs = []
            for row in job_rows:
                job_details = self._extract_job_details(row)
                
                # Apply category filter (Diploma only)
                if self.config.get('category', 'Diploma').lower() in job_details['qualifications'].lower():
                    
                    # Apply date filter if enabled
                    if self.config.get('today_only', True):
                        # Compare the date (implement based on your site's date format)
                        if self._is_today(job_details['date']):
                            current_jobs.append(job_details)
                    else:
                        current_jobs.append(job_details)
            
            return current_jobs
        except requests.RequestException as e:
            print(f"Error fetching webpage: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error during scraping: {e}")
            return []

    def _extract_job_details(self, row) -> Dict:
        """
        Extract details from a single job row
        
        :param row: BeautifulSoup row element
        :return: Dictionary of job details
        """
        return {
            'date': row.find('td', class_='latcpb').text.strip(),
            'organization': row.find('td', class_='latcr').text.strip(),
            'position': row.find('td', class_='latceb').text.strip(),
            'qualifications': row.find('td', class_='latcqb').text.strip(),
            'last_date': row.find('td', class_='latclb').text.strip(),
            'link': row.find('a')['href'] if row.find('a') else None
        }

    def _is_today(self, date_str: str) -> bool:
        """
        Check if the given date string represents today's date
        
        :param date_str: Date string from job posting
        :return: Boolean indicating if the date is today
        """
        try:
            # Adjust the parsing based on the actual date format on the website
            job_date = datetime.strptime(date_str.strip(), self.config.get('date_format', '%d-%m-%Y'))
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            return job_date.date() == today.date()
        except Exception as e:
            print(f"Error parsing date: {e}")
            # If there's an error parsing the date, include the job to be safe
            return True

    async def send_telegram_notification(self, jobs: List[Dict]):
        """
        Send Telegram notifications for new jobs
        
        :param jobs: List of new job dictionaries
        """
        if not jobs:
            if self.config.get('notify_when_no_jobs', False):
                await self.bot.send_message(
                    chat_id=self.chat_id, 
                    text="No new Diploma jobs found today."
                )
            return
            
        for job in jobs:
            # Avoid duplicate notifications
            job_hash = hash(frozenset(job.items()))
            if job_hash not in self.previous_jobs:
                message = (
                    f"🚨 New Diploma Job Alert! 🚨\n\n"
                    f"Organization: {job['organization']}\n"
                    f"Position: {job['position']}\n"
                    f"Qualifications: {job['qualifications']}\n"
                    f"Last Date: {job['last_date']}\n"
                    f"Apply Link: {job['link']}"
                )
                
                # Send message
                try:
                    await self.bot.send_message(
                        chat_id=self.chat_id, 
                        text=message
                    )
                    
                    # Track to prevent duplicates
                    self.previous_jobs.add(job_hash)
                except Exception as e:
                    print(f"Error sending Telegram message: {e}")

    async def run(self):
        """
        Main execution method to scrape and notify
        """
        try:
            # Scrape jobs
            new_jobs = self.scrape_jobs()
            
            # Send notifications
            await self.send_telegram_notification(new_jobs)
            
            # Log the run
            print(f"Scraper run completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Found {len(new_jobs)} new Diploma jobs today")
            
        except Exception as e:
            # Log or send error notification
            error_message = f"Scraping Error: {str(e)}"
            print(error_message)
            try:
                await self.bot.send_message(
                    chat_id=self.chat_id, 
                    text=error_message
                )
            except Exception as send_error:
                print(f"Could not send error notification: {send_error}")

# Updated configuration file (config.json)
example_config = {
    "telegram_bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
    "telegram_chat_id": "YOUR_CHAT_ID",
    "target_url": "https://www.freejobalert.com/latest-notifications/",
    "category": "Diploma",  # Focus on Diploma jobs only
    "today_only": True,     # Only fetch today's jobs
    "date_format": "%d-%m-%Y",  # Adjust based on your website's format
    "notify_when_no_jobs": True  # Send a notification even when no jobs found
}

# Main script to run
if __name__ == "__main__":
    scraper = JobScraper()
    asyncio.run(scraper.run())