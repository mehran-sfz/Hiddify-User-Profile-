from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from task_manager.hiddify_actions import generate_qr_code, on_off_user
from adminlogs.action import add_admin_log


from django.db.models import Sum
from accounts.models import Profile, CustomUser
from client_actions.models import Config, Order
from task_manager.models import HiddifyUser, HiddifyAccessInfo
from plans.models import Plan
from adminlogs.models import AdminLog, Message
from telegram_bot.models import Telegram_Bot_Info

from datetime import date, datetime
from django.utils import timezone

# ------------------------------------ User Panel Views ------------------------------------#


def LoginView(request):

    if request.method == 'POST':

        if request.POST.get('form_id') == 'login-form':

            phone_number = request.POST.get('phone')
            password = request.POST.get('password')

            # Authenticate user by username (phone) and password
            try:
                user = authenticate(
                    request, phone_number=phone_number, password=password)
            except (ValueError, ValidationError) as e:
                messages.error(request, f'ارور در احراز هویت: {str(e)}')
                return redirect('/login-register/')

            if user is not None:
                login(request, user)
                if user.is_staff:
                    return redirect('/admin-panel/')
                else:
                    return redirect('/home/')
            else:
                messages.error(request, 'نام کاربری یا رمز عبور اشتباه است')

        elif request.POST.get('form_id') == 'register-form':

            name = request.POST.get('name')
            family = request.POST.get('family')
            phone = request.POST.get('phone')
            password = request.POST.get('password')
            confirm_password = request.POST.get('confirm_password')
            invited_code = request.POST.get('invite_code')

            if password != confirm_password:
                messages.error(request, "پسوورد ها یکی نیستند")
                return redirect('/login-register/')

            # Check if phone number is already registered
            if not CustomUser.objects.filter(phone_number=phone).exists():
                try:
                    # Try to create a new user
                    user = CustomUser.objects.create_user(
                        phone_number=phone, password=password, first_name=name, last_name=family)
                except (ValueError, ValidationError) as e:
                    messages.error(request, f'ارور در ساخت یوزر: {str(e)}')
                    return redirect('/login-register/')
                except Exception as e:
                    messages.error(request, f'ارور در ساخت یوزر: {str(e)}')
                    return redirect('/login-register/')

                invited_user = None
                if invited_code:
                    try:
                        # or any other field you use to identify users
                        invited_user = CustomUser.objects.get(
                            phone_number=invited_code)
                    except CustomUser.DoesNotExist:
                        messages.error(
                            request, "کاربری با چنین کد دعوتی وجود ندارد")
                        return redirect('/login-register/')

                try:
                    profile = Profile(user=user, invited_by=invited_user)
                    profile.save()
                    messages.success(request, "کاربر با موفقیت ساخته شد")
                except ValueError as e:
                    user.delete()
                    messages.error(
                        request, f'ارور در ساخت پروفیل کاربر: {str(e)}')
                    return redirect('/login-register/')

                # Log the user in after successful registration
                login(request, user)
                # Redirect to home after successful login
                return redirect('/home/')
            else:
                messages.error(request, "شماره تلفن قبلا ثبت شده است")
                return redirect('/login-register/')

    if request.method == 'GET':

        if request.user.is_authenticated:
            return redirect('home')
        else:
            return render(request, 'user/login_register.html')

    # Fallback if neither POST nor GET method matched
    return render(request, 'user/login_register.html')


def LogoutView(request):

    if request.user.is_authenticated:

        logout(request)
        return redirect('/login-register/')
    else:
        return redirect('/login-register/')


def OrdersView(request):
    if not request.user.is_authenticated:
        return redirect('/login-register/')

    if request.method == 'GET':

        orders = request.user.orders.all()
        order_uuids = request.user.config.values_list('uuid', flat=True)
        hiddify_entries = HiddifyUser.objects.filter(
            uuid__in=order_uuids).values('uuid', 'name')
        uuid_to_name = {entry['uuid']: entry['name']
                        for entry in hiddify_entries}

        # Attach the Hiddify name to each order (add a custom attribute 'name')
        for order in orders:
            # Get name or None if not found
            order.name = uuid_to_name.get(order.config.uuid, None)

        invite_code = request.user.profile.invite_code

        return render(request, 'user/orders.html', {'orders': orders, 'invite_code': invite_code})


