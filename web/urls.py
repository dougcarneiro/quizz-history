from django.urls import path
from . import views

urlpatterns = [
    path(r'', views.menu),
    path(r'game/new', views.new_game),
    path(r'game/stop', views.stop_game),
    path(r'game/play', views.play_game),
    path(r'game/setup', views.setup_game),
    path(r'game/answer', views.answer_game),
    path(r'game/challenge/sort', views.sort_challenge),
]
