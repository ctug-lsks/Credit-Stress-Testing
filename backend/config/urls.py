from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR.parent / 'frontend' / 'dist' / 'frontend' / 'browser'

def serve_spa(request, path=''):
    if not path or path == '/':
        path = 'index.html'
    return serve(request, path, document_root=str(FRONTEND_DIR))

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('stress_app.urls')),
    re_path(r'^(?P<path>.*)$', serve_spa),
]