class HomeView(TemplateView):
    template_name = 'user/home_active.html'

    def get(self, request, *args, **kwargs):
        # Check if the user is authenticated
        if not request.user.is_authenticated:
            return redirect('/login-register/')

        elif request.user.is_staff:
            return redirect('/admin/')

        # Check if user has an active profile
        elif not request.user.profile.is_active:
            return render(request, 'user/home_deactive.html')

        # Fetch the user's plans and configurations
        plans = Plan.objects.all()
        user_configs = Config.objects.filter(user=request.user)
        
        # Get all admin messages
        admin_messages = self.get_admin_messages()

        # get telegram bot info
        telegram_bot_info = self.get_telegram_bot_info(request)

        # check if the user has telegram_account or not
        telegram_account = False
        if request.user.telegram_account.exists():
            telegram_account = True
        else:
            telegram_account = False

        if not user_configs:
            return redirect('/buyconfig/')

        data_return = []
        for config in user_configs:
            hiddify_user = self.get_hiddify_user(config.uuid)
            if not hiddify_user:
                continue

            last_order = self.get_last_order(config)
            package_days = self.calculate_package_days(hiddify_user)
            subscriptionlink, qrcode = self.generate_subscription_data(
                config, hiddify_user)


            data_return.append({
                'name': hiddify_user.name,
                'current_usage': round(float(hiddify_user.current_usage_GB), 2),
                'is_active': hiddify_user.is_active,
                'last_online': hiddify_user.last_online,
                'left_trafic': round(float(hiddify_user.usage_limit_GB) - float(hiddify_user.current_usage_GB), 2),
                'package_days': package_days,
                'uuid': config.uuid,
                'qrcode': qrcode,
                'subscriptionlink': subscriptionlink,
                'last_order': last_order,
            })

        return_data = {
            'data': {'config': data_return},
            'invite_code': request.user.profile.invite_code,
            'telegram_id': telegram_account,
            'telegram_bot_info': telegram_bot_info,
            'user_uuid': request.user.profile.uuid,
            'plans': plans,
            'message_to_users': admin_messages,
        }
        return render(request, self.template_name, return_data)

    def get_hiddify_user(self, uuid):
        """Fetches the Hiddify user by UUID, with exception handling."""
        try:
            return HiddifyUser.objects.get(uuid=uuid)
        except HiddifyUser.DoesNotExist:
            messages.error(
                self.request, f'Error retrieving Hiddify user for config {uuid}')
            return None
        except Exception as e:
            messages.error(
                self.request, f'Error retrieving Hiddify user for config {uuid}: {str(e)}')
            return None

    def get_admin_messages(self):
        """Fetches the admin messages for the user."""
        return Message.objects.filter(status=True).order_by('-id')

    def get_last_order(self, config):
        """Fetches and processes the last order for a given configuration."""
        order = config.order_configs.filter(user=self.request.user).last()
        if order:
            payment_status = self.get_payment_status(order)
            return {
                'plan': order.plan,
                'pk_order': order.pk,
                'status': payment_status,
                'pending': order.pending,
            }
        return None

    def get_payment_status(self, order):
        """Determine the status of a payment related to an order."""
        # payment = order.order_payment.exists():
        payment = getattr(order, 'order_payment', None)
        if payment and payment.validated:
            return 'payed'
        elif payment and not payment.validated:
            return 'payed under checking'
        elif not order.status and not order.pending:
            
            
            # how many dayes passed from the creation date
            remaining_days = 5 - (date.today() - order.created_date.date()).days
            
            return remaining_days
        elif not order.status and order.pending:
            return 'pending'
        else:
            return 'not paid'

    def calculate_package_days(self, hiddify_user):
        """Calculates the remaining days for a user's package."""
        if hiddify_user.start_date:
            return hiddify_user.package_days - (date.today() - hiddify_user.start_date).days
        return None

    def generate_subscription_data(self, config, hiddify_user):
        """Generates the subscription link and QR code for a user."""

        try:
            hiddify_access_info = HiddifyAccessInfo.objects.latest('created_date')
        except HiddifyAccessInfo.DoesNotExist:
            return None

        subscriptionlink = f'{hiddify_access_info.panel_admin_domain}/{hiddify_access_info.sub_proxy_path}/{config.uuid}/#{hiddify_user.name}'
        qrcode = generate_qr_code(subscriptionlink)
        return subscriptionlink, qrcode

    def get_telegram_bot_info(self, request):
        try:
            return Telegram_Bot_Info.objects.latest('created_date').bot_name
        except Telegram_Bot_Info.DoesNotExist:
            return None
        except Exception as e:
            add_admin_log(
                action=f'Error in fetching Telegram bot info: {str(e)}', category='admin', user=request.user)
            return None


