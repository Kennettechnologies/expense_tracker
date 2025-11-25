import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expense_tracker.settings')

app = Celery('expense_tracker')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Schedule for periodic tasks
app.conf.beat_schedule = {
    'check-budget-alerts': {
        'task': 'tracker.tasks.check_budget_alerts',
        'schedule': 3600.0,  # Run every hour
    },
    'check-bill-reminders': {
        'task': 'tracker.tasks.check_bill_reminders',
        'schedule': 3600.0,  # Run every hour
    },
    'calculate-financial-health': {
        'task': 'tracker.tasks.calculate_financial_health_scores',
        'schedule': 86400.0,  # Run daily
    },
    'generate-monthly-reports': {
        'task': 'tracker.tasks.generate_monthly_reports',
        'schedule': 86400.0,  # Run daily (but only executes on 1st of month)
    },
    'check-goal-milestones': {
        'task': 'tracker.tasks.check_savings_goal_milestones',
        'schedule': 3600.0,  # Run every hour
    },
    'detect-unusual-spending': {
        'task': 'tracker.tasks.detect_unusual_spending',
        'schedule': 86400.0,  # Run daily
    },
}

app.conf.timezone = 'UTC'

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
