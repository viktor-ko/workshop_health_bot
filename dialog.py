import yaml
import telebot
import random
import pymorphy2
from urllib.parse import urlparse


def is_url(url: str):
    '''
    Фцункция, определяющая является ли данная строка URL

    :param url: собственно, строка
    :return: булево True | False
    '''

    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


class Dialog(object):
    '''
    Класс, реализующий диалог чатбота
    '''

    def __init__(self, bot: telebot.TeleBot, config: dict) -> None:
        '''
        Конструктор класса диалога
        :param bot: объект бота pyTelegramBot
        :param config: словарь с конфигурацией
        '''

        super().__init__()

        self._bot = bot
        self._config = config.copy()
        self._voc = self._load_voc()

        # это пользовательские сессии
        self._sessions = self._load_sessions()

        # здесь мы определяем ноду по умолчанию, с которой будем начинать
        # и на которую будем переходить в случае ошибки диалога
        self._default_node = self._voc.get('default', 'begin')

        # это библиотека морфологии, она нам нужна для морфоанализа слов
        self.__morph = pymorphy2.MorphAnalyzer()

    def _load_sessions(self):
        '''
        Загружает пользовательские сессии. В данный момент это всего лишь пустой словарь
        :return: словарь сессий
        '''

        return dict()

    def _load_voc(self):
        '''
        Загружает словарь диалогов
        :return: словарь диалогов
        '''

        with open(self._config['voc'], 'r', encoding='utf-8') as f:
            return yaml.load(f, Loader=yaml.FullLoader)

    def _get_node(self, node_name):
        '''
        Возвращает ноду по имени
        :param node_name: имя ноды
        :return: нода
        '''

        return self._voc['nodes'][node_name]

    def _get_node_phrase(self, node_name, the_key='q'):
        '''
        Берет фразу ноды по указанному ключу

        :param node_name: имя ноды
        :param the_key: ключ, по умолчанию это q -- то есть текст вопроса ноды
        :return:
        '''
        node = self._get_node(node_name)
        phrase = node.get(the_key, None)

        # если фраз несколько, то берем на угад любую
        if isinstance(phrase, list):
            phrase = random.choice(phrase)

        return phrase

    def _get_node_answers(self, node_name):
        '''
        Возвращает ответы ноды
        :param node_name: имя ноды
        :return: список ответов
        '''

        node = self._get_node(node_name)
        answers = node['a']

        # если списка как такового нет, и сразу указан единственный ответ,
        # мы все равно превращаем его в список
        if not isinstance(answers, list):
            answers = [answers]

        return answers

    def _get_node_type(self, node_name):
        '''
        Возвращает тип ноды
        :param node_name: имя ноды
        :return: тип ноды, строка из вариантов { plain, variant }
        '''

        return self._get_node(node_name).get('type', 'plain')

    def _get_session(self, chat_id):
        '''
        Берет текущую сессию чата, или возвращает None если ее нет
        :param chat_id: идентификатор чата
        :return: сессия (редуцирована до имени текущей ноды)
        '''

        return self._sessions.get(chat_id, None)

    def _check_plain_node(self, message, node_name):
        '''
        Проверяет текстовый ответ пользователя и возвращает следующую ноду диалога
        :param message: сообщение pyTelegramBot
        :param node_name: имя ноды
        :return: имя следующей ноды или None
        '''

        answers = self._get_node_answers(node_name)
        message_words = message.text.split(' ')

        # берем каждый ответ в ноде
        for answer in answers:

            answer_words = answer['words']
            if not isinstance(answer_words, list):
                answer_words = [answer_words]

            # берем каждое слово в ответе ноды
            for aword in answer_words:

                # если мы находим квантор "любой ответ" то сразу же возвращаем goto этой ноды
                if aword == '*':
                    return answer['goto']

                # проверяем все слова в ответе пользователя
                for mword in message_words:
                    a_morphs = self.__morph.parse(aword.lower())
                    b_morphs = self.__morph.parse(mword.lower())

                    # берем все формы слова в ответе ноды
                    for aw in a_morphs:

                        # берем все формы слова в ответе пользователя
                        for bw in b_morphs:
                            # если слова совпали -- значит это тот самый ответ
                            if aw.normal_form == bw.normal_form:
                                return answer['goto']

        return None

    def _check_variant_node(self, message, data, node_name):
        '''
        Проверяет вариативный ответ пользователя (кнопки) и возвращает следующую ноду
        :param message: сообщение pyTelegramBot
        :param data: код кнопки
        :param node_name: имя текущей ноды
        :return: имя следующей ноды или None
        '''
        answers = self._get_node_answers(node_name)

        try:
            return answers[int(data)]['goto']
        except (AttributeError, IndexError, TypeError) as e:
            return None

    def _check_answer(self, message, data, current_node):
        '''
        Проверяет ответ пользователя
        :param message: сообщение pyTelegramBot
        :param data: код кнопки
        :param current_node: имя текущей ноды
        :return: имя следующей ноды или None
        '''

        # определяем тип ноды
        node_type = self._get_node_type(current_node)

        # если это ввод текста, то проверяем ввод текста
        if node_type == 'plain':
            return self._check_plain_node(message, current_node)

        # если это вариант, то проверяем по-своему
        elif node_type == 'variant':
            return self._check_variant_node(message, data, current_node)

        # в случае ошибки вернем None
        return None

    def _get_node_buttons(self, message, node_name, row_width=2):
        '''
        Создает клавиатуру с кнопками для ответа
        :param message: сообщение pyTelegramBot
        :param node_name: имя ноды
        :param row_width: кол-во кнопок в строке, по умолчанию 2
        :return: клавиатура
        '''

        node_type = self._get_node_type(node_name)

        # у текстовых нод не может быть клавиатуры
        if node_type == 'plain':
            return None

        # специальный объект разметки, встраиваемая клавиатура
        markup = telebot.types.InlineKeyboardMarkup(row_width=row_width)

        # получаем ответы ноды
        answers = self._get_node_answers(node_name)

        markup_buttons = []

        # пройдемся по ответам, пронумеровав их от 0 до N
        for i, a in enumerate(answers):
            # если в GOTO указана ссылка, то сделаем специальную кнопку с внешней ссылкой
            if is_url(a['goto']):
                markup_buttons.append(telebot.types.InlineKeyboardButton(
                    text=a['name'],
                    url=a['goto']
                ))
            # если это просто кнопка, то создадим кнопку с
            else:
                payload = str(i)
                markup_buttons.append(telebot.types.InlineKeyboardButton(
                    text=a['name'],
                    callback_data=payload
                ))

        # добавляем кнопки в клавиатуру
        markup.add(*markup_buttons)

        return markup

    def _get_node_photo(self, node_name):
        '''
        Взять фото из ноды
        :param node_name: имя ноды
        :return: URL фотографии
        '''

        node = self._get_node(node_name)
        return node.get('photo', None)

    def _play_node(self, message, node_name):
        '''
        Отыгрывает ноду, то есть пишет от имени бота ее вопрос / картинку / клавиатуру
        :param message: сообщение pyTelegramBot
        :param node_name: имя ноды
        :return: ничего
        '''

        phrase = self._get_node_phrase(node_name)
        photo = self._get_node_photo(node_name)
        buttons = self._get_node_buttons(message, node_name)

        if phrase is None:
            raise IndexError('No phrase in node {}'.format(node_name))

        if photo is not None:
            self._bot.send_photo(message.chat.id,
                                 photo=photo,
                                 caption=phrase,
                                 reply_markup=buttons)
        else:
            self._bot.send_message(message.chat.id,
                                   text=phrase,
                                   reply_markup=buttons)

        self._sessions[message.chat.id] = node_name

    def _play_wrong(self, message, node_name):
        '''
        Отыгрывает неправильный ответ пользователя, показывает ему специализированное сообщение
        :param message: сообщение pyTelegramBot
        :param node_name: имя ноды
        :return: ничего
        '''

        phrase = self._get_node_phrase(node_name, the_key='wrong')

        if phrase is None:
            phrase = self._voc.get('wrong', None)
            # raise IndexError('No wrong phrase in node {}'.format(node_name))

        self._bot.send_message(message.chat.id, phrase)

    def _dialog(self, message, data=None):
        '''
        Основной алгоритм ведения диалогов
        :param message: сообщение pyTelegramBot
        :param data: код нажатой кнопки
        :return: ничего
        '''

        # отправляем пользователю мета-сообщение "Бот печатает..."
        self._bot.send_chat_action(message.chat.id, 'typing')

        # попытаемся взять текущую ноду для данного чата
        current_node = self._get_session(message.chat.id)

        # если диалога еще нет, то идем в самое начало
        if current_node is None:
            self._play_node(message, self._default_node)
            return

        try:
            # проверяем ответ пользователя, и определяемся со следующей нодой
            next_node = self._check_answer(message, data, current_node)

            # если нода не смогла определиться, то, скорее всего, это ошибка,
            # а значит идем в начало
            if next_node is None:
                self._play_wrong(message, current_node)
                return

            # отыгрываем следующую ноду
            self._play_node(message, next_node)

        # в случае возникновения ошибки в коде
        except (AttributeError, IndexError, KeyError, ValueError) as e:
            import traceback

            # показываем в консоли эту ошибку, чтобы мы понимали что произошло
            print(e)
            print(traceback.format_exc())

            # отыгрываем текущую ноду еще раз
            self._play_node(message, self._default_node)

    def _attach_handlers(self):
        '''
        Добавляет нашу реакцию (ведение диалога) на события чат-бота
        :return:
        '''

        # реакция на текстовые сообщения
        @self._bot.message_handler(content_types=['text'])
        def text_handler(message):
            self._dialog(message=message)

        # реакция на нажатие кнопки
        @self._bot.callback_query_handler(func=lambda call: True)
        def callback_inline(call):
            self._dialog(message=call.message, data=call.data)

    def start(self):
        '''
        Запускаем вселенную!
        :return:
        '''

        # привязываем обработчики событий
        self._attach_handlers()

        # запускаем бота обработчики событий
        self._bot.polling()
