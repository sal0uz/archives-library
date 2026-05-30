from django.utils import timezone
from django.conf import settings

class OnlineTrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            threshold = getattr(settings, 'ONLINE_THRESHOLD', 300)
            last = request.user.last_online
            if (timezone.now() - last).total_seconds() > 60:
                from .models import User
                User.objects.filter(pk=request.user.pk).update(last_online=timezone.now())
        return self.get_response(request)
