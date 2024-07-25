from django.conf import settings
from django.conf.urls import include, url
from rest_framework.routers import DefaultRouter, Route

from account.views_logout_mobile import LogoutMobileView
from account.views_session import SessionView
from account.views_sso_aws_cognito import SSOAWSCognitoView
from account.views_user_transaction import TransactionContentView  # Ice
from .views_avatar import AccountAvatarView
from .views_calendar import CalendarView
from .views_change_password import ChangePasswordViewSet
from .views_check_auth import CheckAuthView
from .views_competency import CompetencyView
from .views_force_reset_password import UserResetPassword
from .views_forget_password import ForgetPasswordView


from .views_is_authenticated import IsAuthenticatedView
from .views_learning import LearningView
from .views_login import LoginView
from .views_login_mobile import LoginMobileView
from .views_login_qr_code import GenerateQrCode
from .views_login_qr_code import LoginQrCodeView
from .views_login_social import LoginSocialView
from .views_logout import LogoutView

from .views_profile import ProfileView
from .views_progress_summary import ProgressSummaryView
from .views_register import RegisterView
from .views_reset_password import ResetPasswordView

from .views_sso import SSOView
from .views_sso_redirect import SSORedirectView
from .views_sso_token import SSOTokenView
from .views_token import TokenView
from .views_validate import ValidateView
from .views_oauth_validate import OauthValidateView
from .views_oauth_notification_logout import OauthNotificationLogoutView
from .views_forget_password_otp import ForgetPasswordOTPView
from .views_reset_password_otp import ResetPasswordOTPView
from .views_forget_password_otp_resend import ResendForgetPasswordOTPView
from .views_summary_point import SummaryPointAccountView
from .views_verify_email import VerifyEmailView
from .views_verify_email_resend import VerifyEmailResendView
from .views_user_inactive import UserInactiveViews
from .views_login_otp import AccountOTPView


router = DefaultRouter()
router.include_root_view = settings.ROUTER_INCLUDE_ROOT_VIEW
router.routes[0] = Route(
    url=r'^{prefix}{trailing_slash}$',
    mapping={
        'get': 'list',
        'post': 'create',
        'patch': 'profile_patch',
    },
    name='{basename}-list',
    detail=False,
    initkwargs={'suffix': 'List'}
)
router.register(r'login/social', LoginSocialView)
router.register(r'login/mobile', LoginMobileView)
router.register(r'login', LoginView)
router.register(r'sso/authenticate', SSOView)
router.register(r'sso/redirect', SSORedirectView)
router.register(r'sso/token', SSOTokenView)
router.register(r'validate', ValidateView)
router.register(r'cognito/validate', SSOAWSCognitoView)
router.register(r'oauth/validate', OauthValidateView)
router.register(r'oauth/logout_notification', OauthNotificationLogoutView)
router.register(r'profile', ProfileView)
router.register(r'check-auth', CheckAuthView)
router.register(r'user-inactive', UserInactiveViews)

router.register(r'calendar', CalendarView)

router.register(r'forget/password/otp/resend', ResendForgetPasswordOTPView)
router.register(r'forget/password/otp', ForgetPasswordOTPView)
router.register(r'forget/password', ForgetPasswordView)

router.register(r'reset/password/otp', ResetPasswordOTPView)
router.register(r'reset/password', ResetPasswordView, basename='account-reset-password')

router.register(r'change/password', ChangePasswordViewSet, basename='account-change-password')
router.register(r'token', TokenView)

router.register(r'register', RegisterView)
router.register(r'verify-email/resend', VerifyEmailResendView)
router.register(r'verify-email', VerifyEmailView)

router.register(r'competency', CompetencyView)
router.register(r'generate/qrcode', GenerateQrCode)
router.register(r'login/qrcode', LoginQrCodeView)
router.register(r'progress', ProgressSummaryView)

router.register(r'transaction', TransactionContentView)
router.register(r'force/reset-password', UserResetPassword, basename='force-reset')
router.register(r'avatars', AccountAvatarView)
router.register(r'learning', LearningView)

router.register(r'login/otp', AccountOTPView)


router.register(r'gamification/point', SummaryPointAccountView)
router.routes.extend([
    Route(
        url=r'^{prefix}/(?P<year>[0-9]+)/(?P<month>[0-9]+)/$',
        name='{basename}-monthly',
        mapping={
            'get': 'monthly',
        },
        detail=False,
        initkwargs={},
    ),
    Route(
        url=r'^{prefix}/(?P<year>[0-9]+)/(?P<month>[0-9]+)/(?P<day>[0-9]+)/$',
        name='{basename}-daily',
        mapping={
            'get': 'daily',
        },
        detail=False,
        initkwargs={},
    ),
])

urlpatterns = [
    url(r'is-authenticated/$', IsAuthenticatedView.as_view()),
    url(r'logout/mobile/$', LogoutMobileView.as_view()),
    url(r'logout/$', LogoutView.as_view()),
    url(r'session/$', SessionView.as_view()),

    url(r'^', include(router.urls)),
]