def ByConfig(request):

    if not request.user.is_authenticated:
        return redirect('/login-register/')

    if request.method == 'GET':

        try:
            plan = Plan.objects.all()
        except Plan.DoesNotExist:
            messages.error(request, 'ارور در دریافت پلن ها')
            return redirect('/home/')
        except Exception as e:
            add_admin_log(
                action=f'Error in fetching plans: {str(e)}', category='admin', user=request.user)
            messages.error(request, f'ارور کد 12')
            return redirect('/home/')

        try:
            invite_code = request.user.profile.invite_code
        except Exception as e:
            add_admin_log(
                action=f'Error in fetching invite code: {str(e)}', category='admin', user=request.user)
            messages.error(request, f'ارور کد 13')
            return redirect('/home/')

        return render(request, 'user/buy_config.html', {'plans': plan, 'invite_code': invite_code})

# ------------------------------------ Admin Panel Views ------------------------------------#

def AdminPanelView(request):

    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('/home/')

    if request.method == 'GET':

        hiddifyUsers_count = HiddifyUser.objects.all().count()
        plan_count = Plan.objects.all().count()
        not_payed_orders_count = Order.objects.filter(
            status=False, pending=False).count()
        pending_orders_count = Order.objects.filter(pending=True).count()
        log_count = AdminLog.objects.all().count()
        admin_messages_count = Message.objects.filter(status=True).count()

        # Get tha first day of the month 
        last_month = timezone.now().replace(day=1)

        # Query all orders that are not older than 5 days ago, still pending, and not paid
        last_month_orders = Order.objects.filter(
            created_date__gte=last_month,  # Orders created in this month
            status=True,  # Order not paid
        )

        alltime_orders = Order.objects.filter(status=True)
        total_sell_last_month = last_month_orders.aggregate(
            total=Sum('plan__price'))
        total_sell = alltime_orders.aggregate(total=Sum('plan__price'))

        data_return = {
            'hiddifyUsers_count': hiddifyUsers_count,
            'plan_count': plan_count,
            'not_payed_orders_count': not_payed_orders_count,
            'pending_orders_count': pending_orders_count,
            'log_count': log_count,
            'total_sell_last_month': 0 if total_sell_last_month['total']==None else total_sell_last_month['total'],
            'total_sell': 0 if total_sell['total']==None else total_sell['total'],
            'admin_messages_count': admin_messages_count,
        }

        return render(request, 'admin/admin_home.html', data_return)

    return redirect('/admin-panel/')


def AdminUsersView(request):
    # check if user is admin or not
    if not request.user.is_authenticated and not request.user.is_staff:
        return redirect('/login-register/')

    if request.method == "GET":
        profiles = Profile.objects.all()

        return render(request, 'admin/admin_users.html', {'profiles': profiles})

    elif request.method == "POST":

        # Check if the request is a PUT or DELETE
        action = request.POST.get('action')

        if action == 'PUT':

            user_uuid = request.POST.get('user_uuid')
            if not user_uuid:
                messages.error(request, 'لطفا یوزر انتخاب کنید')
                return redirect('/admin-panel/users')

            # Toggle the user's active status
            try:
                profile = Profile.objects.get(uuid=user_uuid)

                if profile.is_active:
                    profile.is_active = False
                    messages.success(request, 'با موفقیت غیر فعال شد')
                else:
                    profile.is_active = True
                    messages.success(request, 'با موفقیت فعال شد')
                profile.save()

            except Profile.DoesNotExist:
                messages.error(request, 'کاربر یافت نشد')
                return redirect('/admin-panel/users')

        elif action == "DELETE":

            user_pk = request.POST.get('user_pk')

            if not user_pk:
                messages.error(request, 'لطفا یوزر انتخاب کنید')
                return redirect('/admin-panel/users')

            # Delete the user
            try:
                User = CustomUser.objects.get(pk=user_pk)
                User.delete()
                messages.success(request, 'با موفقیت حذف شد')
            except Profile.DoesNotExist:
                messages.error(request, 'کاربر یافت نشد')
                return redirect('/admin-panel/users')

    return redirect('/admin-panel/users')


