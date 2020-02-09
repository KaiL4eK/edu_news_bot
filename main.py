import logging
import os

import yaml
from telegram.ext import Updater, CommandHandler

# Enabling logging
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

TOKEN = os.environ.get('API_KEY')

def cmd_start(update, context):
    logger.info("User {} started bot".format(context.user_data))
    context.bot.send_message(chat_id=update.effective_chat.id, text="Hello from Python!")


def run(updater):
    PORT = int(os.environ.get("PORT", "8443"))
    HEROKU_APP_NAME = os.environ.get("HEROKU_APP_NAME")

    updater.start_webhook(listen="0.0.0.0",
                          port=PORT,
                          url_path=TOKEN)
    updater.bot.set_webhook(
        "https://{}.herokuapp.com/{}".format(HEROKU_APP_NAME, TOKEN))


def main():
    updater = Updater(token=TOKEN, use_context=True)
    dp = updater.dispatcher

    # dp.add_handler(CommandHandler('news', cmd_start))

    dp.add_handler(CommandHandler("start", cmd_start))

    run(updater)


if __name__ == '__main__':
    main()
