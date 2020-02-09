import logging
import os

import yaml
from telegram.ext import Updater, CommandHandler

# Enabling logging
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

TOKEN = os.environ.get('API_KEY')

def cmd_start(bot, update):
    logger.info("User {} started bot".format(update.effective_user["id"]))
    update.message.reply_text("Hello from Python!")


def run(updater):
    PORT = int(os.environ.get("PORT", "8443"))
    HEROKU_APP_NAME = os.environ.get("HEROKU_APP_NAME")

    updater.start_webhook(listen="0.0.0.0",
                          port=PORT,
                          url_path=TOKEN)
    updater.bot.set_webhook(
        "https://{}.herokuapp.com/{}".format(HEROKU_APP_NAME, TOKEN))


def main():

    with open('token.yaml') as f:
        data = yaml.load(f, Loader=yaml.FullLoader)

    updater = Updater(token=TOKEN, use_context=True)
    dp = updater.dispatcher

    # dp.add_handler(CommandHandler('news', cmd_start))

    dp.add_handler(CommandHandler("start", cmd_start))

    run(updater)


if __name__ == '__main__':
    main()
