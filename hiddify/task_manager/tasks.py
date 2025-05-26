import requests

from celery import shared_task

from django.utils import timezone
from django.db import transaction
from django.db.models import Q, F

from client_actions.models import Config, Order

from telegram_bot.models import Telegram_Bot_Info, Telegram_account
from task_manager.models import HiddifyUser, HiddifyAccessInfo
from task_manager.hiddify_actions import update_user, get_users, on_off_user, send_telegram_message

from adminlogs.action import add_admin_log

from datetime import datetime, timedelta
import logging


logger = logging.getLogger(__name__)

# ------------------ Tasks for fetching data from external API and updating the database ------------------

# Task to fetch data from external API and update the database
@shared_task()
def fetch_data_from_api():
    """ Fetch data from external API and update the database """

    try:
        hiddify_access_info = HiddifyAccessInfo.objects.latest('created_date')
    except HiddifyAccessInfo.DoesNotExist:
        logger.error("No objects found in HiddifyAccessInfo.")
        return 0
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return 0

    hiddify_api_key = hiddify_access_info.hiddify_api_key
    panel_admin_domain = hiddify_access_info.panel_admin_domain
    admin_proxy_path = hiddify_access_info.admin_proxy_path

    try:
        logger.info('Task started: fetching data from API...')
        users_data = get_users(
            hiddify_api_key, panel_admin_domain, admin_proxy_path)

        # Check if data was fetched successfully
        if not users_data:
            logger.error('Failed to fetch data from API.')
            return 'Failed to fetch data from API.'

        # Update your database
        with transaction.atomic():  # Ensure atomic DB operations
            for item in users_data:
                # Convert naive datetime to timezone-aware datetime
                last_online = item['last_online']
                last_reset_time = item['last_reset_time']
                start_date = item['start_date']

                # Convert to timezone-aware if it's a valid datetime
                if last_online:
                    last_online = timezone.make_aware(
                        datetime.fromisoformat(last_online))
                if last_reset_time:
                    last_reset_time = timezone.make_aware(
                        datetime.fromisoformat(last_reset_time))
                if start_date:
                    start_date = timezone.make_aware(
                        datetime.fromisoformat(start_date))

                # Update or create the HiddifyUser instance
                HiddifyUser.objects.update_or_create(
                    uuid=item['uuid'],  # Lookup field (unique identifier)
                    defaults={
                        'added_by_uuid': item['added_by_uuid'],
                        'current_usage_GB': item['current_usage_GB'],
                        'enable': item['enable'],
                        'is_active': item['is_active'],
                        'last_online': last_online,
                        'last_reset_time': last_reset_time,
                        'name': item['name'],
                        'package_days': item['package_days'],
                        'start_date': start_date,
                        'telegram_id': item['telegram_id'],
                        'usage_limit_GB': item['usage_limit_GB'],
                    }
                )
            logger.info('Task completed successfully.')
            return 'Database updated successfully.'

    except requests.exceptions.RequestException as e:
        logger.error(f'Error fetching data: {str(e)}')
        return f'Error fetching data: {str(e)}'

    except Exception as e:
        logger.error(f'Task failed with error: {str(e)}')
        return f'Task failed with error: {str(e)}'

# Task to check if user's subscription has expired and has a pending order or not
@shared_task()
def check_subscription_expiry():
    """ Check if user's subscription has expired and has a pending order or not """
    
    try:
        hiddify_access_info = HiddifyAccessInfo.objects.latest('created_date')
    except HiddifyAccessInfo.DoesNotExist:
        logger.error("No objects found in HiddifyAccessInfo.")
        return 0
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return 0

    hiddify_api_key = hiddify_access_info.hiddify_api_key
    panel_admin_domain = hiddify_access_info.panel_admin_domain
    admin_proxy_path = hiddify_access_info.admin_proxy_path

    # get all HiddifyUser that are expired
    expired_users = HiddifyUser.objects.filter( Q(enable=False) | Q(is_active=False) )

    for expired_user in expired_users:
        # Check if user has a pending order
        try:
            config = Config.objects.get(uuid=expired_user.uuid)

        except Config.DoesNotExist:
            logger.error(
                f'The site has no config with the given uuid. uuid: {expired_user.uuid} name: {expired_user.name}')
            continue

        order = config.order_configs.filter(
            user=config.user, config=config).last()

        if order and order.pending:
            # initiate the payment process
            update_respons = update_user(
                uuid=expired_user.uuid,
                days=order.plan.duration,
                trafic=order.plan.trafic,
                hiddify_api_key=hiddify_api_key,
                admin_proxy_path=admin_proxy_path,
                panel_admin_domain=panel_admin_domain,
                )
            

            if update_respons:
                # Update the order status
                order.pending = False
                order.save()
                logger.info(
                    f'User subscription updated: {expired_user.uuid} name: {expired_user.name}')
                continue

        else:
            # Disable the user account
            logger.info(
                f'User do not have a pending order: {expired_user.uuid} name: {expired_user.name}')
            continue

# Task to disable users that have not paid for their subscription
@shared_task(bind=True, max_retries=5)
def disable_not_paid_users(self):
    """ Disable users that have not paid for their subscription """
    
    try:
        hiddify_access_info = HiddifyAccessInfo.objects.latest('created_date')
    except HiddifyAccessInfo.DoesNotExist:
        logger.error("No objects found in HiddifyAccessInfo.")
        return 0
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return 0

    hiddify_api_key = hiddify_access_info.hiddify_api_key
    panel_admin_domain = hiddify_access_info.panel_admin_domain
    admin_proxy_path = hiddify_access_info.admin_proxy_path

    # Get 5 days ago date
    five_days_ago = timezone.now() - timedelta(days=5)

    # Query all orders that are older than 5 days, still pending, and not paid
    unpaid_orders = Order.objects.filter(
        updated_date__lte=five_days_ago,  # Orders created more than 5 days ago
        status=False,  # Order not paid
        pending=False   # Order not pending
    )

    for order in unpaid_orders:
        try:
            # Disable the user account
            on_off_user(uuid=order.config.uuid, enable=False,
                        hiddify_api_key=hiddify_api_key,
                        admin_proxy_path=admin_proxy_path,
                        panel_admin_domain=panel_admin_domain
                        )
            logger.info(f'User disabled: {order.config.uuid}')
            continue
        except Exception as e:
            logger.error(f'Error disabling user: {str(e)}')
            continue


