import requests
import threading
import logging
import time

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = '8924676710:AAF4WeeyWbHTMGOsskJGn3uO7t4vVyYytSM'
ADMIN_CHAT_ID = '8130952764'
TELEGRAM_API = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}'

_bot_started = False
_bot_lock = threading.Lock()


def esc(text):
    """Экранирует спецсимволы Markdown для Telegram."""
    if not text:
        return ''
    for ch in ['*', '_', '`', '[']:
        text = str(text).replace(ch, f'\\{ch}')
    return text


def send_message(chat_id, text, keyboard=None):
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    if keyboard:
        data['reply_markup'] = keyboard
    try:
        resp = requests.post(f'{TELEGRAM_API}/sendMessage', json=data, timeout=10)
        if not resp.ok:
            logger.error(f'send_message failed: {resp.text}')
    except Exception as e:
        logger.error(f'send_message exception: {e}')


def answer_callback(callback_id, text):
    try:
        requests.post(f'{TELEGRAM_API}/answerCallbackQuery', json={
            'callback_query_id': callback_id,
            'text': text,
            'show_alert': True
        }, timeout=10)
    except Exception as e:
        logger.error(f'answer_callback error: {e}')


def send_telegram(job):
    """Отправляет новую вакансию админу на проверку."""
    author = esc(job.author.username) if job.author else 'Не указан'
    email = esc(job.author.email) if job.author else 'Не указан'
    phone = esc(job.contact_phone) if job.contact_phone else 'не указан'
    text = (
        f"\U0001f195 *Новая вакансия на проверку!*\n\n"
        f"\U0001f4cc *{esc(job.title)}*\n"
        f"\U0001f3e2 {esc(job.company)} \u00b7 \U0001f4cd {esc(job.location)}\n"
        f"\U0001f4b0 {esc(job.get_salary_display())}\n"
        f"\U0001f464 Автор: {author}\n"
        f"\U0001f4e7 {email}\n"
        f"\U0001f4de {phone}\n"
        f"\U0001f194 ID: {job.pk}"
    )
    keyboard = {
        'inline_keyboard': [[
            {'text': '✅ Одобрить', 'callback_data': f'approve_{job.pk}'},
            {'text': '❌ Отклонить', 'callback_data': f'reject_{job.pk}'}
        ]]
    }
    send_message(ADMIN_CHAT_ID, text, keyboard)


def send_support_notify(ticket):
    """Отправляет обращение в поддержку админу."""
    name = esc(ticket.name)
    email = esc(ticket.email)
    message = esc(ticket.message[:800])
    user_info = f'\U0001f464 {name}\n\U0001f4e7 {email}'
    if ticket.user:
        user_info += f'\n\U0001f517 Аккаунт: {esc(ticket.user.username)}'
    text = (
        f"\U0001f9df *Новое обращение в поддержку!*\n\n"
        f"{user_info}\n\n"
        f"\U0001f4ac *Сообщение:*\n{message}"
    )
    send_message(ADMIN_CHAT_ID, text)


def process_action(action, job_id, callback_id, chat_id):
    from .models import Job
    from django.core.mail import send_mail
    from django.conf import settings

    try:
        job = Job.objects.get(pk=job_id)
    except Job.DoesNotExist:
        answer_callback(callback_id, 'Вакансия не найдена')
        return

    try:
        if action == 'approve':
            job.status = 'approved'
            job.is_active = True
            job.save()
            answer_callback(callback_id, '✅ Одобрено!')
            send_message(chat_id, f'✅ Вакансия "{esc(job.title)}" одобрена и опубликована!')
            if job.author and job.author.email:
                send_mail(
                    subject='Ваша вакансия одобрена — Nexbit',
                    message=(
                        f'Здравствуйте, {job.author.get_full_name() or job.author.username}!\n\n'
                        f'Ваша вакансия "{job.title}" одобрена и опубликована на портале.\n\n'
                        f'Nexbit — портал вакансий Кыргызстана'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[job.author.email],
                    fail_silently=True
                )

        elif action == 'reject':
            job.status = 'rejected'
            job.is_active = False
            job.save()
            answer_callback(callback_id, '❌ Отклонено!')
            send_message(chat_id, f'❌ Вакансия "{esc(job.title)}" отклонена.')
            if job.author and job.author.email:
                send_mail(
                    subject='Ваша вакансия отклонена — Nexbit',
                    message=(
                        f'Здравствуйте, {job.author.get_full_name() or job.author.username}!\n\n'
                        f'К сожалению, ваша вакансия "{job.title}" не прошла модерацию.\n\n'
                        f'Nexbit — портал вакансий Кыргызстана'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[job.author.email],
                    fail_silently=True
                )
    except Exception as e:
        logger.error(f'process_action error: {e}')
        answer_callback(callback_id, 'Произошла ошибка')


def handle_updates():
    offset = None
    logger.info('Nexbit Telegram bot polling started')
    while True:
        try:
            params = {'timeout': 30}
            if offset:
                params['offset'] = offset
            resp = requests.get(f'{TELEGRAM_API}/getUpdates', params=params, timeout=35)
            if not resp.ok:
                logger.error(f'getUpdates failed: {resp.text}')
                time.sleep(5)
                continue

            for update in resp.json().get('result', []):
                offset = update['update_id'] + 1
                try:
                    callback = update.get('callback_query')
                    if callback:
                        chat_id = str(callback['from']['id'])
                        data_str = callback['data']

                        if chat_id != ADMIN_CHAT_ID:
                            answer_callback(callback['id'], '⛔ Нет доступа.')
                            continue

                        if data_str.startswith('approve_'):
                            job_id = int(data_str.replace('approve_', ''))
                            process_action('approve', job_id, callback['id'], chat_id)

                        elif data_str.startswith('reject_'):
                            job_id = int(data_str.replace('reject_', ''))
                            process_action('reject', job_id, callback['id'], chat_id)

                except Exception as e:
                    logger.error(f'Error processing update: {e}')

        except Exception as e:
            logger.error(f'handle_updates outer error: {e}')
            time.sleep(5)


def start_bot():
    global _bot_started
    with _bot_lock:
        if _bot_started:
            logger.warning('Bot already started, skipping')
            return
        _bot_started = True

    logger.info('Starting Nexbit Telegram bot thread')
    t = threading.Thread(target=handle_updates, daemon=True, name='NexbitBot')
    t.start()