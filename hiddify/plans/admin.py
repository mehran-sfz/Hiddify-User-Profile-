from django.contrib import admin
from .models import Plan

@admin.register(Plan)
class UserAdmin(admin.ModelAdmin):
    list_display = ['trafic', 'duration', 'price']
    