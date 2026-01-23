from django.db import models
from django.contrib.auth.models import User
import qrcode
from io import BytesIO
from django.core.files import File

# ==============================================================================
# 1. TABLAS PARAMÉTRICAS
# ==============================================================================

class Categoria(models.Model):
    nombre = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    activo = models.BooleanField(default=True, verbose_name="Activa") 

    def __str__(self):
        return self.nombre

class Ubicacion(models.Model):
    class Meta:
        verbose_name = "Ubicación"
        verbose_name_plural = "Ubicaciones"
    nombre = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    activo = models.BooleanField(default=True, verbose_name="Activa")

    def __str__(self):
        return self.nombre

# ==============================================================================
# 2. ACTORES
# ==============================================================================

class Trabajador(models.Model):
    class Meta:
        verbose_name = "Trabajador"
        verbose_name_plural = "Trabajadores"
    rut = models.CharField(max_length=12, unique=True)
    nombre = models.CharField(max_length=50)
    apellido = models.CharField(max_length=50)
    cargo = models.CharField(max_length=50)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

# ==============================================================================
# 3. INVENTARIO
# ==============================================================================

class Herramienta(models.Model):
    # Definimos estados completos incluyendo las bajas por daño o pérdida
    ESTADOS = (
        ('DISPONIBLE', 'Disponible'),
        ('EN_USO', 'En Uso'),
        ('EN_MANTENCION', 'En Mantención'),
        ('DE_BAJA', 'De Baja Administrativa'),
        ('BAJA_POR_DANO', 'Baja por Daño'),
        ('BAJA_POR_PERDIDA', 'Baja por Pérdida'),
    )

    codigo_qr = models.CharField(max_length=100, unique=True, blank=True)
    nombre = models.CharField(max_length=100)
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50, blank=True, null=True)
    
    estado = models.CharField(max_length=20, choices=ESTADOS, default='DISPONIBLE') 
    
    categoria = models.ForeignKey('Categoria', on_delete=models.CASCADE)
    ubicacion = models.ForeignKey('Ubicacion', on_delete=models.CASCADE)
    
    imagen_qr = models.ImageField(upload_to='codigos_qr/', blank=True, null=True)
    activo = models.BooleanField(default=True, verbose_name="Activa en Sistema")

    def save(self, *args, **kwargs):
        # Generación automática de QR al crear
        if not self.pk:
            super().save(*args, **kwargs)
            self.codigo_qr = f"HER-{self.pk}"
            qrcode_img = qrcode.make(self.codigo_qr)
            canvas = BytesIO()
            qrcode_img.save(canvas, format='PNG')
            file_name = f'qr_{self.codigo_qr}.png'
            self.imagen_qr.save(file_name, File(canvas), save=False)
            super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} ({self.codigo_qr})"

# ==============================================================================
# 4. TRANSACCIONES
# ==============================================================================

class Prestamo(models.Model):
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_devolucion = models.DateTimeField(null=True, blank=True)
    trabajador = models.ForeignKey(Trabajador, on_delete=models.PROTECT)
    bodeguero = models.ForeignKey(User, on_delete=models.PROTECT)
    observacion = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Prestamo #{self.id} - {self.trabajador}"

class DetallePrestamo(models.Model):
    prestamo = models.ForeignKey(Prestamo, on_delete=models.CASCADE)
    herramienta = models.ForeignKey(Herramienta, on_delete=models.PROTECT)
    
    devuelto = models.BooleanField(default=False)
    fecha_devolucion = models.DateTimeField(null=True, blank=True)
    
    # Aquí definimos las opciones para que coincidan con tu HTML de devolución
    OPCIONES_ESTADO = (
        ('DISPONIBLE', 'Bueno / Operativo'),
        ('EN_MANTENCION', 'Dañado / Falla'),
    )
    estado_devolucion = models.CharField(max_length=20, choices=OPCIONES_ESTADO, blank=True, null=True)
    
    observacion_falla = models.TextField(blank=True, null=True)
    
    # Campo CRÍTICO: Aquí se guardarán las fotos en el volumen de Railway
    foto_evidencia = models.ImageField(upload_to='evidencias/', blank=True, null=True)

    def __str__(self):
        return f"{self.herramienta.nombre} en Prestamo #{self.prestamo.id}"
    
class HistorialBaja(models.Model):
    """
    Tabla de auditoría para guardar el historial de bajas y reactivaciones.
    Esto permite trazabilidad aunque la herramienta se reactive.
    """
    herramienta = models.ForeignKey(Herramienta, on_delete=models.CASCADE)
    fecha_evento = models.DateTimeField(auto_now_add=True)
    
    # Registramos qué pasó: 'BAJA' o 'REACTIVACION'
    TIPO_ACCION = (
        ('BAJA', 'Dar de Baja'),
        ('REACTIVACION', 'Reactivación / Alta'),
    )
    accion = models.CharField(max_length=20, choices=TIPO_ACCION)
    
    # Guardamos el motivo o estado que tenía en ese momento
    motivo = models.CharField(max_length=100) 
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True) # Quién lo hizo

    def __str__(self):
        return f"{self.herramienta.nombre} - {self.accion} ({self.fecha_evento})"