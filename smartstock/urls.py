from django.contrib import admin
from django.urls import path, include
from django.conf import settings            # Importamos la configuración (settings.py)
from django.conf.urls.static import static  # Herramienta para servir archivos estáticos
from django.views.static import serve # Para servir archivos físicamente
from django.urls import re_path # Para rutas complejas

urlpatterns = [
    # 1. EL PANEL DE ADMINISTRACIÓN
    # Django ya trae un admin listo. Aquí le decimos en qué dirección vive.
    path('admin/', admin.site.urls),

    # 2. SISTEMA DE AUTENTICACIÓN (Login/Logout)
    # Incluimos las URLs nativas de Django para el manejo de sesiones.
    # Esto nos da gratis las rutas 'login/' y 'logout/'.
    path('accounts/', include('django.contrib.auth.urls')),

    # 3. NUESTRA APLICACIÓN (Bodega)
    # Si la ruta no es admin ni accounts, se la pasamos a nuestra app 'bodega'.
    # El string vacío '' significa "la raíz del sitio".
    path('', include('bodega.urls')),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

# Mantenemos esto para tu funcionamiento local en el PC
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    