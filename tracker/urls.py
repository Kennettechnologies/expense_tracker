from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.index, name='index'),
    path('signup/', views.signup, name='signup'),
    path('profile/', views.profile, name='profile'),

    path('transactions/', views.transactions, name='transactions'),
    path('transactions/new/', views.transaction_create, name='transaction_create'),
    path('transactions/<int:pk>/edit/', views.transaction_edit, name='transaction_edit'),
    path('transactions/<int:pk>/delete/', views.transaction_delete, name='transaction_delete'),
    path('transactions/<int:pk>/duplicate/', views.transaction_duplicate, name='transaction_duplicate'),
    path('export-csv/', views.export_transactions_csv, name='export_csv'),

    path('dashboard/', views.dashboard, name='dashboard'),
    path('import-csv/', views.import_transactions_csv, name='import_csv'),
    path('budgets/', views.budgets_list, name='budgets'),
    path('budgets/new/', views.budget_create, name='budget_create'),
    path('budgets/<int:pk>/edit/', views.budget_edit, name='budget_edit'),
    path('budgets/<int:pk>/delete/', views.budget_delete, name='budget_delete'),
    path('recurrings/', views.recurring_list, name='recurrings'),
    path('recurrings/new/', views.recurring_create, name='recurring_create'),
    path('recurrings/<int:pk>/edit/', views.recurring_edit, name='recurring_edit'),
    path('recurrings/<int:pk>/delete/', views.recurring_delete, name='recurring_delete'),
    path('transactions/<int:pk>/split/', views.split_create, name='split_create'),
    path('splits/<int:pk>/edit/', views.split_edit, name='split_edit'),
    path('splits/<int:pk>/delete/', views.split_delete, name='split_delete'),
    
    # Phase 2: Advanced Features
    # Transaction Templates
    path('templates/', views.templates_list, name='templates'),
    path('templates/new/', views.template_create, name='template_create'),
    path('templates/<int:pk>/use/', views.template_use, name='template_use'),
    path('templates/<int:pk>/delete/', views.template_delete, name='template_delete'),
    
    # Savings Goals
    path('goals/', views.goals_list, name='goals'),
    path('goals/new/', views.goal_create, name='goal_create'),
    path('goals/<int:pk>/', views.goal_detail, name='goal_detail'),
    path('goals/<int:pk>/contribute/', views.goal_contribute, name='goal_contribute'),
    path('goals/<int:pk>/delete/', views.goal_delete, name='goal_delete'),
    
    # Bills & Reminders
    path('bills/', views.bills_list, name='bills'),
    path('bills/new/', views.bill_create, name='bill_create'),
    path('bills/<int:pk>/pay/', views.bill_pay, name='bill_pay'),
    path('bills/<int:pk>/delete/', views.bill_delete, name='bill_delete'),
    
    # Advanced Transaction Management
    path('transactions/advanced/', views.transactions_advanced, name='transactions_advanced'),
    path('transactions/bulk-action/', views.transactions_bulk_action, name='transactions_bulk_action'),
    
    # Phase 3: Enhanced Features
    # Enhanced Dashboard & Analytics
    path('dashboard/enhanced/', views.dashboard_enhanced, name='dashboard_enhanced'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('financial-health/', views.financial_health_view, name='financial_health'),
    path('reports/pdf/', views.generate_pdf_report_view, name='generate_pdf_report'),
    
    # Advanced Search & Calendar
    path('search/advanced/', views.advanced_search_view, name='advanced_search'),
    path('calendar/', views.calendar_view, name='calendar_view'),
    
    # Voice Input
    path('voice/', views.voice_transaction_view, name='voice_transaction'),
    
    # AI Insights
    path('ai-insights/', views.ai_insights_view, name='ai_insights'),
]
