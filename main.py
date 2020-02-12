import logging
import os

from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import news_parser as news

# Enabling logging
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

TOKEN = os.environ.get('API_KEY')

stream = news.StreamingNews(
    sources=[
        news.GovNewsParser()
    ]
)


def cmd_start(update, context):
    logger.info('User {} started bot'.format(context.user_data))
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Hello from Python!")

more_news_keyboard = [[
    InlineKeyboardButton('Еще новостей!', callback_data='more_news')
]]

def cb_button(update, context):
    query = update.callback_query
    query.edit_message_reply_markup(InlineKeyboardMarkup([[]]))

    reply_markup = InlineKeyboardMarkup(more_news_keyboard)

    try:
        link = stream.get_last_fresh_news(update.effective_chat.id)
    except:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Что-то пошло не так =( Спроси лешу =)")
        return

    if link is None:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="На сегодня новые новости закончились, хорошего дня! =)")
        return

    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Свеженькое для вас: {}".format(link),
                             reply_markup=reply_markup)


def cmd_news(update, context):
    reply_markup = InlineKeyboardMarkup(more_news_keyboard)

    try:
        link = stream.get_last_fresh_news(update.effective_chat.id)
    except:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Что-то пошло не так =( Спроси лешу =)")
        return

    if link is None:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="На сегодня новые новости закончились, хорошего дня! =)")
        return

    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Свеженькое для вас: {}".format(link),
                             reply_markup=reply_markup)


def run(updater):
    MODE = os.environ.get("MODE", 'dev')

    if MODE == 'prod':
        PORT = int(os.environ.get("PORT", "8443"))
        HEROKU_APP_NAME = os.environ.get("HEROKU_APP_NAME")

        updater.start_webhook(listen="0.0.0.0",
                              port=PORT,
                              url_path=TOKEN)
        updater.bot.set_webhook(
            "https://{}.herokuapp.com/{}".format(HEROKU_APP_NAME, TOKEN))
    else:
        updater.start_polling()
        updater.idle()


def main():
    updater = Updater(token=TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('news', cmd_news))
    dp.add_handler(CommandHandler("start", cmd_start))
    dp.add_handler(CallbackQueryHandler(cb_button))

    run(updater)


if __name__ == '__main__':
    main()
