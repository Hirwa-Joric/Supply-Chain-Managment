from django.urls import path
from . import views
from .views import branch_list, add_branch, add_menu

urlpatterns = [
    path('dashboard/', views.restaurant_dashboard, name='restaurant_dashboard'),
    path('branch/<int:branch_id>/', views.branch_menus, name='branch_menus'),
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    path('add-branch/', add_branch, name='add_branch'),

    path('add-menu/', add_menu, name='add_menu'),  # For general menu addition
    path('add-menu/<int:branch_id>/', add_menu, name='add_menu_for_branch'),
    path('', branch_list, name='branch_list'),
]
