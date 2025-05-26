from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from plans.models import Plan
from adminlogs.action import add_admin_log



def Add_Edit_PlanView(request):
    
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('/home/')
    
    if request.method == 'POST':
        
        trafic = request.POST.get('trafic')
        duration = request.POST.get('duration')
        price = request.POST.get('price')
        create_or_update = request.POST.get('create_or_update')
        
        if not trafic or not duration or not price or not create_or_update:
            messages.error(request, 'لطفا همه ی فیلد ها را پر کنید!')
            return redirect('/admin-panel/plans')
        
        try:
            int(trafic)
            int(duration)
            int(price)
        except:
            messages.error(request, 'لطفا فیلد های ترافیک، مدت زمان و قیمت را به عدد وارد کنید!')
            return redirect('/admin-panel/plans')
        
        if create_or_update == 'new':
            
            try:
                Plan.objects.create(trafic=trafic, duration=duration, price=price)
                messages.success(request, 'با موفقیت ایجاد شد')
            except Exception as e:
                add_admin_log(action=f'Error in creating new plan: {str(e)}', category='admin', user=request.user)
                messages.error(request, 'ارور در ساخت پلن جدید:', str(e))
                return redirect('/admin-panel/plans')
            
        else:
            try:
                plan = Plan.objects.get(pk=create_or_update)
                plan.trafic = trafic
                plan.duration = duration
                plan.price = price
                plan.save()
                messages.success(request, 'با موفقیت ویرایش شد')
            except Plan.DoesNotExist:
                messages.error(request, 'پلن مورد نظر یافت نشد!')
                return redirect('/admin-panel/plans')
        
    if request.method == 'DELETE':
        
        plan_pk = request.POST.get('plan_pk')
        
        if not plan_pk:
            messages.error(request, 'لطفا همه ی فیلد ها را پر کنید!')
            return redirect('/admin-panel/plans')
        
        try:
            plan_pk = int(plan_pk)
        except Exception as e:
            messages.error(request, 'لطفا فیلد های ترافیک، مدت زمان و قیمت را به عدد وارد کنید!')
            return redirect('/admin-panel/plans')
        
        try:
            plan = Plan.objects.get(pk=plan_pk)
            plan.delete()
            messages.success(request, 'با موفقیت حذف شد')
        
        except Plan.DoesNotExist:
            messages.error(request, 'پلن مورد نظر یافت نشد!')
            return redirect('/admin-panel/plans')
            
        except Exception as e:
            messages.error(request, 'ارور در حذف پلن:', str(e))
            return redirect('/admin-panel/plans')
  
    return redirect('/admin-panel/plans')

def Delete_PlanView(request, pk):    
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('/home/')
    
    instance = get_object_or_404(Plan, pk=pk)
    
    if instance:
        instance.delete()
    
    messages.success(request, 'با موفقیت حذف شد')    
    return redirect('/admin-panel/plans')
    