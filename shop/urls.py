from django.urls import path, include, reverse_lazy
from . import views
# Import Django's built-in auth views directly here for clarity
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Homepage
    path('', views.home, name='home'),

    # Product views
    path('products/', views.fetch_printify_products, name='product_list'),
    path('product/<str:product_id>/', views.product_detail, name='product_detail'),

    # --- NEW: Product Customizer URL ---
    path('products/customize/<int:product_id>/', views.product_customizer_view, name='product_customizer'),
    # --- END NEW URL ---

    # Cart URLs
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/add/<str:product_id>/', views.add_to_cart, name='add_to_cart'), 
    path('cart/add/custom/', views.add_to_cart_custom_design_ajax, name='add_to_cart_custom_design_ajax'), # Make sure this one is here
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

    # Static Pages URLs
    path('privacy-policy/', views.privacy_policy_view, name='privacy_policy'),
    path('terms-of-service/', views.terms_of_service_view, name='terms_of_service'),

    # Authentication URLs (using our custom views)
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Password Reset URLs (Using Django's built-in views)
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='mystore/registration/password_reset_form.html',
        email_template_name='mystore/registration/password_reset_email.html', # For the body of the email
        subject_template_name='mystore/registration/password_reset_subject.txt', # For the subject of the email
        success_url=reverse_lazy('password_reset_done') # Redirect after form submission
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='mystore/registration/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='mystore/registration/password_reset_confirm.html',
        success_url=reverse_lazy('password_reset_complete')
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='mystore/registration/password_reset_complete.html'
    ), name='password_reset_complete'),

    path('api/submit-custom-design/', views.submit_custom_design, name='submit_custom_design'),










        path('test-page/', views.test_page_view, name='test_page'),

]