# coding=windows-1251

import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from datetime import datetime, timedelta
import requests
import re
import time
import json
import threading
import random
import gspread
import logging
import os
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials

print('Запуск бота...')

load_dotenv()

api_key = os.getenv("API_KEY")
user_api_key = os.getenv("USER_API_KEY")
user_api_key_0 = os.getenv("USER_API_KEY_0")

if api_key:
    print("API ключ успешно загружен")

if user_api_key:
    print("API ключ пользователя успешно загружен")

if user_api_key_0:
    print("API ключ пользователя_0 успешно загружен")

# токен сообщества
TOKEN = api_key
TOKEN_USER = user_api_key
TOKEN_USER_2 = user_api_key_0
owner_user_id_1 = os.getenv("OWNER_ID_1")
owner_user_id_2 = os.getenv("OWNER_ID_2")
poll_user_id = owner_user_id_2
poll_peer_id = os.getenv("POLL_PEER_ID")
poll_group_id = os.getenv("POLL_GROUP_ID")
user_poll_peer_id = os.getenv("USER_POLL_PEER_ID")
flood_peer_id = os.getenv("FLOOD_PEER_ID")
sheet_link = os.getenv("SHEET_LINK")
COUNT = 50  # Количество последних сообщений
owner_ids = [owner_user_id_1, owner_user_id_2, poll_group_id]

vk_session = vk_api.VkApi(token=TOKEN)
longpoll = VkLongPoll(vk_session)
vk_session_user = vk_api.VkApi(token=TOKEN_USER)
vk = vk_session_user.get_api()
vk_session_user_2 = vk_api.VkApi(token=TOKEN_USER_2)
midg_vk = vk_session_user_2.get_api()

# Фразы, на которые бот должен реагировать
phrases_to_respond_hi = ['здравствуйте', 'привет', 'приветствую', 'добрый день', 'добрый вечер', 'доброе утро']
phrases_to_respond_commands = ['купить игру', 'аккаунт', 'приобрести игру', 'акк', 'tl', 'лир']
phrases_to_respond_chat = ['чат', 'чата', 'чатик']
phrases_to_respond_thanks = ['спасибо', 'благодарю', 'спс']
phrases_to_respond_needhuman = ['нужен человек', 'позови человека', 'позови']
phrases_to_respond_game = ['собрать', 'оформить']
phrases_to_respond_collect = ['сбор']
phrases_to_respond_position = ['позиции']
phrases_to_respond_deletemsg = ['удали опрос']
phrases_to_respond_deleteflag = ['удали метку']

phrases_to_send_thanks = ['Нет проблем, я для этого создан!', 'Рад помочь! На страже вашего комфорта.',
                          'Рад, что смог помочь! Я всегда тут для вас.',
                          'Пожалуйста! Это не только моя работа, но и удовольствие.',
                          'Без проблем! Да прибудет с вами энергия благодарности!',
                          'Спасибо за ваше спасибо! Продолжайте в том же духе!']

# ID чатов, которые нужно игнорировать
ignored_chats = ['2000000001', '2000000002']
# Хранение состояний пользователей
user_states = {}

poll_type_mapping = {
    'PS4 PS5': 1,
    'PS5': 2,
    'PS PLUS': 3,
    'DLC PS4 PS5': 4,
    'DLC PS5': 5
}

# Настройка логгера
logging.basicConfig(filename="log.txt", level=logging.INFO,
                    format="%(asctime)s %(message)s")

def log_error(message):
    logging.error(message)


def find_poll(attachments):
    # Итерация по элементам словаря
    for key, value in attachments.items():
        # Проверка, является ли значение 'poll'
        if value == 'poll':
            # Возврат соответствующего ключа attach (например, 'attach1', 'attach2' и т.д.)
            return key.replace('_type', '')
    # Если 'poll' не найден, возврат None
    return None


# Функция для обработки сообщений
def warningtext(peer_id):
    warning_text = 'Пожалуйста ознакомься с правилами в закрепленном сообщении чата. Запомни, что оплачивать игры без разрешения *midg_game (администратора) запрещено!'
    vk_session.method('messages.send', {
        'peer_id': peer_id,
        'message': warning_text,
        'random_id': get_random_id(),
    })
    vk_session.method('messages.send', {
        'peer_id': peer_id,
        'message': 'Здесь ты можешь узнать, что такое позиции: https://vk.com/narrative-217283918_35449_456239061',
        'random_id': get_random_id(),
    })
    vk_session.method('messages.send', {
        'peer_id': peer_id,
        'message': 'А тут узнаешь, как покупать или продавать игры в нашем чатике: https://vk.com/narrative-217283918_35448_456239050',
        'random_id': get_random_id(),
    })


def process_message(message):
    hi_flag = False
    command_flag = False
    chat_flag = False
    needhuman_flag = False
    thanks_flag = False
    game_flag = False
    collect_flag = False
    position_flag = False
    deletemsg_flag = False
    deleteflag_flag = False

    # Проверяем наличие приветственной фразы в сообщении
    for phrase in phrases_to_respond_hi:
        if re.search(phrase.lower(), message.lower(), re.IGNORECASE):
            hi_flag = True
            break

    # Проверяем наличие командной фразы в сообщении
    for phrase in phrases_to_respond_commands:
        if re.search(phrase.lower(), message.lower(), re.IGNORECASE):
            command_flag = True
            break

    # Проверяем наличие чат фразы в сообщении
    for phrase in phrases_to_respond_chat:
        if re.search(phrase.lower(), message.lower(), re.IGNORECASE):
            chat_flag = True
            break

    # Проверяем наличие фразы для вызова человека в сообщении
    for phrase in phrases_to_respond_needhuman:
        if re.search(phrase.lower(), message.lower(), re.IGNORECASE):
            needhuman_flag = True
            break
    # Проверяем наличие фразы благодарности в сообщении
    for phrase in phrases_to_respond_thanks:
        if re.search(phrase.lower(), message.lower(), re.IGNORECASE):
            thanks_flag = True
            break
            # Желание собрать игру
    for phrase in phrases_to_respond_game:
        if re.search(phrase.lower(), message.lower(), re.IGNORECASE):
            game_flag = True
            break
            # Сбор игры
    for phrase in phrases_to_respond_collect:
        if re.search(phrase.lower(), message.lower(), re.IGNORECASE):
            collect_flag = True
            break
            # Позиция
    for phrase in phrases_to_respond_position:
        if re.search(phrase.lower(), message.lower(), re.IGNORECASE):
            position_flag = True
            break
            # Удалить строку
    for phrase in phrases_to_respond_deletemsg:
        if re.search(phrase.lower(), message.lower(), re.IGNORECASE):
            deletemsg_flag = True
            break
            # Удалить метку
    for phrase in phrases_to_respond_deleteflag:
        if re.search(phrase.lower(), message.lower(), re.IGNORECASE):
            deleteflag_flag = True
            break
            # Возвращаем результат в зависимости от наличия приветственной и/или командной фразы
    if hi_flag and command_flag:
        return 3  # Сразу начать объяснять
    elif hi_flag and chat_flag:
        return 5
    elif hi_flag:
        return 1  # Приветствовать
    elif command_flag:
        return 2  # Дать объяснение
    elif chat_flag:
        return 4
    elif needhuman_flag:
        return 6
    elif thanks_flag:
        return 7
    elif game_flag:
        return 8
    elif collect_flag:
        return 9
    elif position_flag:
        return 10
    elif deletemsg_flag:
        return -1
    elif deleteflag_flag:
        return -2
    else:
        return False  # Не понял сообщение


