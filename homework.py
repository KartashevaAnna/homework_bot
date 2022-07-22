import logging
import os
import sys
import time
from http import HTTPStatus
from logging import StreamHandler

import requests
import telegram
from dotenv import load_dotenv

from exceptions import LoggedOnlyError, NoHomeworksError

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
    message_sent = bot.send_message(TELEGRAM_CHAT_ID, message)
    logger.info(f'Message {message_sent} sent')


def get_api_answer(current_timestamp):
    """This function receives reply from Yandex Praktikum."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != HTTPStatus.OK:
        raise LoggedOnlyError
        logger.error(f'Yandex Praktikum is not responding')
    homework = response.json()
    return (homework)


def check_response(response):
    """Checking whether the response from Yandex Praktikum is valid."""
    if response == {}:
        raise NoHomeworksError('No homeworks found')
    elif response['homeworks'] is None:
        raise LoggedOnlyError
        logger.error(f'No "homeworks" found as key')
    elif type(response.get('homeworks')) != list:
        raise LoggedOnlyError
        logger.error(f'We expect a list of homeworks')
    homework = response.get('homeworks')
    return homework


def send_error_message(error):
    message = f'Сбой в работе программы: {error}'
    bot.send_message(message)

def parse_status(homework):
    """This function obtains specific values of the homework."""
    if not list:
        raise NoHomeworksError
        logging.error('The list of homeworks is empty')
        bot.send_error_message(error)

    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = REVIEWER_REPLY[homework_status]
    fine = f'Изменился статус проверки работы "{homework_name}". {verdict}'
    return fine




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

    while True:

        try:
            current_timestamp = int(time.time())
            response = get_api_answer(current_timestamp)
            check_response(response)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            logging.error(error, exc_info=True)
            if error == LoggedOnlyError:
                send_error_message(error)
        else:
            current_timestamp = response.get('current_date', current_timestamp)

            try:
                send_message(
                    bot, parse_status(
                        check_response(get_api_answer(current_timestamp))
                    )
                )
            except Exception as error:
                logger.error(f'Failed to send message, reason: {error}')
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
