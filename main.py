import telebot
from dialog import Dialog

token = '111111111:AAH5xxxxxxxxxxxxxxxxxxxxxxxxxxxxqD4'

bot = telebot.TeleBot(token=token)

print(f'Your token is: {token}')
print('Start pooling...')

dialog = Dialog(bot, {
    'voc': 'voc.yaml',
})

dialog.start()