def save_poll_info_google_sheets(poll_id, poll_type, game_title, message_id):
    try:
        print('The bot is in the process of adding the poll to Google Sheets...')
        # Авторизуемся в Google Sheets API
        client = authenticate_google_sheets()
        # Открываем таблицу по URL
        sheet = client.open_by_url(sheet_link)
        # Выбираем лист, с которым будем работать
        worksheet = sheet.get_worksheet(3)  # лист 'Опросы'
        # Добавляем данные в таблицу
        current_date = datetime.now()
        formatted_date = current_date.strftime(' %d.%m.%Y')
        if poll_type == 3:
            multiplier = '1, 1, 1'
        else:
            multiplier = 1
        data = [poll_id, poll_type, game_title, message_id, 'FALSE', multiplier, formatted_date]
        print(data)
        worksheet.append_row(data)
        worksheet.format('G1:G100', {"numberFormat": {"type": "DATE", "pattern": "dd/mm/yyyy"}})
        print(f'Adding the poll (id: {poll_id}, type: {poll_type}) was a success')
        return True  # Возвращаем True, если добавление прошло успешно
    except Exception as e2:
        print(f"An error occurred: {e2}")
        log_error(e2)
        print(f'Adding a poll (id: {poll_id}, type: {poll_type}) was unsuccessful')
        return False  # Возвращаем False в случае ошибки


def determine_poll_type(poll):
    # Определение типов опросов по количеству и тексту вариантов ответов
    poll_types = {
        1: ['Т2/П2', 'Т3', 'П3', 'Просто кнопка'],  # Game
        2: ['П2', 'П3', 'Просто кнопка'],  # Game
        3: ['Essential Т3', 'Essential П3', 'Extra Т3', 'Extra П3', 'Deluxe Т3', 'Deluxe П3', 'Просто кнопка'],
        # PS Plus
        4: ['Т3', 'П3', 'Просто кнопка'],  # DLC
        5: ['П3', 'Просто кнопка']  # DLC
    }

    # Получение списка текстов вариантов ответов из опроса
    answer_texts = [answer['text'] for answer in poll['answers']]

    # Проверка каждого типа опроса
    for poll_type, expected_answers in poll_types.items():
        if all(any(re.search(r'\b' + re.escape(expected_answer) + r'\b', answer_text, re.IGNORECASE) for answer_text in
                   answer_texts) for expected_answer in expected_answers):
            return poll_type

    # Если ни один из типов не подошел, возвращаем None
    return None


def help_owner(message, user_name):
    vk_session.method('messages.send', {
        'user_id': owner_user_id_1,
        'message': f'Боту нужна помощь в диалоге с пользователем {user_name}. Для удобства пометил диалог, как "Важный"',
        'random_id': get_random_id(),
    })
    vk_session.method('messages.send', {
        'user_id': owner_user_id_1,
        'message': f'Текст сообщения: ' + message,
        'random_id': get_random_id(),
    })
    vk_session.method('messages.send', {
        'user_id': owner_user_id_1,
        'message': 'Пожалуйста не забудь снять метку, как только закончишь общаться с человеком, потому что я не смогу отвечать на сообщения и буду грустить :(',
        'random_id': get_random_id(),
    })
    vk_session.method('messages.send', {
        'user_id': owner_user_id_2,
        'message': f'Боту нужна помощь в диалоге с пользователем {user_name}. Для удобства пометил диалог, как "Важный"',
        'random_id': get_random_id(),
    })
    vk_session.method('messages.send', {
        'user_id': owner_user_id_2,
        'message': f'Текст сообщения: ' + message,
        'random_id': get_random_id(),
    })
    vk_session.method('messages.send', {
        'user_id': owner_user_id_2,
        'message': 'Пожалуйста не забудь снять метку, как только закончишь общаться с человеком, потому что я не смогу отвечать на сообщения и буду грустить :(',
        'random_id': get_random_id(),
    })


def send_alive_message():
    while True:
        print("The bot is still working. The current time is:", time.strftime("%H:%M:%S", time.localtime()))
        time.sleep(3600)  # Отправлять сообщение каждый час


# Запуск потока для отправки сообщения о работе бота
threading.Thread(target=send_alive_message, daemon=True).start()


def authenticate_google_sheets():
    # Указываем название файла JSON с учетными данными
    credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json',
                                                                   ['https://spreadsheets.google.com/feeds',
                                                                    'https://www.googleapis.com/auth/drive'])
    # Авторизуемся в Google Sheets API
    return gspread.authorize(credentials)


def check_lastmsgs_ftrsnd_fromuser():  # Проверка сообщений после загрузки бота
    print('Загрузка старых сообщений от пользователя...')
    messages = vk_session_user.method('messages.getHistory', {'peer_id': user_poll_peer_id, 'count': COUNT})
    flag = False
    client = authenticate_google_sheets()
    sheet = client.open_by_url(sheet_link)
    worksheet = sheet.get_worksheet(3)  # лист 'Опросы''

    for message in messages.get('items', []):
        attachments = message.get('attachments', [])
        for attachment in attachments:
            if attachment.get('type') == 'poll':
                poll_data = attachment.get('poll')
                poll_id = poll_data.get('id')
                print(f"Id опроса: {poll_id}")
                flag = True

            if flag:
                try:
                    found = False
                    records = worksheet.get_all_records()

                    for i, record in enumerate(records, start=2):
                        if poll_id == record['POLL_ID']:
                            found = True
                            break
                    if not found:
                        # ...
                        print(f'Найден пропущенный опрос с ID: {poll_id}')

                        for owner_id in owner_ids:
                            try:
                                poll = vk.polls.getById(owner_id=owner_id, poll_id=poll_id)
                            except Exception as e:
                                continue  # Игнорировать ошибку и попробовать следующий owner_id

                        poll_type = determine_poll_type(poll)

                        if poll_type:
                            print(f'Poll type is {poll_type}.')
                        else:
                            print('Poll type is None')
                            break
                        if message.get('text'):
                            text = message['text']
                            lines = text.split('\n')
                            game_title = lines[0].strip()
                        success = save_poll_info_google_sheets(poll_id, poll_type, game_title, '0')

                        if success:
                            message_to_send = f'Предыдущий опрос (id = {poll_id}) по игре {game_title} успешно добавлен'
                            vk_session.method('messages.send', {
                                'peer_id': owner_user_id_1,
                                'message': message_to_send,
                                'random_id': get_random_id(),
                            })
                            vk_session.method('messages.send', {
                                'peer_id': owner_user_id_2,
                                'message': message_to_send,
                                'random_id': get_random_id(),
                            })
                            break
                except Exception as e:
                    print(f"Error processing message {message['id']}: {e}")
                    log_error(e)
                    time.sleep(10)
            else:
                print("No poll found in the attachments.")
        else:
            print('Message do not have attachments')


