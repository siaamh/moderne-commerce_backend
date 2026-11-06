from django.urls import path
from .chat_views import ChatView

urlpatterns = [
    path("chat/", ChatView.as_view(), name="chat"),
]
