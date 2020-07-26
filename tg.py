import telebot

token = '723314573:AAH5-onyzwyA1fMDnk73GLBQ7sE2a2j_qD4'

bot = telebot.TeleBot(token=token)


@bot.message_handler(commands=['start', 'help', 'vasya'])
def send_welcome(message):
    bot.reply_to(message, "Hello papagena! Tu le bella comme le papaya!")


@bot.message_handler(func=lambda m: True)
def echo_all(message):

    if message.text == 'banana':
        bot.reply_to(message, 'BBANANAAA!!!1')
    else:
        bot.send_message(message.chat.id, message.text)


print('Start pooling...')
bot.polling()