# Task to send payment reminder message to users
@shared_task()
def send_payment_reminder_messsage():
    """ Send message trough telegram bot """

    telegram_info = Telegram_Bot_Info.objects.latest('created_date')
    if not telegram_info:
        logger.error("No objects found in Telegram_Bot_Info.")
        return 0

    # Get 3 days ago date
    three_days_ago = timezone.now() - timedelta(days=3)

    # Query all orders that are older than 3 days, still pending, and not paid
    unpaid_orders = Order.objects.filter(
        updated_date__lte=three_days_ago,  # Orders created more than 3 days ago
        status=False,  # Order not paid
        pending=False   # Order not pending
    )

    for unpaid_order in unpaid_orders:
        try:
            # Get the user's telegram account
            telegram_account = Telegram_account.objects.get(
                user=unpaid_order.user)
            
            #get the congig name
            config = HiddifyUser.objects.get(uuid=unpaid_order.config.uuid)

            # calculate the remaining days
            remaining_days = 7 - (timezone.now() - unpaid_order.updated_date).days

            # Create the message
            message = f"یادآوری پرداخت اشتراک {config.name} \nزمان باقی مانده : {remaining_days} روز \n پلن سفارش داده شده : {unpaid_order.plan}"

            # Send the payment reminder message
            send_telegram_message(
                token=telegram_info.token,
                chat_id=telegram_account.telegram_user_id,
                message=message,
            )
            logger.info(f'Message sent to {unpaid_order.user}')
            continue
        
        except Telegram_account.DoesNotExist:
            logger.error(f"No telegram account found for user: {unpaid_order.user}")
            continue

        except HiddifyUser.DoesNotExist:
            logger.error(f"No config_hiddify found for uuid: {unpaid_order.config.uuid}")
            add_admin_log(f'No config_hiddify found for user that order something with uuid: {unpaid_order.config.uuid} in tasks.py', 'user', unpaid_order.user)
            continue

        except Exception as e:
            logger.error(f'Error sending message: {str(e)}')
            add_admin_log(f'Error sending message: {str(e)} in tasks.py function : send_payment_reminder_messsage ', 'user', unpaid_order.user)
            continue



# Task to send a warning message to users that have not enough days to their subscription and current_usage_GB is more than usage_limit_GB
@shared_task()
def send_warning_message():
    """ send warning message to users that have not enough days to their subscription and current_usage_GB is more than usage_limit_GB """

    telegram_info = Telegram_Bot_Info.objects.latest('created_date')
    if not telegram_info:
        logger.error("No objects found in Telegram_Bot_Info.")
        return 0
    
    # Calculate the threshold for "less than 3 days from now"
    three_days_later = timezone.now().date() + timedelta(days=3)

    # Query for hiddify_accounts
    hiddify_accounts = HiddifyUser.objects.filter(
        Q(
            usage_limit_GB__isnull=False,  # Ensure usage_limit_GB is not null
            current_usage_GB__isnull=False,  # Ensure current_usage_GB is not null
            usage_limit_GB__lte=F('current_usage_GB') + 5  # Difference is less than 5
        ) | Q(
            end_date__isnull=False,  # Ensure end_date exists
            end_date__lte=three_days_later  # end_date is within 3 days
        )
    )

    for hiddify_account in hiddify_accounts:

        try:

            # get the users
            config = Config.objects.get(uuid=hiddify_account.uuid)

            # check if the config.user has an telegram_account or not
            if not config.user.telegram_account.exists():
                logger.warning(f"User {config.user} does not have a valid telegram_account.")
                continue
            
            telegram_account = Telegram_account.objects.get(user=config.user)

            # remind days
            remining_trafic = round(hiddify_account.usage_limit_GB - hiddify_account.current_usage_GB, 2)
            remind_days = (hiddify_account.end_date - timezone.now().date()).days
            if remind_days <= 2 :
                message = f"یادآوری تمدید اشتراک {hiddify_account.name} \n زمان باقی مانده : {remind_days} روز \n مصرف فعلی : {round(hiddify_account.current_usage_GB, 2)} GB \n سقف بسته : {hiddify_account.usage_limit_GB} GB"

            elif remining_trafic <= 5:
                message = f"یادآوری تمدید اشتراک {hiddify_account.name} \n زمان باقی مانده : {remind_days} روز \n ترافیک باقی مانده : {remining_trafic} GB"
            
            else:
                continue

            # Send the warning message
            send_telegram_message(
                token=telegram_info.token,
                chat_id=telegram_account.telegram_user_id,
                message=message,
            )
            logger.info(f'Message sent to {config.user}')

        except Config.DoesNotExist:
            logger.error(f"No user found for uuid: {hiddify_account.uuid}")
            continue

        except Config.Telegram_account:
            logger.error(f"No telegram info found for uuid: {hiddify_account.uuid}")
            continue

        except Exception as e:
            logger.error(f'Error sending message: {str(e)}')
            add_admin_log(f'Error sending message: {str(e)} in tasks.py function : send_warning_message', 'user', config.user)
            continue