def AdminConfigsView(request):

    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('/home/')

    if request.method == 'GET':
        
        filter = request.GET.get('filter')
        if filter == 'active':
            configs = HiddifyUser.objects.filter(enable=True)

        elif filter == 'inactive':
            configs = HiddifyUser.objects.filter(enable=False)

        else:
            configs = HiddifyUser.objects.all()
            
        return render(request, 'admin/admin_configs.html', {'configs': configs, 'filter': filter})

    elif request.method == 'POST':
        action = request.POST.get('action')

        if action == 'on_off':

            hidify_user_uuid = request.POST.get('hidify_user_uuid')
            if not hidify_user_uuid:
                messages.error(request, 'لطفا یوزر انتخاب کنید')
                return redirect('/admin-panel/configs')

            try:
                hiddify_user = HiddifyUser.objects.get(uuid=hidify_user_uuid)
                if hiddify_user.enable:
                    status = on_off_user(hiddify_user.uuid, enable=False)
                    if status:
                        hiddify_user.enable = False
                        messages.warning(request, 'با موفقیت غیر فعال شد')
                else:
                    status = on_off_user(hiddify_user.uuid, enable=True)
                    if status:
                        hiddify_user.enable = True
                        messages.success(request, 'با موفقیت فعال شد')
                hiddify_user.save()
            except HiddifyUser.DoesNotExist:
                messages.error(request, 'کاربر یافت نشد')
                return redirect('/admin-panel/configs')

    return redirect('/admin-panel/configs')


def AdminOrdersView(request):
    # check if user is admin or not
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('/home/')

    if request.method == 'GET':

        # Fetch all orders
        orders = Order.objects.all().order_by('-id')

        # Fetch the UUIDs from the Config model and related Hiddify user data
        order_uuids = Config.objects.values_list('uuid', flat=True)
        hiddify_entries = HiddifyUser.objects.filter(
            uuid__in=order_uuids).values('uuid', 'name')

        # Create a dictionary mapping UUIDs to Hiddify user names
        uuid_to_name = {entry['uuid']: entry['name']
                        for entry in hiddify_entries}

        # Attach the Hiddify name to each order (add a custom attribute 'name')
        for order in orders:
            # Safely access order.config and order.config.uuid, handling cases where they may be None
            # payment = order.config.exists():
            order_uuid = getattr(order.config, 'uuid', None)
            # Get the name associated with the UUID, or None if not found
            order.name = uuid_to_name.get(order_uuid, None)

        return render(request, 'admin/admin_orders.html', {'orders': orders})


def AdminPlansView(request):

    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('/home/')

    if request.method == 'GET':
        plans = Plan.objects.all()
        return render(request, 'admin/admin_plans.html', {'plans': plans})

    return render(request, 'admin/admin_plans.html')


def AdminLogsView(request):

    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('/home/')

    if request.method == 'GET':
        category = request.GET.get('category')
        page = request.GET.get('page', 1)  # شماره صفحه‌ای که از URL می‌گیریم. پیش‌فرض 1

        categories = [cat[0] for cat in AdminLog.ACTION_CATEGORIES]
        if category and category in categories:
            logs = AdminLog.objects.filter(category=category).order_by('-id')
        else:
            logs = AdminLog.objects.all().order_by('-id')

        paginator = Paginator(logs, 10)  # صفحه‌بندی با 10 آیتم در هر صفحه
        try:
            logs_paginated = paginator.page(page)
        except PageNotAnInteger:
            logs_paginated = paginator.page(1)  # اگر شماره صفحه معتبر نبود، به صفحه اول برمی‌گردد
        except EmptyPage:
            logs_paginated = paginator.page(paginator.num_pages)  # اگر شماره صفحه خارج از بازه بود، آخرین صفحه را نشان می‌دهد

        total_logs = logs.count()
        return render(request, 'admin/admin_logs.html', {
            'logs': logs_paginated,  # فقط لاگ‌های مربوط به صفحه فعلی
            'total_logs': total_logs,
            'categories': categories,
            'selected_category': category,
            'paginator': paginator,  # اضافه کردن شیء paginator برای رندر کردن لینک‌های ناوبری
        })

    return redirect('/admin-panel/logs')


def AdminMessageView(request):
    
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('/home/')
    
    if request.method == 'GET':
        
        admin_messages = Message.objects.all().order_by('-id')
        
        return render(request, 'admin/admin_messages.html', {'admin_messages': admin_messages})
    
    return redirect('/admin-panel/messages')