check_lastmsgs_ftrsnd_fromuser()


def add_data_to_google_sheet(game_name, position, user_name, account_link):
    try:
        # Авторизуемся в Google Sheets API
        client = authenticate_google_sheets()
        # Открываем таблицу по URL
        sheet = client.open_by_url(sheet_link)
        # Выбираем лист, с которым будем работать
        worksheet = sheet.get_worksheet(0)  # Например, первый лист
        # Добавляем данные в таблицу
        data = [game_name, user_name, account_link, position]
        worksheet.append_row(data)
        return True  # Возвращаем True, если добавление прошло успешно
    except Exception as e1:
        print(f"An error occurred: {e1}")
        print('Не удалось добавить заявку на сбор игры')
        log_error(e1)
        return False  # Возвращаем False в случае ошибки


def process_game_info(message, user_name, account_link):
    # Разделение сообщения на строки и извлечение нужных данных
    lines = message.split('\n')
    game_name = lines[1].split(': ', 1)[1]
    position = lines[2].split(': ')[1]
    # Добавление данных в Google Таблицу
    success = add_data_to_google_sheet(game_name, position, user_name, account_link)
    if success:
        print(f'Добавил заявку на сбор игры {game_name} от пользователя {user_name}, позиция - {position}')
        return True
    else:
        print(f'Не удалось добавить заявку на сбор игры {game_name} от пользователя {user_name}, позиция - {position}')
        return False


def check_poll_conditions(poll_id, poll_type, n):
    for owner_id in owner_ids:
        try:
            poll = vk.polls.getById(owner_id=owner_id, poll_id=poll_id)
        except Exception as e:
            continue  # Игнорировать ошибку и попробовать следующий owner_id

    answers = poll['answers']
    answer_votes = {answer['text']: answer['votes'] for answer in answers}

    if poll_type == 1:
        t2p2_value = list(answer_votes.values())[0]
        t3_value = list(answer_votes.values())[1]
        p3_value = list(answer_votes.values())[2]
        return (t2p2_value >= (1 * n) and t3_value >= (1 * n) and p3_value >= (2 * n)) or \
            (t2p2_value >= (1 * n) and t3_value >= (2 * n) and p3_value >= (1 * n))
    elif poll_type == 2:
        p2_value = list(answer_votes.values())[0]
        p3_value = list(answer_votes.values())[1]
        return p2_value >= 1 * n and p3_value >= 2 * n
    elif poll_type == 5:
        p3_value = list(answer_votes.values())[0]
        return (p3_value >= (2 * n))
    elif poll_type == 4:
        t3_value = list(answer_votes.values())[0]
        return (t3_value >= (2 * n))
    elif poll_type == 3:
        ess_n, ex_n, de_n = map(int, n.split(', '))
        essT3_value = list(answer_votes.values())[0]
        essP3_value = list(answer_votes.values())[1]
        extrT3_value = list(answer_votes.values())[2]
        extrP3_value = list(answer_votes.values())[3]
        deluxeT3_value = list(answer_votes.values())[4]
        deluxeP3_value = list(answer_votes.values())[5]
        if (essT3_value >= (1 * ess_n) and essP3_value >= (1 * ess_n)):
            return 'ess'
        if (extrT3_value >= (1 * ex_n) and extrP3_value >= (1 * ex_n)):
            return 'ex'
        if (deluxeT3_value >= (1 * de_n) and deluxeP3_value >= (1 * de_n)):
            return 'de'


# Функция для получения информации о голосовавших за разные варианты ответов
def get_voters_by_answer(poll_id):
    # Получаем информацию об опросе
    for owner_id in owner_ids:
        try:
            poll = vk.polls.getById(owner_id=owner_id, poll_id=poll_id)
        except Exception as e:
            continue  # Игнорировать ошибку и попробовать следующий owner_id

    answers = poll['answers']

    # Словарь для хранения информации о голосовавших по вариантам ответов
    voters_by_answer = {}

    # Получаем информацию о голосовавших для каждого варианта ответа, кроме "Просто кнопка"
    for answer in answers:
        if answer['text'] != "Просто кнопка":
            response = vk.polls.getVoters(poll_id=poll_id, answer_ids=[answer['id']])
            voters_info = response[0]
            voters_ids = voters_info['users']['items']  # Список ID пользователей, проголосовавших за вариант
            voters_by_answer[answer['text']] = voters_ids

    return voters_by_answer


def compose_message(game_title, voters_by_answer, poll_id):
    # Начало составления сообщения
    message = f"(poll_id = {poll_id}) Можно собрать игру: {game_title}\n"

    # Итерация по каждому варианту ответа и добавление информации о голосовавших в сообщение
    for answer_text, voters_ids in voters_by_answer.items():
        # Добавление текста варианта ответа
        message += f"{answer_text}:\n"
        # Добавление имени, фамилии и ссылки на профиль каждого голосовавшего
        for voter_id in voters_ids:
            # Получение информации о пользователе через VK API
            user_info = vk.users.get(user_ids=voter_id)[0]
            # Извлечение имени и фамилии пользователя
            first_name = user_info['first_name']
            last_name = user_info['last_name']
            # Добавление информации о голосовавшем в сообщение
            message += f"*id{voter_id} ({first_name} {last_name})\n"

    return message


# Функция для проверки всех опросов в таблице
def check_all_polls():
    client = authenticate_google_sheets()
    # Открываем таблицу по URL
    sheet = client.open_by_url(sheet_link)
    # Выбираем лист, с которым будем работать
    worksheet = sheet.get_worksheet(3)  # лист 'Опросы'
    # Получаем все записи из таблицы
    records = worksheet.get_all_records()
    for i, record in enumerate(records, start=2):
        poll_id = record['POLL_ID']
        poll_type = record['POLL_TYPE']
        game_title = record['GAME_TITLE']
        collect_value = record['COLLECT']
        multiplier = record['MULTIPLIER']

        # Проверяем условия опроса
        success = check_poll_conditions(poll_id, poll_type, multiplier)
        if poll_type == 3:
            ess_n, ex_n, de_n = map(int, multiplier.split(', '))
            if success == 'ess':
                ess_n += 1
                success = True
            elif success == 'ex':
                ex_n += 1
                success = True
            elif success == 'de':
                de_n += 1
                success = True

        if success and collect_value != 'TRUE':
            print(f"Опрос {poll_id} соответствует условиям типа {poll_type}.")
            voters_by_answer = get_voters_by_answer(poll_id)
            message_to_send = compose_message(game_title, voters_by_answer, poll_id)
            vk_session.method('messages.send', {
                'peer_id': owner_user_id_1,
                'message': message_to_send,
                'random_id': get_random_id(),
            })
            vk_session.method('messages.send', {
                'peer_id': owner_user_id_2,
                'message': message_to_send,
                'random_id': get_random_id(),
            })
            if poll_type == 3:
                new_value = ', '.join(map(str, [ess_n, ex_n, de_n]))
            else:
                current_value = int(worksheet.cell(i, 6).value)
                new_value = current_value + 1
            worksheet.update_cell(i, 6, new_value)
            print(f'Poll id = {poll_id}. Multiplier = {multiplier}')

        elif collect_value == 'TRUE':
            print(f"Опрос {poll_id} уже готов к сборке. Collect = {collect_value}.")
        else:
            print(f"Опрос {poll_id} не соответствует условиям типа {poll_type}.")


