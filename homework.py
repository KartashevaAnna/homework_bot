import logging
import os
import time
from logging import StreamHandler

import requests
import telegram
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',

)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = StreamHandler()
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
handler.setFormatter(formatter)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


class TokenNotFoundError(Exception):
    """At least one token is missing in env."""

    pass


class NoHomeworksError(Exception):
    """The list of homeworks is empty."""

    pass


class NoReplyFromApiError(Exception):
    """Yandex Praktikum is not responding."""

    pass


def send_message(bot, message):
    """This function sends messages to telegram."""
    bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(current_timestamp):
    """This function receives reply from Yandex Praktikum."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != 200:
        raise NoReplyFromApiError
    else:
        homework = response.json()
        return (homework)


def check_response(response):
    """Checking whether the response from Yandex Praktikum is valid."""
    if response == {}:
        raise NoHomeworksError('No homeworks found')
    elif response['homeworks'] is None:
        raise KeyError
    elif type(response.get('homeworks')) != list:
        raise TypeError('We expect a list of homeworks')
    else:
        homework = response.get('homeworks')
        return homework


def parse_status(homework):
    """This function obtains specific values of the homework."""
    if homework != []:
        homework_name = homework.get('homework_name')
        homework_status = homework.get('status')
        verdict = HOMEWORK_STATUSES[homework_status]
        fine = f'Изменился статус проверки работы "{homework_name}". {verdict}'
        return fine
    else:
        logging.error('NoHomeworksError')
        raise NoHomeworksError


def check_tokens():
    """This function checks whether all tokens are present."""
    tokens_list = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    for token in tokens_list:
        if not token:
            return False
        return True


def main():
    """Main functions are called from here."""
    if not check_tokens():
        logger.critical('No tokens found')

    while True:
        try:
            current_timestamp = int(time.time())
            response = get_api_answer(current_timestamp)
            check_response(response)
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            logging.error(error, exc_info=True)
            time.sleep(RETRY_TIME)
        else:
            current_timestamp = response.get('current_date', current_timestamp)
            bot = telegram.Bot(token=TELEGRAM_TOKEN)
            try:
                message_sent = send_message(
                    bot, parse_status(
                        check_response(get_api_answer(current_timestamp))
                    )
                )
                logger.info(f'Message {message_sent} sent')
            except Exception as error:
                logger.error(f'Failed to send message, reason: {error}')


if __name__ == '__main__':
    main()
