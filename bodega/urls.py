from django.urls import path
from . import views

urlpatterns = [
    # --- 1. PÁGINA PRINCIPAL ---
    path('', views.inicio, name='inicio'),

    # --- 2. OPERACIÓN BODEGUERO ---
    path('prestamo/', views.registrar_prestamo, name='prestamo'), 
    path('devolucion/', views.registrar_devolucion, name='devolucion'),
    path('stock/', views.consultar_stock, name='consultar_stock'),
    path('herramienta/reactivar/<int:id>/', views.reactivar_herramienta, name='reactivar_herramienta'),

    # --- 3. CONEXIÓN API REST ---
    path('api/verificar/', views.api_verificar_qr, name='api_verificar'),

    # --- 4. GESTIÓN Y REPORTES ---
    path('reportes/menu/', views.menu_reportes, name='menu_reportes'),
    path('reportes/mermas/', views.ver_reportes, name='reportes'), # Cambié un poco la URL para ser ordenados
    path('mantencion/', views.en_mantencion, name='en_mantencion'),
    path('herramientas-disponibles/', views.herramientas_disponibles, name='herramientas_disponibles'), # Herramientas activas para prestamo
    path('en-uso/', views.herramientas_en_uso, name='herramientas_en_uso'),
    path('trabajadores/', views.lista_trabajadores, name='lista_trabajadores'),
    path('reportes/transacciones/', views.historial_transacciones, name='historial_transacciones'),

    # --- ¡ESTAS SON LAS QUE FALTABAN! (Reportes Nuevos) ---
    path('reportes/estadisticas/', views.estadisticas_uso, name='estadisticas'),
    path('reportes/bajas/', views.reporte_bajas, name='reporte_bajas'),

    # --- 5. RUTAS DINÁMICAS (Acciones) ---
    path('imprimir/<int:herramienta_id>/', views.imprimir_qr, name='imprimir_qr'),
    path('liberar/<int:herramienta_id>/', views.liberar_herramienta, name='liberar_herramienta'),

    # --- 6. RUTAS DE ELIMINACIÓN (BORRADO LÓGICO) ---
    path('herramienta/eliminar/<int:id>/', views.eliminar_herramienta, name='eliminar_herramienta'),
    path('trabajador/eliminar/<int:id>/', views.eliminar_trabajador, name='eliminar_trabajador'),
    path('ubicacion/eliminar/<int:id>/', views.eliminar_ubicacion, name='eliminar_ubicacion'),
    path('categoria/eliminar/<int:id>/', views.eliminar_categoria, name='eliminar_categoria'),
    
]