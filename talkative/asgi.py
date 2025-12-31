import os
from django.core.asgi import get_asgi_application

# 1. Set settings module FIRST
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'talkative.settings')

# 2. Initialize the Django ASGI application early
# This ensures the AppRegistry is populated before importing consumers/middleware
django_asgi_app = get_asgi_application()

# 3. Import Channels components AFTER get_asgi_application()
from channels.routing import ProtocolTypeRouter, URLRouter
from chat.middleware import TokenAuthMiddlewareStack
import chat.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": TokenAuthMiddlewareStack(
        URLRouter(
            chat.routing.websocket_urlpatterns
        )
    ),
})
