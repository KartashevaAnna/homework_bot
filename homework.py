import logging
import os
import sys
import time
from http import HTTPStatus
from logging import StreamHandler

import requests
import telegram
from telegram.error import TelegramError
from dotenv import load_dotenv

from exceptions import LoggedOnlyError, NoHomeworksError, ApiNotRespondingError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
REVIEWER_REPLY = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
logger = logging.getLogger(__name__)


def send_message(bot, message):
    """This function sends messages to telegram."""
    try:
        message_sent = bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Message {message_sent} sent')
    except TelegramError as error:
        raise LoggedOnlyError(f'Failed to send message, reason: {error}')


def get_api_answer(current_timestamp):
    """This function receives reply from Yandex Praktikum."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != HTTPStatus.OK:
        raise ApiNotRespondingError(f'response code is {response.status_code}')
    homework = response.json()
    return homework


def check_response(response):
    """Checking whether the response from Yandex Praktikum is valid."""
    if not response:
        raise NoHomeworksError('No homeworks found')
    if response['homeworks'] is None:
        raise LoggedOnlyError(
            f'response["homeworks"] is {response["homeworks"]}'
        )
    if not isinstance(response.get('homeworks'), list):
        raise LoggedOnlyError(
            'response["homeworks"] must be a list, '
            f'got {type(response.get("homeworks"))} instead.')

    if not isinstance(response.get('homeworks')[0], dict):
        raise LoggedOnlyError(
            f'response.get("homeworks") must be a dict, '
            f'got {type(response.get("homeworks")[0])} instead.'
        )
    homework = response.get('homeworks')
    return homework


def parse_status(homework):
    """This function obtains specific values of the homework."""
    if not list:
        raise NoHomeworksError('The list of homeworks is empty')

    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = REVIEWER_REPLY[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """This function checks whether all tokens are present."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Main functions are called from here."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',

    )
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = StreamHandler(stream=sys.stdout)
    logger.addHandler(handler)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
    handler.setFormatter(formatter)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    if not check_tokens():
        logger.critical('No tokens found')
        sys.exit()

    previous_messages = []

    def clear_messages(previous_messages):
        """Cleaning memory."""
        if len(previous_messages) > 2:
            return previous_messages.pop()

    def send_error_message(error):
        """Sending details of errors occurred to telegram."""
        message = f'Сбой в работе программы: {error}'
        if message != previous_messages[-1]:
            bot.send_message(TELEGRAM_CHAT_ID, message)
            previous_messages.append(message)
            clear_messages(previous_messages)

    while True:

        try:
            current_timestamp = int(time.time())
            response = get_api_answer(current_timestamp)
            check_response(response)
            current_timestamp = response.get('current_date', current_timestamp)
            bot.send_message(
                TELEGRAM_CHAT_ID,
                parse_status(check_response(get_api_answer(current_timestamp)))
            )
        except LoggedOnlyError as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
        except Exception as error:
            logging.error(error)
            send_error_message(error)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
