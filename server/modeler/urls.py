from django.urls import path
from . import views

urlpatterns = [
    path('integrate/', views.integrate),
    path('go/', views.go),
    path('view/', views.view),
]