# Функция для периодической проверки опросов каждый час
def hourly_poll_check():
    while True:
        try:
            print("Начинаю проверку всех опросов... Текущее время:", time.strftime("%H:%M:%S", time.localtime()))
            check_all_polls()
            print("Проверка окончена. Текущее время:", time.strftime("%H:%M:%S", time.localtime()))
            time.sleep(3600)  # Ожидаем час перед следующей проверкой
        except Exception as e4:
            print(f"An error occurred in hourly_poll_check: {e4}")
            log_error(e4)
            time.sleep(30)


# Запускаем периодическую проверку опросов
threading.Thread(target=hourly_poll_check, daemon=True).start()


def extract_id_from_string(string):
    match = re.search(r'id\s*=\s*(\d+)', string)
    if match:
        return int(match.group(1))
    else:
        return None


def send_message(peer_id, message, keyboard = None):
    if keyboard:
        keyboard = keyboard.get_keyboard()
    vk_session.method('messages.send', {
        'peer_id': peer_id,
        'message': message,
        'keyboard': keyboard if keyboard else None,
        'random_id': get_random_id(),
    })


def download_image(url, save_path):
    response = requests.get(url)
    if response.status_code == 200:
        with open(save_path, 'wb') as file:
            file.write(response.content)
    else:
        print(f"Failed to download image: {response.status_code}")

#Округляет значение до ближайшего base (по умолчанию 50)
def round_to_nearest(value, base=50):
    return base * round(value / base)

