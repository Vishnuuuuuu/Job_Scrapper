import telegram

# Replace with your actual bot token
bot = telegram.Bot(token='7589636517:AAEvzthvfqIaXJVKq9ZmO_0AMxLazU7kJfg')

# This will print updates, including your chat ID
updates = bot.get_updates()
for update in updates:
    print(update.message.chat_id)