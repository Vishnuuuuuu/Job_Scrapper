import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List

import requests
from bs4 import BeautifulSoup
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ContextTypes)

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class JobScraperBot:
    def __init__(self, config_path='config.json'):
        # Load configuration
        self.load_config(config_path)
        
        # Track user preferences (in memory)
        self.user_preferences = {}
        
        # Available job categories
        self.categories = [
            "Diploma", "BCA", "MCA", "B.Tech", "M.Tech", 
            "B.Sc", "M.Sc", "BA", "MA", "All"
        ]

    def load_config(self, config_path):
        """Load configuration from JSON file or environment variables"""
        # First check for environment variables (Railway.app will use these)
        if 'TELEGRAM_BOT_TOKEN' in os.environ:
            self.config = {
                "telegram_bot_token": os.environ['TELEGRAM_BOT_TOKEN'],
                "target_url": os.environ.get('TARGET_URL', "https://www.freejobalert.com/latest-notifications/"),
                "date_format": os.environ.get('DATE_FORMAT', "%d-%m-%Y"),
                "lookback_hours": int(os.environ.get('LOOKBACK_HOURS', 24))
            }
        else:
            # Load from config.json as fallback
            try:
                with open(config_path, 'r') as f:
                    self.config = json.load(f)
            except FileNotFoundError:
                # Create default config if not found
                self.config = {
                    "telegram_bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
                    "target_url": "https://www.freejobalert.com/latest-notifications/",
                    "date_format": "%d-%m-%Y",
                    "lookback_hours": 24
                }
                with open(config_path, 'w') as f:
                    json.dump(self.config, f, indent=4)

    async def scrape_jobs(self, category: str = "All") -> List[Dict]:
        """
        Scrape job notifications from the website
        
        :param category: Job qualification category to filter
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
            
            # Calculate the cutoff time (24 hours ago by default)
            lookback_hours = self.config.get('lookback_hours', 24)
            cutoff_time = datetime.now() - timedelta(hours=lookback_hours)
            
            # Process and filter jobs
            current_jobs = []
            for row in job_rows:
                job_details = self._extract_job_details(row)
                
                # Apply category filter if not "All"
                if category.lower() == "all" or category.lower() in job_details['qualifications'].lower():
                    
                    # Apply time filter
                    if self._is_recent(job_details['date'], cutoff_time):
                        current_jobs.append(job_details)
            
            return current_jobs
        except requests.RequestException as e:
            logger.error(f"Error fetching webpage: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error during scraping: {e}")
            return []

    def _extract_job_details(self, row) -> Dict:
        """Extract details from a single job row"""
        try:
            return {
                'date': row.find('td', class_='latcpb').text.strip(),
                'organization': row.find('td', class_='latcr').text.strip(),
                'position': row.find('td', class_='latceb').text.strip(),
                'qualifications': row.find('td', class_='latcqb').text.strip(),
                'last_date': row.find('td', class_='latclb').text.strip(),
                'link': row.find('a')['href'] if row.find('a') else None
            }
        except AttributeError as e:
            logger.error(f"Error extracting job details: {e}")
            # Return empty dict with default values if extraction fails
            return {
                'date': 'Unknown',
                'organization': 'Unknown',
                'position': 'Unknown',
                'qualifications': 'Unknown',
                'last_date': 'Unknown',
                'link': None
            }

    def _is_recent(self, date_str: str, cutoff_time: datetime) -> bool:
        """
        Check if the given date string is more recent than the cutoff time
        
        :param date_str: Date string from job posting
        :param cutoff_time: Datetime object representing the cutoff time
        :return: Boolean indicating if the date is recent
        """
        try:
            # Adjust the parsing based on the actual date format on the website
            job_date = datetime.strptime(date_str.strip(), self.config.get('date_format', '%d-%m-%Y'))
            return job_date >= cutoff_time
        except Exception as e:
            logger.error(f"Error parsing date: {e}")
            # If there's an error parsing the date, include the job to be safe
            return True

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a message when the command /start is issued."""
        user = update.effective_user
        welcome_text = (
            f"Hello {user.first_name}! 👋\n\n"
            f"I'm your Job Alert Bot. I can help you find the latest job postings "
            f"based on your qualification.\n\n"
            f"Use the menu below to select your qualification category:"
        )
        
        # Create category selection keyboard
        keyboard = []
        row = []
        for i, category in enumerate(self.categories):
            row.append(InlineKeyboardButton(category, callback_data=f"category_{category}"))
            if (i + 1) % 3 == 0 or i == len(self.categories) - 1:
                keyboard.append(row)
                row = []
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a message when the command /help is issued."""
        help_text = (
            "🔍 *Job Scraper Bot Help* 🔍\n\n"
            "Available commands:\n"
            "/start - Start the bot and show qualification categories\n"
            "/help - Show this help message\n"
            "/categories - Show available qualification categories\n"
            "/getjobs - Check for new jobs with your saved preference\n\n"
            "How to use:\n"
            "1. Use /start to begin\n"
            "2. Select your qualification from the menu\n"
            "3. The bot will show you jobs posted in the last 24 hours\n"
            "4. Use /categories anytime to change your selection\n"
            "5. Use /getjobs to quickly check for new jobs with your saved preference"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def categories_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show available categories when /categories command is issued."""
        categories_text = "Please select your qualification category:"
        
        # Create category selection keyboard
        keyboard = []
        row = []
        for i, category in enumerate(self.categories):
            row.append(InlineKeyboardButton(category, callback_data=f"category_{category}"))
            if (i + 1) % 3 == 0 or i == len(self.categories) - 1:
                keyboard.append(row)
                row = []
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(categories_text, reply_markup=reply_markup)

    async def getjobs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get jobs with saved preference when /getjobs command is issued."""
        user_id = update.effective_user.id
        
        if user_id in self.user_preferences:
            category = self.user_preferences[user_id]
            await update.message.reply_text(f"Searching for {category} jobs posted in the last 24 hours...")
            
            # Scrape jobs for the saved category
            jobs = await self.scrape_jobs(category)
            await self._send_job_results(update, context, category, jobs)
        else:
            # No saved preference, show categories
            await update.message.reply_text(
                "You don't have a saved preference yet. Please select a category:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(category, callback_data=f"category_{category}") 
                     for category in self.categories[:3]],
                    [InlineKeyboardButton(category, callback_data=f"category_{category}") 
                     for category in self.categories[3:6]],
                    [InlineKeyboardButton(category, callback_data=f"category_{category}") 
                     for category in self.categories[6:]]
                ])
            )

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle button presses."""
        query = update.callback_query
        await query.answer()
        
        # Get the category from callback data
        if query.data.startswith("category_"):
            category = query.data.replace("category_", "")
            
            # Save user preference
            user_id = update.effective_user.id
            self.user_preferences[user_id] = category
            
            await query.edit_message_text(text=f"Searching for {category} jobs posted in the last 24 hours...")
            
            # Scrape jobs for the selected category
            jobs = await self.scrape_jobs(category)
            await self._send_job_results(update, context, category, jobs)
            
        # Handle "Search Again" button
        elif query.data == "search_again":
            await self.categories_command(update, context)

    async def _send_job_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category: str, jobs: List[Dict]) -> None:
        """Send job results to the user."""
        if not jobs:
            try:
                await update.callback_query.edit_message_text(
                    text=f"No {category} jobs found in the last 24 hours. Try another category.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("Search Again", callback_data="search_again")
                    ]])
                )
            except AttributeError:
                # If this was called from a command, not a callback
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"No {category} jobs found in the last 24 hours. Try another category.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("Search Again", callback_data="search_again")
                    ]])
                )
        else:
            try:
                # Edit the original message
                await update.callback_query.edit_message_text(
                    text=f"Found {len(jobs)} {category} jobs in the last 24 hours. Sending details..."
                )
            except AttributeError:
                # If this was called from a command, not a callback
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Found {len(jobs)} {category} jobs in the last 24 hours. Sending details..."
                )
            
            # Send each job as a separate message
            for job in jobs:
                message = (
                    f"🚨 *Job Alert: {category}* 🚨\n\n"
                    f"*Organization:* {job['organization']}\n"
                    f"*Position:* {job['position']}\n"
                    f"*Qualifications:* {job['qualifications']}\n"
                    f"*Posted Date:* {job['date']}\n"
                    f"*Last Date:* {job['last_date']}\n"
                )
                
                # Add apply link if available
                if job['link']:
                    message += f"*Apply Here:* {job['link']}"
                
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message,
                    parse_mode='Markdown'
                )
            
            # Send a button to search again
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Would you like to search for jobs in another category?",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("Search Again", callback_data="search_again")
                ]])
            )

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors."""
        logger.error(f"Error: {context.error}")
        
        # Send error message to user
        if update:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="An error occurred. Please try again later."
            )


def main():
    """Start the bot."""
    # Create the bot
    bot = JobScraperBot()
    
    # Create the Application and pass it your bot's token
    application = Application.builder().token(bot.config["telegram_bot_token"]).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(CommandHandler("help", bot.help_command))
    application.add_handler(CommandHandler("categories", bot.categories_command))
    application.add_handler(CommandHandler("getjobs", bot.getjobs_command))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(bot.button_handler))
    
    # Add error handler
    application.add_error_handler(bot.error_handler)

    # Run the bot
    logger.info("Bot is running!")
    application.run_polling()

if __name__ == "__main__":
    main()