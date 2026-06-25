# openoutreach/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from openoutreach.core import views as core_views

urlpatterns = [
    path("", include("openoutreach.signals.urls")),
    path("admin/", admin.site.urls),
    # Authentication
    path("accounts/login/", auth_views.LoginView.as_view(template_name="core/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/signup/", core_views.signup, name="signup"),
    path("accounts/password-reset/", auth_views.PasswordResetView.as_view(
        template_name="core/password_reset.html",
        email_template_name="core/password_reset_email.txt",
        subject_template_name="core/password_reset_subject.txt",
    ), name="password_reset"),
    path("accounts/password-reset/done/", auth_views.PasswordResetDoneView.as_view(
        template_name="core/password_reset_done.html",
    ), name="password_reset_done"),
    path("accounts/reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="core/password_reset_confirm.html",
    ), name="password_reset_confirm"),
    path("accounts/reset/done/", auth_views.PasswordResetCompleteView.as_view(
        template_name="core/password_reset_complete.html",
    ), name="password_reset_complete"),
    # Client portal
    path("portal/", core_views.portal, name="portal"),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
