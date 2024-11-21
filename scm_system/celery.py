import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scm_system.settings')

app = Celery('scm_system')

# Use a string here instead of a file path so the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Configure periodic tasks
app.conf.beat_schedule = {
    'check-stock-levels': {
        'task': 'inventory.tasks.check_stock_levels',
        'schedule': crontab(hour='9', minute='0'),  # Run daily at 9 AM
    },
    'generate-purchase-orders': {
        'task': 'inventory.tasks.generate_purchase_orders',
        'schedule': crontab(hour='10', minute='0'),  # Run daily at 10 AM
    },
    'check-overdue-orders': {
        'task': 'inventory.tasks.check_overdue_orders',
        'schedule': crontab(hour='11', minute='0'),  # Run daily at 11 AM
    },
    'analyze-inventory-metrics': {
        'task': 'inventory.tasks.analyze_inventory_metrics',
        'schedule': crontab(0, 0, day_of_month='1'),  # Run monthly
    },
    'supplier-performance-review': {
        'task': 'inventory.tasks.supplier_performance_review',
        'schedule': crontab(0, 0, day_of_month='1'),  # Run monthly
    },
}