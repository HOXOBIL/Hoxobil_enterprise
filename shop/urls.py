from django.urls import path
from . import views

urlpatterns = [
    # Homepage
    path('', views.home, name='home'),

    # Product views
    path('products/', views.fetch_printify_products, name='product_list'),
    path('product/<str:product_id>/', views.product_detail, name='product_detail'),

    # Cart URLs
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/add/<str:product_id>/', views.add_to_cart, name='add_to_cart'), 
    path('cart/remove/<str:cart_key>/', views.remove_from_cart, name='remove_from_cart'),

    # Checkout URLs
    path('checkout/', views.checkout_page, name='checkout'),
    path('checkout/submit/', views.checkout_submit, name='checkout_submit'), 

    # Paystack Callback URL
    path('paystack/callback/', views.paystack_callback, name='paystack_callback'),

    # Order Status Pages
    path('order/success/<str:order_reference>/', views.order_success, name='order_success'),
    path('order/failure/', views.order_failure, name='order_failure'), 
    path('order/failure/<path:error_message>/', views.order_failure, name='order_failure_specific'),

    # Product Synchronization URL
    path('sync/', views.sync_products_view, name='sync_products'),

    # Competition URLs
    path('competition/', views.competition_page, name='competition_page'),
    path('competition/submit_code/', views.submit_competition_code, name='submit_competition_code'),

    # Privacy Policy URL
    path('privacy-policy/', views.privacy_policy_view, name='privacy_policy'),

    # +++ NEW AUTHENTICATION URLS +++
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    # Add this to your urlpatterns in shop/urls.py
path('terms-of-service/', views.terms_of_service_view, name='terms_of_service'),
    path('logout/', views.logout_view, name='logout'),
]
