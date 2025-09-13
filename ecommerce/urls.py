from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .views import signup_view
from django.views.generic import TemplateView





urlpatterns = [
    path('', views.home, name='home'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path("signup/", signup_view, name="signup"),
    path("products/", views.products, name="products"),
    path("products/<int:product_id>/info", views.product_singlepage, name="product_singlepage"),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('orders/<int:user_id>/info', views.orders, name='orders'),
    path('order/delete/<int:order_id>', views.order_confirm_delete, name='order_confirm_delete'),
    path('profile/<int:user_id>/', views.profile, name='profile'),
    path('profile/update/', views.profile_update, name='profile_update'),
    path('payment/initiate/<int:order_id>/', views.initiate_payment, name='initiate_payment'),
    path('payment/return/', views.payment_return, name='payment_return'),
    path('payment/success-redirect/', views.payment_success_redirect, name='payment_success_redirect'),
    path('payment/fail/', views.payment_fail, name='payment_fail'),
    path("commande/confirmation/<int:order_id>/", views.confirm_order, name="confirm_order"),
    path('conditions-generales/', TemplateView.as_view(template_name='payment/terms_and_conditions.html'), name='terms_and_conditions'),
    path('payment/recu/<int:order_id>/pdf/', views.download_receipt_pdf, name='download_receipt_pdf'),
    path('payment/send-receipt/<int:order_id>/', views.send_receipt_email, name='send_receipt_email'),
    path("ajax/get-communes/", views.get_communes_for_wilaya, name="get_communes"),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('confirm-cod/<int:order_id>/confirm/', views.confirm_cod_order, name='confirm_cod_order'),






]