from django.contrib import admin
from django.utils.html import format_html
from .models import Categoria, Ubicacion, Trabajador, Herramienta, Prestamo, DetallePrestamo

# ==============================================================================
# CONFIGURACIÓN GENERAL DEL PANEL
# ==============================================================================
admin.site.site_header = "Administración SmartStockQR"
admin.site.site_title = "SmartStockQR Admin"
admin.site.index_title = "Panel de Control Gerencial"

# ==============================================================================
# 1. PARAMÉTRICAS (Con Borrado Lógico)
# ==============================================================================

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'descripcion', 'activo') 
    list_filter = ('activo',) 
    search_fields = ('nombre',)
    actions = ['dar_de_baja']

    def dar_de_baja(self, request, queryset):
        updated = queryset.update(activo=False)
        self.message_user(request, f"{updated} categorías fueron desactivadas.")
    dar_de_baja.short_description = "Dar de Baja (Soft Delete)"

@admin.register(Ubicacion)
class UbicacionAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'descripcion', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre',)
    actions = ['dar_de_baja']

    def dar_de_baja(self, request, queryset):
        updated = queryset.update(activo=False)
        self.message_user(request, f"{updated} ubicaciones fueron desactivadas.")
    dar_de_baja.short_description = "Dar de Baja (Soft Delete)"

# ==============================================================================
# 2. ACTORES
# ==============================================================================

@admin.register(Trabajador)
class TrabajadorAdmin(admin.ModelAdmin):
    list_display = ('rut', 'nombre', 'apellido', 'cargo', 'activo')
    list_filter = ('cargo', 'activo')
    search_fields = ('rut', 'nombre', 'apellido')
    ordering = ('nombre',)
    actions = ['desactivar_trabajador']

    def desactivar_trabajador(self, request, queryset):
        updated = queryset.update(activo=False)
        self.message_user(request, f"{updated} trabajadores fueron desactivados.")
    desactivar_trabajador.short_description = "Desactivar Trabajador"

# ==============================================================================
# 3. INVENTARIO (El Corazón del Sistema)
# ==============================================================================

@admin.register(Herramienta)
class HerramientaAdmin(admin.ModelAdmin):
    list_display = ('codigo_qr', 'nombre', 'marca', 'estado', 'ubicacion', 'activo')
    list_filter = ('activo', 'estado', 'categoria', 'ubicacion', 'marca')
    search_fields = ('nombre', 'marca', 'codigo_qr')
    readonly_fields = ('codigo_qr',) 
    actions = ['dar_de_baja_herramienta']

    def dar_de_baja_herramienta(self, request, queryset):
        updated = queryset.update(activo=False)
        self.message_user(request, f"{updated} herramientas dadas de baja correctamente.")
    dar_de_baja_herramienta.short_description = "Dar de Baja (Soft Delete)"

# ==============================================================================
# 4. TRANSACCIONES (Préstamos y Detalles con FOTOS)
# ==============================================================================

class DetallePrestamoInline(admin.TabularInline):
    """Permite ver las herramientas y sus fotos dentro del Préstamo"""
    model = DetallePrestamo
    extra = 0
    readonly_fields = ('herramienta', 'devuelto', 'estado_devolucion', 'mostrar_evidencia', 'observacion_falla', 'fecha_devolucion')
    fields = ('herramienta', 'devuelto', 'estado_devolucion', 'mostrar_evidencia', 'observacion_falla', 'fecha_devolucion')
    can_delete = False 

    def mostrar_evidencia(self, obj):
        try:
            if obj.foto_evidencia:
                return format_html('<img src="{}" style="width: 80px; height: auto; border-radius: 5px; border: 1px solid #ccc;" />', obj.foto_evidencia.url)
        except Exception:
            return "Error al cargar img"
        return "Sin foto"
    mostrar_evidencia.short_description = "Evidencia Visual"


@admin.register(Prestamo)
class PrestamoAdmin(admin.ModelAdmin):
    list_display = ('id', 'trabajador', 'bodeguero', 'fecha_solicitud', 'fecha_devolucion', 'estado_visual')
    list_filter = ('fecha_solicitud', 'bodeguero')
    search_fields = ('trabajador__nombre', 'trabajador__rut')
    inlines = [DetallePrestamoInline]

    def estado_visual(self, obj):
        """Muestra un indicador visual del estado del préstamo"""
        # CORRECCIÓN AQUÍ: format_html requiere {} y argumentos separados
        if obj.fecha_devolucion:
            return format_html('<span style="color: green; font-weight: bold;">{}</span>', "✔ Cerrado")
        return format_html('<span style="color: orange; font-weight: bold;">{}</span>', "⏳ En Curso")
    estado_visual.short_description = "Estado"


@admin.register(DetallePrestamo)
class DetallePrestamoAdmin(admin.ModelAdmin):
    """Vista individual de cada ítem prestado, útil para reportes de fallas"""
    list_display = ('prestamo', 'herramienta', 'devuelto', 'estado_devolucion', 'ver_foto', 'fecha_devolucion')
    list_filter = ('devuelto', 'estado_devolucion')
    search_fields = ('herramienta__nombre', 'herramienta__codigo_qr')
    readonly_fields = ('ver_foto_grande',)

    def ver_foto(self, obj):
        try:
            if obj.foto_evidencia:
                return format_html('<img src="{}" style="width: 50px; height: auto; border-radius: 3px;" />', obj.foto_evidencia.url)
        except Exception:
            return "Error"
        return "-"
    ver_foto.short_description = "Miniatura"

    def ver_foto_grande(self, obj):
        try:
            if obj.foto_evidencia:
                return format_html('<a href="{0}" target="_blank"><img src="{0}" style="width: 300px; height: auto; border-radius: 5px;" /></a>', obj.foto_evidencia.url)
        except Exception:
            return "Error cargando imagen grande"
        return "No hay evidencia cargada"
    ver_foto_grande.short_description = "Evidencia Tamaño Real"