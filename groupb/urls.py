from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # トップページ (ルート /) へのアクセスを app/urls.py に渡す
    path("", include("app.urls")),
    
    path('admin/', admin.site.urls),

    # accounts.urls が存在しない場合はコメントアウト
    path("accounts/", include("accounts.urls")),
]
