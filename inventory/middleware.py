import time
from django.db import connection
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
import logging

logger = logging.getLogger('inventory_operations')

class InventoryOperationsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip monitoring for static/media files and admin urls
        if any(url in request.path for url in ['/static/', '/media/', '/admin/']):
            return self.get_response(request)

        start_time = time.time()
        
        # Process the request
        response = self.get_response(request)
        
        # Only monitor inventory-related operations
        if '/inventory/' in request.path:
            duration = time.time() - start_time
            self.log_operation(request, response, duration)
            self.update_metrics(request, duration)
        
        return response

    def log_operation(self, request, response, duration):
        """Log inventory operations for monitoring"""
        if not request.user.is_authenticated:
            return

        log_data = {
            'timestamp': timezone.now().isoformat(),
            'user': request.user.username,
            'method': request.method,
            'path': request.path,
            'status_code': response.status_code,
            'duration': round(duration, 3),
            'ip': self.get_client_ip(request)
        }

        # Add query count if debug is enabled
        if settings.DEBUG:
            log_data['query_count'] = len(connection.queries)

        logger.info('Inventory Operation', extra=log_data)

    def update_metrics(self, request, duration):
        """Update real-time metrics for monitoring"""
        current_hour = timezone.now().strftime('%Y-%m-%d-%H')
        
        # Update operation counts
        ops_key = f'inventory_ops_{current_hour}'
        cache.incr(ops_key, default=0)
        
        # Update average response time
        time_key = f'inventory_time_{current_hour}'
        current_avg = cache.get(time_key, {'count': 0, 'avg': 0})
        new_count = current_avg['count'] + 1
        new_avg = ((current_avg['avg'] * current_avg['count']) + duration) / new_count
        cache.set(time_key, {'count': new_count, 'avg': new_avg}, 3600)

        # Track slow operations
        if duration > 1.0:  # Operations taking more than 1 second
            slow_ops_key = f'slow_ops_{current_hour}'
            slow_ops = cache.get(slow_ops_key, [])
            slow_ops.append({
                'path': request.path,
                'duration': duration,
                'timestamp': timezone.now().isoformat()
            })
            cache.set(slow_ops_key, slow_ops[-10:], 3600)  # Keep last 10 slow operations

    def get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')