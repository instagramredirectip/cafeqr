from django.urls import path
from . import views_customer, views_owner, views_public

urlpatterns = [
    # Platform Gateway
    path('', views_public.platform_home_view, name='platform_home'),

    # Customer-Facing Restaurant Pages
    path('r/<slug:slug>/menu/', views_customer.restaurant_menu_view, name='restaurant_menu'),
    path('r/<slug:slug>/api/food/<int:item_id>/', views_customer.food_item_detail_api, name='food_item_detail_api'),
    path('r/<slug:slug>/api/checkout/', views_customer.checkout_submit_api, name='checkout_submit_api'),
    path('r/<slug:slug>/order/<uuid:access_token>/', views_customer.order_status_view, name='order_status'),
    path('r/<slug:slug>/api/order-status/<uuid:access_token>/', views_customer.order_status_api, name='order_status_api'),

    # Owner & Staff Portal
    path('owner/login/', views_owner.owner_login_view, name='owner_login'),
    path('owner/logout/', views_owner.owner_logout_view, name='owner_logout'),
    path('owner/dashboard/', views_owner.owner_dashboard, name='owner_dashboard'),
    path('owner/api/live-orders/', views_owner.owner_live_orders_api, name='owner_live_orders_api'),
    
    # Orders Management
    path('owner/orders/', views_owner.owner_orders_list, name='owner_orders_list'),
    path('owner/orders/<int:order_id>/', views_owner.owner_order_detail, name='owner_order_detail'),
    path('owner/api/orders/<int:order_id>/status/', views_owner.owner_order_update_status_api, name='owner_order_update_status_api'),

    # Menu & Category Management
    path('owner/menu/', views_owner.owner_menu_list, name='owner_menu_list'),
    path('owner/menu/add/', views_owner.owner_food_add, name='owner_food_add'),
    path('owner/menu/<int:item_id>/edit/', views_owner.owner_food_edit, name='owner_food_edit'),
    path('owner/menu/<int:item_id>/toggle-availability/', views_owner.owner_food_toggle_availability, name='owner_food_toggle_availability'),
    path('owner/menu/<int:item_id>/delete/', views_owner.owner_food_delete, name='owner_food_delete'),
    path('owner/categories/', views_owner.owner_categories, name='owner_categories'),
    path('owner/categories/<int:category_id>/delete/', views_owner.owner_category_delete, name='owner_category_delete'),

    # QR Codes & Tables Management
    path('owner/qr/', views_owner.owner_qr_management, name='owner_qr_management'),
    path('owner/tables/<int:table_id>/delete/', views_owner.owner_table_delete, name='owner_table_delete'),
    path('owner/qr/print/', views_owner.owner_table_print_view, name='owner_qr_print_general'),
    path('owner/qr/print/<int:table_id>/', views_owner.owner_table_print_view, name='owner_qr_print_table'),

    # Settings
    path('owner/settings/', views_owner.owner_settings, name='owner_settings'),
]

