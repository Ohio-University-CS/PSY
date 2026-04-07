"""
URL configuration for the canBet project.

Page routes  →  serve HTML templates
API routes   →  JSON endpoints consumed by JS fetch() in the templates
"""

from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from canbet_app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('privacy/', views.privacy, name='privacy'),
    path('about/', views.about, name='about'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('main/', views.main, name='main'),
    path('inventory/', views.inventory, name='inventory'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('profile/', views.profile, name='profile'),
    path('settings/', views.settings_view, name='settings'),
    path('shop/', views.shop, name='shop'),
    path('crate/', views.crate, name='crate'),
    path('api/me/', views.api_me, name='api_me'),
    path('api/crate/open/', views.api_open_crate, name='api_open_crate'),
    path('api/inventory/', views.api_inventory, name='api_inventory'),
    path('api/token-login/', views.api_token_login, name='api_token_login'),
    path('api/leaderboard/', views.api_leaderboard, name='api_leaderboard'),
    path('api/recent-opens/', views.api_recent_opens, name='api_recent_opens'),
    path('api/lootboxes/', views.api_lootboxes, name='api_lootboxes'),
    path('api/lootbox/buy/', views.api_buy_lootbox, name='api_buy_lootbox'),
    path('register/', views.register_view, name='register'),
    path('delete-account/', views.delete_account, name='delete_account'),
    path('api/canvas/sync/', views.api_canvas_sync, name='api_canvas_sync'),
    path('api/shop/buy/', views.api_buy_item, name='api_buy_item'),
    path('api/crate-pool/<str:crate_type>/', views.api_crate_pool, name='api_crate_pool'),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
