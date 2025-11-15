from django.urls import path
from . import views

urlpatterns = [
    path("",views.home_page, name = "home"),
    path("register/", views.register_page, name = 'register'),
    path("login/", views.login_page, name = 'login'),
    path("logout/", views.logout_page, name = 'logout'),
    path("dashboard/", views.dashboard_page, name = 'dashboard'),
    path("results/", views.results_page, name = 'results'),
    # --- ADD THIS NEW PATH ---
    # The 'slug' will be the unique URL name of the election, e.g., /vote/general-election-2025/
    path('vote/<slug:election_slug>/', views.vote_page, name='vote_page'),
]