# Основной цикл обработки событий
def main():
    counter = 1
    while True:
        ignore = False
        try:
            for event in longpoll.listen():
                if event.type == VkEventType.MESSAGE_NEW and event.from_me:
                    peerid = event.peer_id
                    if str(peerid) == poll_peer_id:
                        if str(event.user_id) == poll_group_id and event.attachments:
                            poll_id = None
                            poll_key = find_poll(event.attachments)

                            if poll_key:
                                print(f"Poll found in {poll_key}: {event.attachments[poll_key]}")
                            else:
                                print("No poll found in the attachments.")
                                continue

                            poll_id = event.attachments[poll_key]

                            if poll_id is not None:

                                for owner_id in owner_ids:
                                    try:
                                        poll = vk.polls.getById(owner_id=owner_id, poll_id=poll_id)
                                    except Exception as e:
                                        continue  # Игнорировать ошибку и попробовать следующий owner_id

                                poll_type = determine_poll_type(poll)

                                if poll_type:
                                    print(f'Poll type is {poll_type}.')
                                else:
                                    print('Poll type is None')
                                    continue
                                message = event.text
                                message_id = event.message_id
                                lines = message.split('\n')
                                game_title = lines[0].strip()
                                success = save_poll_info_google_sheets(poll_id, poll_type, game_title, message_id)
                                if success:
                                    message_to_send = f'Опрос (id = {poll_id}) по игре {game_title} успешно добавлен.'
                                    vk_session.method('messages.send', {
                                        'peer_id': owner_user_id_1,
                                        'message': message_to_send,
                                        'random_id': get_random_id(),
                                    })
                                    vk_session.method('messages.send', {
                                        'peer_id': owner_user_id_2,
                                        'message': message_to_send,
                                        'random_id': get_random_id(),
                                    })
                                    continue
                if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                    # Если пришло новое сообщение и оно для бота

                    peerid = event.peer_id
                    if str(peerid) == poll_peer_id:
                        if str(event.user_id) == poll_user_id and event.attachments:
                            poll_id = None
                            poll_key = find_poll(event.attachments)

                            if poll_key:
                                print(f"Poll found in {poll_key}: {event.attachments[poll_key]}")
                            else:
                                print("No poll found in the attachments.")
                                continue

                            poll_id = event.attachments[poll_key]

                            if poll_id is not None:

                                poll = vk.polls.getById(owner_id=poll_user_id, poll_id=poll_id)

                                poll_type = determine_poll_type(poll)

                                if poll_type:
                                    print(f'Poll type is {poll_type}.')
                                else:
                                    print('Poll type is None')
                                    continue
                                message = event.text
                                message_id = event.message_id
                                lines = message.split('\n')
                                game_title = lines[0].strip()
                                success = save_poll_info_google_sheets(poll_id, poll_type, game_title, message_id)
                                if success:
                                    message_to_send = f'Опрос (id = {poll_id}) по игре {game_title} успешно добавлен.'
                                    vk_session.method('messages.send', {
                                        'peer_id': owner_user_id_1,
                                        'message': message_to_send,
                                        'random_id': get_random_id(),
                                    })
                                    vk_session.method('messages.send', {
                                        'peer_id': owner_user_id_2,
                                        'message': message_to_send,
                                        'random_id': get_random_id(),
                                    })
                                    continue
                                else:
                                    message_to_send = f'Опрос (id = {poll_id}) по игре {game_title} добавить не удалось.'
                                    vk_session.method('messages.send', {
                                        'peer_id': owner_user_id_1,
                                        'message': message_to_send,
                                        'random_id': get_random_id(),
                                    })
                                    vk_session.method('messages.send', {
                                        'peer_id': owner_user_id_2,
                                        'message': message_to_send,
                                        'random_id': get_random_id(),
                                    })
                                    continue

                    user_id = event.peer_id
                    message = event.text
                    security = False

                    if user_id not in user_states:
                        user_states[user_id] = {'step': 0, 'prices_step': 0}

                    state = user_states[user_id]

                    if message.lower() == "назад" and state['step'] != 0:
                        ignore = True
                        check = False
                        if state['prices_step'] > 0:
                            state['prices_step'] -= 2
                            check = True
                        if check == False:
                            state['step'] -= 2
                            if state['step'] == 0:
                                send_message(user_id, "Напиши отмена и создай опрос заново")
                            else:
                                send_message(user_id, "Напиши исправленное сообщение: ")
                    if str(event.user_id) == str(owner_user_id_1):
                        security = True
                    elif str(user_id) == str(owner_user_id_2):
                        security = True
                    if (message.lower() == "создать опрос" and state['step'] == 0) and security == True:
                        send_message(user_id, "Напиши название игры: ")
                        state['step'] = 1
                        ignore = True
                        next1 = False
                        print(f"Starting create a poll. User_id {event.user_id}")

                    elif message.lower() == "отмена":
                        keyboard = VkKeyboard(one_time=True)
                        keyboard.add_button('Создать опрос', color=VkKeyboardColor.PRIMARY)
                        send_message(user_id, "Понял. отмена", keyboard)
                        del user_states[user_id]
                        ignore = True
                        print(f"Stop create a poll. User_id {event.user_id}")

                    elif state['step'] == 1:
                        ignore = True
                        state['game_name'] = message
                        print(f"Saved game title {state['game_name']}")
                        keyboard = VkKeyboard(one_time=True)
                        keyboard.add_button('русская озвучка', color=VkKeyboardColor.PRIMARY)
                        keyboard.add_button('русские субтитры', color=VkKeyboardColor.PRIMARY)
                        keyboard.add_line()
                        keyboard.add_button('-английский язык', color=VkKeyboardColor.PRIMARY)
                        keyboard.add_button('русский язык', color=VkKeyboardColor.PRIMARY)
                        keyboard.add_line()
                        keyboard.add_button('-не содержит основную игру', color=VkKeyboardColor.PRIMARY)
                        send_message(user_id,
                                     "Напиши или выбери дополнительную информацию (субтитры, озвучка, предзаказ): ", keyboard)
                        state['step'] = 2

                    elif state['step'] == 2:
                        print(f"Saved audio info")
                        ignore = True
                        state['audio_info'] = message
                        send_message(user_id, "Отправь картинку для опроса: ")
                        state['step'] = 3

                    elif state['step'] == 3:
                        ignore = True
                        message_id = event.message_id

                        # Получение полного сообщения
                        response = vk_session.method('messages.getById', {
                            'message_ids': message_id
                        })
                        if 'items' in response and len(response['items']) > 0:
                            message_info = response['items'][0]
                            attachments = message_info.get('attachments', [])

                            for attachment in attachments:
                                if attachment['type'] == 'photo':
                                    photo = attachment['photo']
                                    photo_id = photo['id']
                                    owner_id = photo['owner_id']
                                    access_key = photo.get('access_key', None)

                            keyboard = VkKeyboard(one_time=True)
                            keyboard.add_button('PS4 PS5', color=VkKeyboardColor.PRIMARY)
                            keyboard.add_button('PS5', color=VkKeyboardColor.PRIMARY)
                            keyboard.add_button('PS PLUS', color=VkKeyboardColor.PRIMARY)
                            keyboard.add_button('DLC PS4 PS5', color=VkKeyboardColor.PRIMARY)
                            keyboard.add_button('DLC PS5', color=VkKeyboardColor.PRIMARY)
                            send_message(user_id, "Выбери тип опроса:", keyboard)
                            state['step'] = 0.4
                        else:
                            send_message(user_id, "Пожалуйста, отправь картинку.")
                            print(f"Expected error. Don't saved picture")
                    elif state['step'] == 0.4:
                        if message in poll_type_mapping:
                            state['poll_type'] = poll_type_mapping[message]
                            keyboard = VkKeyboard(one_time=True)
                            keyboard.add_button('Автоматически', color=VkKeyboardColor.PRIMARY)
                            keyboard.add_button('Вручную', color=VkKeyboardColor.PRIMARY)
                            send_message(user_id, "Выбери способ заполнения(Работает только для (PS4 PS5) и PS5): ", keyboard)
                        state['step'] = 4
                        first_send = 0
                        state['accept_price'] = 0
                    elif state['step'] == 4:
                        ignore = True
                        if state['poll_type'] <= 2:
                            if str(message) == "Автоматически":
                                method_input = 1
                                send_message(user_id, "Напиши цену в лирах (без точек): ")
                                first_send = 1
                                break
                            elif str(message) == 'Вручную':
                                method_input = 0
                                first_send = 1
                        if state['poll_type'] <= 2 and method_input == 1:
                            state['tl_price'] = message
                            if method_input != 0 and state['accept_price'] != 1:
                                client = authenticate_google_sheets()
                                sheet = client.open_by_url(sheet_link)
                                worksheet = sheet.get_worksheet(4)
                                worksheet.update_cell(4,1, state['tl_price'])
                                send_message(user_id, "Предлагаю следующие цены: ")
                                if state['poll_type'] == 1:
                                    state['price_T2P2'] = round_to_nearest(float(worksheet.acell('G4').value.replace(',', '.')))
                                    state['price_T3P3'] = round_to_nearest(float(worksheet.acell('H4').value.replace(',', '.')))
                                    price_message = f"Т2/П2 - {state['price_T2P2']}\n Т3 - {state['price_T3P3']}\n П3 - {state['price_T3P3']}\n"
                                    text_message = price_message + "\n Устраивает?"

                                elif state['poll_type'] == 2:
                                    state['price_P2'] = round_to_nearest(float(worksheet.acell('F4').value.replace(',', '.')))
                                    state['price_P3'] = round_to_nearest(float(worksheet.acell('D4').value.replace(',', '.')))
                                    price_message = f"П2 - {state['price_P2']}\n П3 - {state['price_P3']}\n"
                                    text_message = price_message + "\n Устраивает?"
                                keyboard = VkKeyboard(one_time=True)
                                keyboard.add_button('Да', color=VkKeyboardColor.PRIMARY)
                                keyboard.add_button('Нет, введу свои', color=VkKeyboardColor.PRIMARY)
                                send_message(user_id, text_message, keyboard)
                                state['accept_price'] = 1
                            elif state['accept_price'] == 1:
                                if str(message) == 'Да':
                                    if state['poll_type'] == 1:
                                        answers = [f"Т2/П2 - {state['price_T2P2']}р", f"Т3 - {state['price_T3P3']}р",
                                                   f"П3 - {state['price_T3P3']}р", "Просто кнопка"]
                                    else:
                                        answers = [f"П2 - {state['price_P2']}р", f"П3 - {state['price_P3']}р",
                                                   "Просто кнопка"]
                                    state['step'] = 5
                                else:
                                    method_input = 0
                        else:
                            if state['poll_type'] == 1:
                                if state['prices_step'] == 0:
                                    send_message(user_id, "Напиши цену для Т2/П2: ")
                                    state['prices_step'] = 1
                                elif state['prices_step'] == 1:
                                    state['price_T2P2'] = message
                                    send_message(user_id, "Напиши цену для Т3/П3: ")
                                    state['prices_step'] = 2
                                elif state['prices_step'] == 2:
                                    state['price_T3P3'] = message
                                    price_message = f"Т2/П2 - {state['price_T2P2']}\n Т3 - {state['price_T3P3']}\n П3 - {state['price_T3P3']}\n"
                                    text_message = price_message + "\n Верно?"
                                    keyboard = VkKeyboard(one_time=True)
                                    keyboard.add_button('Да', color=VkKeyboardColor.PRIMARY)
                                    keyboard.add_button('Нет, исправить', color=VkKeyboardColor.PRIMARY)
                                    send_message(user_id, text_message, keyboard)
                                    state['prices_step'] = 3
                                elif state['prices_step'] == 3:
                                    print(message)
                                    if str(message) == 'Да':
                                        state['step'] = 5
                                        next1 = True
                                        print(f"Answers saved")
                                        answers = [f"Т2/П2 - {state['price_T2P2']}р", f"Т3 - {state['price_T3P3']}р",
                                                   f"П3 - {state['price_T3P3']}р", "Просто кнопка"]
                                    if str(message) == 'Нет, исправить':
                                        state['prices_step'] = 0

                            elif state['poll_type'] == 2:
                                if state['prices_step'] == 0:
                                    send_message(user_id, "Напиши цену для П2: ")
                                    state['prices_step'] = 1
                                elif state['prices_step'] == 1:
                                    state['price_P2'] = message
                                    send_message(user_id, "Напиши цену для П3: ")
                                    state['prices_step'] = 2
                                elif state['prices_step'] == 2:
                                    state['price_P3'] = message
                                    price_message = f"П2 - {state['price_P2']}\n П3 - {state['price_P3']}\n"
                                    text_message = price_message + "\n Верно?"
                                    keyboard = VkKeyboard(one_time=True)
                                    keyboard.add_button('Да', color=VkKeyboardColor.PRIMARY)
                                    keyboard.add_button('Нет, исправить', color=VkKeyboardColor.PRIMARY)
                                    send_message(user_id, text_message, keyboard)
                                    state['prices_step'] = 3
                                elif state['prices_step'] == 3:
                                    if str(message) == 'Да':
                                        state['step'] = 5
                                        answers = [f"П2 - {state['price_P2']}р", f"П3 - {state['price_P3']}р",
                                                   "Просто кнопка"]
                                        next1 = True
                                        print(f"Answers saved")
                                    if str(message) == 'Нет, исправить':
                                        state['prices_step'] = 0
                            elif state['poll_type'] == 3:
                                if state['prices_step'] == 0:
                                    send_message(user_id, "Напиши цену для Essential T3: ")
                                    state['prices_step'] = 1
                                elif state['prices_step'] == 1:
                                    state['price_EsT3'] = message
                                    send_message(user_id, "Напиши цену для Essential П3: ")
                                    state['prices_step'] = 2
                                elif state['prices_step'] == 2:
                                    state['price_EsP3'] = message
                                    send_message(user_id, "Напиши цену для Extra T3: ")
                                    state['prices_step'] = 3
                                elif state['prices_step'] == 3:
                                    state['price_ExT3'] = message
                                    send_message(user_id, "Напиши цену для Extra П3: ")
                                    state['prices_step'] = 4
                                elif state['prices_step'] == 4:
                                    state['price_ExP3'] = message
                                    send_message(user_id, "Напиши цену для Deluxe T3: ")
                                    state['prices_step'] = 5
                                elif state['prices_step'] == 5:
                                    state['price_DeT3'] = message
                                    send_message(user_id, "Напиши цену для Deluxe П3: ")
                                    state['prices_step'] = 6
                                elif state['prices_step'] == 6:
                                    state['price_DeP3'] = message
                                    price_message = f"Essential T3 - {state['price_EsT3']}\n Essential П3 - {state['price_EsP3']}\n\n" \
                                                    f"Extra T3 - {state['price_ExT3']}\n Extra П3 - {state['price_ExP3']}\n\n" \
                                                    f"Deluxe T3 - {state['price_DeT3']}\n Deluxe П3 - {state['price_DeP3']}\n\n"
                                    text_message = price_message + "\n Верно?"
                                    keyboard = VkKeyboard(one_time=True)
                                    keyboard.add_button('Да', color=VkKeyboardColor.PRIMARY)
                                    keyboard.add_button('Нет, исправить', color=VkKeyboardColor.PRIMARY)
                                    send_message(user_id, text_message, keyboard)
                                    state['prices_step'] = 7
                                elif state['prices_step'] == 7:
                                    if str(message) == 'Да':
                                        state['step'] = 5
                                        answers = [f"Essenital T3 - {state['price_EsT3']}р",
                                                   f"Essential П3 - {state['price_EsP3']}р",
                                                   f"Extra T3 - {state['price_ExT3']}р",
                                                   f"Extra П3 - {state['price_ExP3']}р",
                                                   f"Deluxe T3 - {state['price_DeT3']}р",
                                                   f"Deluxe П3 - {state['price_DeP3']}р",
                                                   "Просто кнопка"]
                                        next1 = True
                                        print(f"Answers saved")
                                    if str(message) == 'Нет, исправить':
                                        state['prices_step'] = 0
                            elif state['poll_type'] == 4:
                                ignore = True
                                if state['prices_step'] == 0:
                                    send_message(user_id, "Напиши цену для Т3: ")
                                    state['prices_step'] = 1
                                if state['prices_step'] == 1:
                                    state['price_T3'] = message
                                    send_message(user_id, "Напиши цену для П3: ")
                                    state['prices_step'] = 2
                                elif state['prices_step'] == 2:
                                    state['price_P3'] = message
                                    price_message = f"Т3 - {state['price_T3']}\nП3 - {state['price_P3']}"
                                    text_message = price_message + "\n Верно?"
                                    keyboard = VkKeyboard(one_time=True)
                                    keyboard.add_button('Да', color=VkKeyboardColor.PRIMARY)
                                    keyboard.add_button('Нет, исправить', color=VkKeyboardColor.PRIMARY)
                                    send_message(user_id, text_message, keyboard)
                                    state['prices_step'] = 3
                                elif state['prices_step'] == 3:
                                    if str(message) == 'Да':
                                        state['step'] = 5
                                        answers = [f"Т3 - {state['price_T3']}р",f"П3 - {state['price_P3']}р", "Просто кнопка"]
                                        next1 = True
                                        print(f"Answers saved")
                                    if str(message) == 'Нет, исправить':
                                        state['prices_step'] = 0
                            elif state['poll_type'] == 5:
                                ignore = True
                                if state['prices_step'] == 0:
                                    send_message(user_id, "Напиши цену для П3: ")
                                    state['prices_step'] = 1
                                elif state['prices_step'] == 1:
                                    state['price_P3'] = message
                                    price_message = f"П3 - {state['price_P3']}\n"
                                    text_message = price_message + "\n Верно?"
                                    keyboard = VkKeyboard(one_time=True)
                                    keyboard.add_button('Да', color=VkKeyboardColor.PRIMARY)
                                    keyboard.add_button('Нет, исправить', color=VkKeyboardColor.PRIMARY)
                                    send_message(user_id, text_message, keyboard)
                                    state['prices_step'] = 2
                                elif state['prices_step'] == 2:
                                    if str(message) == 'Да':
                                        state['step'] = 5
                                        answers = [f"П3 - {state['price_P3']}р", "Просто кнопка"]
                                        print(f"Answers saved")
                                    if str(message) == 'Нет, исправить':
                                        state['prices_step'] = 0
                                        send_message(user_id, 'Напиши: "Исправить"')
                            else:
                                if method_input == 1:
                                    send_message(user_id, "Пожалуйста, выберите один из предложенных типов опроса.")

                    if state['step'] == 5:
                        ignore = True
                        # Формируем итоговое сообщение
                        final_message = (f"{state['game_name']}&#128293;\n\n"
                                         f"{state['audio_info']}\n\n"
                                         "Желающие собрать бронируем места в опросе &#128071;\n\n"
                                         "Если вы не готовы купить позицию, не голосуйте!")

                        question = 'Бронь'
                        poll = midg_vk.polls.create(question=question, add_answers=json.dumps(answers),
                                                  owner_id=owner_user_id_2)
                        poll_id = poll['id']
                        attachment = f"photo{owner_id}_{photo_id}_{access_key},poll{owner_user_id_2}_{poll_id}"
                        vk_session.method('messages.send', {
                            'peer_id': user_id,
                            'message': final_message,
                            'attachment': attachment,
                            'random_id': get_random_id()
                        })
                        keyboard = VkKeyboard(one_time=True)
                        keyboard.add_button('Да', color=VkKeyboardColor.PRIMARY)
                        keyboard.add_button('Нет, исправить', color=VkKeyboardColor.PRIMARY)
                        send_message(user_id, "Верно?", keyboard)
                        state['step'] = 6
                    elif state['step'] == 6:
                        print(f"Answers saved")
                        ignore = True
                        if message == 'Да':
                            vk_session.method('messages.send', {
                                'peer_id': poll_peer_id,
                                'message': final_message,
                                'attachment': attachment,
                                'random_id': get_random_id()
                            })
                            poll_info = vk.polls.getById(owner_id=owner_user_id_2, poll_id=poll_id) # user 1
                            answer_id = None
                            for answer in poll_info['answers']:
                                if answer['text'] == "Просто кнопка":
                                    answer_id = answer['id']
                                    break

                            if answer_id is not None:
                                vote_response = vk.polls.addVote(owner_id=owner_user_id_2, poll_id=poll_id, answer_ids=[answer_id])
                            else:
                                print('Answer with text "Просто кнопка" not found.')

                            poll_info = midg_vk.polls.getById(owner_id=owner_user_id_2, poll_id=poll_id) # user 2
                            answer_id = None
                            for answer in poll_info['answers']:
                                if answer['text'] == "Просто кнопка":
                                    answer_id = answer['id']
                                    break

                            if answer_id is not None:
                                vote_response = midg_vk.polls.addVote(owner_id=owner_user_id_2, poll_id=poll_id,
                                                                 answer_ids=[answer_id])
                            else:
                                print('Answer with text "Просто кнопка" not found.')
                            keyboard = VkKeyboard(one_time=True)
                            keyboard.add_button('Создать опрос', color=VkKeyboardColor.PRIMARY)
                            send_message(user_id, "Опрос добавлен в чат", keyboard)
                            print(f"Poll was been created")
                            del user_states[user_id]
                        if message == 'Нет, исправить':
                            state['step'] = 0
                            keyboard = VkKeyboard(one_time=True)
                            keyboard.add_button('Создать опрос', color=VkKeyboardColor.PRIMARY)
                            send_message(user_id, 'Нажми: "Создать опрос"', keyboard)
                        # Сбрасываем состояние

                    # Проверяем, содержит ли сообщение фразы, на которые бот должен реагировать
                    message_type = process_message(event.text)
                    # Получаем информацию о пользователе
                    user_info = vk_session.method('users.get', {'user_ids': event.user_id})
                    first_user_name = user_info[0]['first_name']  # Получаем имя пользователя
                    last_user_name = user_info[0]['last_name']
                    account_id = user_info[0]['id']
                    account_link = 'vk.com/id' + str(account_id)
                    user_name = first_user_name + ' ' + last_user_name

                    if str(peerid) in ignored_chats:
                        print(f'Ingnoring chat {peerid}')
                        continue

                    is_important = vk_session.method('messages.getConversations')
                    important_value = is_important['items'][0]['conversation']['important']
                    id_value = is_important['items'][0]['conversation']['peer']['id']
                    if important_value:
                        print(f'Игнорирую сообщение из диалога с {user_name} (reason: important is True)')
                        continue

                    # Формируем приветственное сообщение с упоминанием имени пользователя
                    welcome_message = f'Привет, {first_user_name}! '
                    info_text = 'обратись к *midg_game (Midgard Games) '
                    chat = 'Лови! Ссылка на чат: https://vk.me/join/s0c3RgqtN_IBklkgAkGoHL0bo_MYL2X2Q9E='

                    if message_type == 1:
                        # Отправляем приветственное сообщение
                        vk_session.method('messages.send', {
                            'peer_id': event.peer_id,
                            'message': welcome_message + 'Как я могу вам помочь?',
                            'random_id': get_random_id(),
                        })
                        counter = 1
                    elif message_type == 2:
                        # Если сообщение содержит командную фразу, отправляем объяснение
                        vk_session.method('messages.send', {
                            'peer_id': event.peer_id,
                            'message': 'Чтобы купить игру, ' + info_text,
                            'random_id': get_random_id(),
                        })
                        counter = 1
                    elif message_type == 3:
                        # Если сообщение содержит и приветственную, и командную фразы, сразу начинаем объяснять
                        vk_session.method('messages.send', {
                            'peer_id': event.peer_id,
                            'message': welcome_message + 'Чтобы купить игру, ' + info_text,
                            'random_id': get_random_id(),
                        })
                        counter = 1
                    elif message_type == 5:
                        # Если сообщение содержит и приветственную, и чат фразы, сразу начинаем объяснять
                        vk_session.method('messages.send', {
                            'peer_id': event.peer_id,
                            'message': welcome_message + chat,
                            'random_id': get_random_id(),
                        })
                        warningtext(event.peer_id)
                        counter = 1
                    elif message_type == 4:
                        # Если только ссылка на чат
                        vk_session.method('messages.send', {
                            'peer_id': event.peer_id,
                            'message': chat,
                            'random_id': get_random_id(),
                        })
                        warningtext(event.peer_id)
                        counter = 1
                    elif message_type == 6:
                        # В чат нужен человек
                        vk_session.method('messages.send', {
                            'peer_id': event.peer_id,
                            'message': 'Сейчас позову человечка. Не теряйся',
                            'random_id': get_random_id(),
                        })
                        vk_session.method('messages.markAsImportantConversation', {
                            'peer_id': event.peer_id,
                            'important': 1})
                        print(f'Зову человека в чат с {user_name}')
                        help_owner(event.text, user_name)
                        counter = 1
                    elif message_type == 7:
                        # Слова благодарности
                        random_phrase_thanks = random.choice(phrases_to_send_thanks)
                        vk_session.method('messages.send', {
                            'peer_id': event.peer_id,
                            'message': random_phrase_thanks,
                            'random_id': get_random_id(),
                        })
                        print(f'Мне сказали "спасибо" в чате с {user_name}. Даже стало тепло на железках')
                        counter = 1
                    elif message_type == 8:
                        # Сбор игры
                        collect_message = '''
    Хочешь предложить игру для сбора? Тогда сообщи мне название игры и позицию, которую ты хочешь занять
    Форма заполнения выглядит так:

    Сбор
    Название игры: *название игры* (Полное название игры из PS Store)
    Позиция: *позиция* (П2, П3, Т2, Т3)

    Пример сообщения:

    Сбор
    Название игры: The Last of Us™ Part I
    Позиция: П3

    Если тебе непонятно слово "позиции", то задай мне вопрос "Что такое позиции?". Я с радостью тебе отвечу
                        '''
                        print(collect_message)
                        vk_session.method('messages.send', {
                            'peer_id': event.peer_id,
                            'message': collect_message,
                            'random_id': get_random_id(),
                        })
                        counter = 1
                    elif message_type == 10:
                        # Объяснение позиций
                        pozition_message = 'Что такое позиции? В нашем сообществе Midgard существуют 4 позиции для PS5 и PS4'
                        P2_message = '''
    Позиция П2 - эта позиция только для консолей PlayStation 5.
    Играть ты сможешь только с выданного аккаунта, на котором обязательно нужно выключить "Общий доступ"
    На твоей консоли всегда должен быть включен Интернет.
                        '''
                        P3_message = '''
    Позиция П3 - эта позиция также только для консолей PlayStation 5.
    Играть ты сможешь с любого аккаунта, но, увы, нельзя играть на выданном аккаунте.
    Здесь тебе нужно будет обязательно включить "Общий доступ"
    На этой позиции подключение к Интернету необязательно
                        '''
                        T2_message = '''
    Позиция Т2 - а эта позиция уже только для консолей PlayStation 4.
    Играть ты сможешь только с выданного аккаунта, на котором обязательно нужно выключить "Общий доступ"
    На твоей консоли всегда должен быть включен Интернет.
                        '''
                        T3_message = '''
    Позиция Т3 - эта позиция также только для консолей PlayStation 4.
    Играть ты сможешь с любого аккаунта, но, увы, нельзя играть на выданном аккаунте.
    Здесь тебе нужно будет обязательно включить "Общий доступ"
    На этой позиции подключение к Интернету необязательно
                        '''
                        vk_session.method('messages.send', {
                            'peer_id': event.peer_id,
                            'message': pozition_message,
                            'random_id': get_random_id(),
                        })
                        vk_session.method('messages.send', {
                            'peer_id': event.peer_id,
                            'message': P2_message,
                            'random_id': get_random_id(),
                        })
                        vk_session.method('messages.send', {
                            'peer_id': event.peer_id,
                            'message': P3_message,
                            'random_id': get_random_id(),
                        })
                        vk_session.method('messages.send', {
                            'peer_id': event.peer_id,
                            'message': T2_message,
                            'random_id': get_random_id(),
                        })
                        vk_session.method('messages.send', {
                            'peer_id': event.peer_id,
                            'message': T3_message,
                            'random_id': get_random_id(),
                        })
                        time.sleep(10)
                        vk_session.method('messages.send', {
                            'peer_id': event.peer_id,
                            'message': 'Хочешь собрать игру? Так и напиши мне: "Хочу собрать игру"',
                            'random_id': get_random_id(),
                        })
                        counter = 1
                    elif message_type == 9:
                        # Сбор игры
                        vk_session.method('messages.send', {
                            'peer_id': event.peer_id,
                            'message': 'Секунду. Пытаюсь сохранить твою заявку...',
                            'random_id': get_random_id(),
                        })
                        print(f'Пытаюсь сохранить заявку пользователя {user_name}...')
                        success = process_game_info(event.text, user_name, account_link)
                        if success:
                            vk_session.method('messages.send', {
                                'peer_id': event.peer_id,
                                'message': 'Успешно сохранил твою заявочку!',
                                'random_id': get_random_id(),
                            })
                        else:
                            vk_session.method('messages.send', {
                                'peer_id': event.peer_id,
                                'message': 'Ой, кажется что-то сломалось. У меня не получилось добавить твою заявку. ' + info_text,
                                'random_id': get_random_id(),
                            })
                        counter = 1
                    elif message_type == -1:
                        print('Начинаю удалять сообщение')
                        delete_poll_id = extract_id_from_string(event.text)
                        client = authenticate_google_sheets()
                        # Открываем таблицу по URL
                        sheet = client.open_by_url(sheet_link)
                        # Выбираем лист, с которым будем работать
                        worksheet = sheet.get_worksheet(3)  # лист 'Опросы'
                        # Получаем все записи из таблицы
                        records = worksheet.get_all_records()
                        for i, record in enumerate(records, start=2):
                            poll_id = record['POLL_ID']
                            message_id = record['MSG_ID']
                            if poll_id == delete_poll_id:
                                worksheet.delete_rows(i)
                                print(f"Удалена строка с poll_id {delete_poll_id}.")
                                message_to_send = f'Строка {i}, содержащая id = {delete_poll_id}, удалена в таблице, а также сдвинута.'
                                vk_session.method('messages.send', {
                                    'peer_id': event.peer_id,
                                    'message': message_to_send,
                                    'random_id': get_random_id(),
                                })
                    elif message_type == -2:
                        print('Начинаю удалять метку')
                        delete_poll_id = extract_id_from_string(event.text)
                        client = authenticate_google_sheets()
                        # Открываем таблицу по URL
                        sheet = client.open_by_url(sheet_link)
                        # Выбираем лист, с которым будем работать
                        worksheet = sheet.get_worksheet(3)  # лист 'Опросы'
                        # Получаем все записи из таблицы
                        records = worksheet.get_all_records()
                        for i, record in enumerate(records, start=2):
                            poll_id = record['POLL_ID']
                            message_id = record['MSG_ID']
                            if poll_id == delete_poll_id:
                                worksheet.update_cell(i, 5, '')
                                print(f"Удалена метка из опроса с poll_id {delete_poll_id}.")
                                message_to_send = f'Метка из строки {i}, содержащая id = {delete_poll_id}, удалена в таблице'
                                vk_session.method('messages.send', {
                                    'peer_id': event.peer_id,
                                    'message': message_to_send,
                                    'random_id': get_random_id(),
                                })
                    else:
                        if ignore == False:
                            if counter == 2:
                                vk_session.method('messages.send', {
                                    'peer_id': event.peer_id,
                                    'message': 'Извини, я не совсем понял тебя. Попробуй объяснить свой вопрос иначе',
                                    'random_id': get_random_id(),
                                })
                                vk_session.method('messages.send', {
                                    'peer_id': event.peer_id,
                                    'message': 'Если ты хочешь в чат, то напиши: "Хочу в чат". Хочешь оформить заявку на сбор игры? - пиши: "Хочу собрать игру". Хочешь купить игру? - пиши: "Хочу купить игру".  А если же тебе нужен человек в чате, то напиши "Позови человека"',
                                    'random_id': get_random_id(),
                                })
                                print(f'Не понял запрос в чате с {user_name}. Повторяю попытку ' + str(counter))
                                counter += 1
                                continue
                            if counter == 3:
                                vk_session.method('messages.send', {
                                    'peer_id': event.peer_id,
                                    'message': 'Похоже, что твой вопросик не для моего процессора. Сейчас позову человечка, который тебе поможет. Не теряйся',
                                    'random_id': get_random_id(),
                                })
                                help_owner(event.text, user_name)
                                vk_session.method('messages.markAsImportantConversation', {
                                    'peer_id': event.peer_id,
                                    'important': 1})
                                print(f'Не смог понять запрос. Запрашиваю помощь в чат с {user_name}')
                                counter = 1
                                continue
                            # Если нет, отправляем стандартное сообщение

                            vk_session.method('messages.send', {
                                'peer_id': event.peer_id,
                                'message': 'Извини, я не совсем понял тебя. Попробуй объяснить свой вопрос иначе',
                                'random_id': get_random_id(),
                            })
                            print(f'Не понял запрос в чате с {user_name}. Повторяю попытку ' + str(counter))
                            counter += 1

        except Exception as e:
            log_error(e)
            print(f"An error occurred: {e}")
            print("Restarting the bot...")
            time.sleep(5)  # Ждем 5 секунд перед перезапуском бота


if __name__ == '__main__':
    main()
