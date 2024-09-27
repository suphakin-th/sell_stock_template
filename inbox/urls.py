from rest_framework import routers

from inbox.views import InboxView

router = routers.DefaultRouter()
router.register('', InboxView)

urlpatterns = router.urls
