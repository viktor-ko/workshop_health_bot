import vk_api
from vk_api.utils import get_random_id
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

token = 'c2c447bd523d8bf261d61e93bda9ccd6a918a3cd988aec9ee16d5d96fc875e10df35e331dcaa0d77b4e85'
group_id = '184695269'


def reply(bot, envelope):

    if envelope.obj.text == 'banana':
        bot.messages.send(
            user_id=envelope.obj.from_id,
            random_id=get_random_id(),
            message='BBANANAAA!!!1',
            reply_to=envelope.obj.id
        )
    elif envelope.obj.text in {'/start', '/help'}:
        bot.messages.send(
            user_id=envelope.obj.from_id,
            random_id=get_random_id(),
            message='Hello papagena! Tu le bella comme le papaya!')
    else:
        bot.messages.send(
            user_id=envelope.obj.from_id,
            random_id=get_random_id(),
            message=envelope.obj.text + ', блять!')


vk_session = vk_api.VkApi(token=token)
bot = vk_session.get_api()


long_poll = VkBotLongPoll(vk_session, group_id=group_id)

try:
    for envelope in long_poll.listen():
        if envelope.type in [
            VkBotEventType.MESSAGE_NEW,
        ]:
            reply(bot, envelope=envelope)
except Exception as e:
    print(e)

    long_poll.session.close()
    vk_session.http.close()
