from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from django.contrib import messages
from datetime import datetime, time
from django.db.models import Count, Q, Case, When, Value, IntegerField
import json

from .models import Herramienta, Prestamo, DetallePrestamo, Trabajador, Categoria, Ubicacion, HistorialBaja

# ==============================================================================
# 1. DASHBOARD PRINCIPAL
# ==============================================================================
@login_required
def inicio(request):
    es_admin = request.user.is_superuser or request.user.is_staff

    if es_admin:
        # contamos solo lo que está realmente en la bodega (estado='DISPONIBLE')
        stock_disponible = Herramienta.objects.filter(activo=True, estado='DISPONIBLE').count()
        
        prestamos_activos = Herramienta.objects.filter(estado='EN_USO', activo=True).count()
        total_trabajadores = Trabajador.objects.filter(activo=True).count()
        en_mantencion = Herramienta.objects.filter(estado='EN_MANTENCION', activo=True).count()
        
        # Renderizamos con KPIs para ver estadisticas rapidas en el dashboard
        return render(request, 'bodega/inicio.html', {
            'es_admin': True,
            'kpi_total': stock_disponible, # Stock disponible para prestamos (estado DISPONIBLE)
            'kpi_prestamos': prestamos_activos, # Prestamos activos (estado EN_USO)
            'kpi_trabajadores': total_trabajadores, # Trabajadores activos
            'kpi_mantencion': en_mantencion # Herramientas en mantención (estado EN_MANTENCION)
        })
    
    return render(request, 'bodega/inicio.html', {
        'es_admin': False
    })

# ==============================================================================
# 2. PRÉSTAMO MULTICARGA
# ==============================================================================

@login_required
def registrar_prestamo(request):
    trabajadores_activos = Trabajador.objects.filter(activo=True).order_by('nombre')

    if request.method == 'POST':
        trabajador_id = request.POST.get('trabajador')
        lista_qrs_json = request.POST.get('lista_qrs')
        observaciones = request.POST.get('observaciones', '')

        if not lista_qrs_json:
            messages.warning(request, "⚠️ No se detectaron herramientas. Por favor escanee o ingrese un código.")
            return render(request, 'bodega/prestamo.html', {'trabajadores': trabajadores_activos})

        try:
            lista_qrs = json.loads(lista_qrs_json)
        except json.JSONDecodeError:
            messages.error(request, "Error técnico: El formato de la lista no es válido. Intente recargar la página.")
            return render(request, 'bodega/prestamo.html', {'trabajadores': trabajadores_activos})

        if len(lista_qrs) == 0:
            messages.warning(request, "⚠️ El carrito está vacío. Agregue herramientas antes de confirmar.")
            return render(request, 'bodega/prestamo.html', {'trabajadores': trabajadores_activos})

        if not trabajador_id:
             messages.error(request, "Debe seleccionar un trabajador.")
             return render(request, 'bodega/prestamo.html', {'trabajadores': trabajadores_activos})

        trabajador = get_object_or_404(Trabajador, id=trabajador_id)
        
        nuevo_prestamo = Prestamo.objects.create(
            trabajador=trabajador,
            bodeguero=request.user,
            fecha_solicitud=timezone.now(),
            observacion=observaciones
        )
        
        guardados = 0
        errores = []
        
        for codigo in lista_qrs:
            try:
                herramienta = Herramienta.objects.get(codigo_qr=codigo, activo=True)
                
                if herramienta.estado == 'DISPONIBLE':
                    DetallePrestamo.objects.create(
                        prestamo=nuevo_prestamo,
                        herramienta=herramienta
                    )
                    herramienta.estado = 'EN_USO'
                    herramienta.save()
                    guardados += 1
                else:
                    errores.append(f"{herramienta.nombre} no disponible ({herramienta.estado})")
                    
            except Herramienta.DoesNotExist:
                errores.append(f"QR {codigo} no existe o fue dado de baja")

        if guardados == 0:
            nuevo_prestamo.delete()
            if errores:
                messages.error(request, f"No se pudo realizar el préstamo: {', '.join(errores)}")
            else:
                messages.error(request, "No se pudo realizar el préstamo. Revise el stock.")
            
            return render(request, 'bodega/prestamo.html', {'trabajadores': trabajadores_activos})

        mensaje_exito = f"Se prestaron {guardados} herramientas a {trabajador.nombre} {trabajador.apellido}."
        if errores:
            mensaje_exito += f" (Atención: {len(errores)} ítems no se pudieron procesar)."
            
        messages.success(request, mensaje_exito)
        return redirect('prestamo')

    return render(request, 'bodega/prestamo.html', {
        'trabajadores': trabajadores_activos
    })

# ==============================================================================
# 3. DEVOLUCIÓN Y MERMAS
# ==============================================================================
@login_required
def registrar_devolucion(request):
    ultimas_devoluciones = None 
    mensaje = None
    error_msg = None

    if request.method == 'POST':
        qrs = request.POST.getlist('qrs[]')
        estados = request.POST.getlist('estados[]')
        observaciones = request.POST.getlist('observaciones[]')
        
        guardados = 0
        errores = []

        for i, codigo_qr in enumerate(qrs):
            try:
                foto = request.FILES.get(f'foto_{i}')
                estado = estados[i]
                obs = observaciones[i]

                herramienta = Herramienta.objects.get(codigo_qr=codigo_qr)
                
                detalle = DetallePrestamo.objects.filter(herramienta=herramienta, devuelto=False).first()

                if detalle:
                    ahora = timezone.now()

                    detalle.devuelto = True
                    detalle.estado_devolucion = estado
                    detalle.fecha_devolucion = ahora
                    detalle.observacion_falla = obs
                    if foto:
                        detalle.foto_evidencia = foto
                    detalle.save()

                    prestamo_padre = detalle.prestamo
                    pendientes = DetallePrestamo.objects.filter(prestamo=prestamo_padre, devuelto=False).count()
                    
                    if pendientes == 0:
                        prestamo_padre.fecha_devolucion = ahora
                        prestamo_padre.save()

                    if estado == 'EN_MANTENCION':
                        herramienta.estado = 'EN_MANTENCION'
                    else:
                        herramienta.estado = 'DISPONIBLE'
                    herramienta.save()
                    
                    guardados += 1
                else:
                    errores.append(f"{codigo_qr}: No estaba prestado.")

            except Herramienta.DoesNotExist:
                errores.append(f"{codigo_qr}: No existe.")

        if guardados > 0:
            mensaje = f"✅ Éxito: Se procesaron {guardados} devoluciones correctamente."
            ultimas_devoluciones = DetallePrestamo.objects.filter(
                devuelto=True
            ).order_by('-fecha_devolucion')[:guardados] 
        
        if errores:
            error_msg = "Alertas: " + ", ".join(errores)

        return render(request, 'bodega/devolucion.html', {
            'mensaje': mensaje,
            'error': error_msg,
            'ultimas_devoluciones': ultimas_devoluciones
        })

    return render(request, 'bodega/devolucion.html', {
        'ultimas_devoluciones': None 
    })

# ==============================================================================
# 4. REPORTES Y FILTROS (CON FECHAS ACTIVAS)
# ==============================================================================

@login_required
def ver_reportes(request):
    """
    Muestra la bitácora completa con ordenamiento dinámico.
    """
    # 1. Captura de parámetros
    fecha_inicio_str = request.GET.get('fecha_inicio', '')
    fecha_fin_str = request.GET.get('fecha_fin', '')
    busqueda = request.GET.get('q', '')
    orden_param = request.GET.get('orden', '')

    # 2. CONFIGURACIÓN DE ORDENAMIENTO (Diccionario de Mapeo)
    # Traduce lo que llega de la URL a campos reales de la BD
    opciones_orden = {
        'fecha': 'fecha_evento',
        '-fecha': '-fecha_evento',
        'accion': 'accion',
        '-accion': '-accion',
        'herramienta': 'herramienta__nombre',
        '-herramienta': '-herramienta__nombre',
        'motivo': 'motivo',
        '-motivo': '-motivo',
        'usuario': 'usuario__username',
        '-usuario': '-usuario__username',
    }
    
    # Si el parámetro no está en el diccionario, usa '-fecha_evento' por defecto
    criterio_final = opciones_orden.get(orden_param, '-fecha_evento')

    # 3. Consulta Base
    historial = HistorialBaja.objects.select_related('herramienta', 'usuario').all().order_by(criterio_final)

    # 4. Filtros
    if busqueda:
        historial = historial.filter(
            Q(herramienta__nombre__icontains=busqueda) |
            Q(herramienta__codigo_qr__icontains=busqueda) |
            Q(motivo__icontains=busqueda)
        )

    if fecha_inicio_str:
        historial = historial.filter(fecha_evento__date__gte=fecha_inicio_str)
    
    if fecha_fin_str:
        historial = historial.filter(fecha_evento__date__lte=fecha_fin_str)

    return render(request, 'bodega/reportes.html', {
        'reportes': historial,
        'total_mermas': historial.count(),
        'busqueda': busqueda,
        'filtro_inicio': fecha_inicio_str,
        'filtro_fin': fecha_fin_str,
        'orden_actual': orden_param # Enviamos esto para que el HTML sepa qué flecha pintar
    })

@login_required
def menu_reportes(request):
    # Solo mostramos esto si es Staff (Admin/Bodeguero)
    if not request.user.is_staff:
        messages.error(request, "Acceso Denegado")
        return redirect('inicio')
        
    return render(request, 'bodega/menu_reportes.html')

@login_required
def reporte_bajas(request):
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado.")
        return redirect('inicio')
    
    herramientas_baja = Herramienta.objects.filter(activo=False).order_by('-id')
    return render(request, 'bodega/listas/reporte_bajas.html', {
        'herramientas': herramientas_baja
    })

# ==============================================================================
# 5. API REST
# ==============================================================================
def api_verificar_qr(request):
    codigo = request.GET.get('codigo', '')
    
    try:
        herramienta = Herramienta.objects.get(codigo_qr=codigo, activo=True)
        esta_disponible = (herramienta.estado == 'DISPONIBLE')
        
        if esta_disponible:
            mensaje = "OK"
        else:
            mensaje = f"⚠️ ¡Cuidado! {herramienta.nombre} ya figura como PRESTADA (o en mantención)."

        return JsonResponse({
            'existe': True,
            'estado': herramienta.estado,
            'disponible': esta_disponible,
            'nombre': herramienta.nombre,
            'marca': herramienta.marca,
            'mensaje': mensaje
        })
            
    except Herramienta.DoesNotExist:
        return JsonResponse({
            'existe': False,
            'mensaje': "❌ Error: El código escaneado NO existe en el sistema."
        })

# ==============================================================================
# 6. UTILIDADES Y GESTIÓN
# ==============================================================================

@login_required
def consultar_stock(request):
    query = request.GET.get('q')

    total_sistema = Herramienta.objects.count()
    total_activas = Herramienta.objects.filter(activo=True).count()
    total_en_uso = Herramienta.objects.filter(estado='EN_USO', activo=True).count()
    total_bajas = Herramienta.objects.filter(activo=False).count()

    orden_prioridad = Case(
        When(estado='DISPONIBLE', then=Value(1)),
        When(estado='EN_USO', then=Value(2)),
        When(estado='EN_MANTENCION', then=Value(3)),
        default=Value(4),
        output_field=IntegerField(),
    )

    herramientas = Herramienta.objects.annotate(
        prioridad=orden_prioridad
    ).order_by('prioridad', 'nombre')
    
    if query:
        herramientas = herramientas.filter(
            Q(nombre__icontains=query) | 
            Q(marca__icontains=query) | 
            Q(modelo__icontains=query) | 
            Q(codigo_qr__icontains=query)
        )

    return render(request, 'bodega/consultar_stock.html', {
        'herramientas': herramientas,
        'busqueda': query,
        'total_sistema': total_sistema,
        'total_activas': total_activas,
        'total_en_uso': total_en_uso,
        'total_bajas': total_bajas
    })

@login_required
def imprimir_qr(request, herramienta_id):
    herramienta = get_object_or_404(Herramienta, id=herramienta_id)
    return render(request, 'bodega/imprimir_qr.html', {
        'h': herramienta
    })

@login_required
def en_mantencion(request):
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado.")
        return redirect('inicio')

    herramientas = Herramienta.objects.filter(estado='EN_MANTENCION', activo=True)
    return render(request, 'bodega/en_mantencion.html', {
        'herramientas': herramientas
    })

@login_required
def liberar_herramienta(request, herramienta_id):
    herramienta = get_object_or_404(Herramienta, id=herramienta_id)
    herramienta.estado = 'DISPONIBLE'
    herramienta.save()
    return redirect('en_mantencion')

@login_required
def herramientas_disponibles(request):
    # FILTRO: Solo herramientas activas Y que estén DISPONIBLES
    herramientas = Herramienta.objects.filter(
        activo=True, 
        estado='DISPONIBLE'
    ).order_by('nombre')
    
    return render(request, 'bodega/listas/herramientas_disponibles.html', {
        'herramientas': herramientas
    })

@login_required
def herramientas_en_uso(request):
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado.")
        return redirect('inicio')
    
    prestamos_activos = DetallePrestamo.objects.filter(devuelto=False).select_related('herramienta', 'prestamo__trabajador')
    return render(request, 'bodega/listas/herramientas_en_uso.html', {
        'prestamos': prestamos_activos
    })

@login_required
def lista_trabajadores(request):
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado.")
        return redirect('inicio')
    
    trabajadores = Trabajador.objects.all().order_by('-activo', 'nombre')
    return render(request, 'bodega/listas/lista_trabajadores.html', {
        'trabajadores': trabajadores
    })

# ==============================================================================
# 7. GESTIÓN DE MAESTROS
# ==============================================================================

@login_required
def eliminar_trabajador(request, id):
    if not request.user.is_staff:
        messages.error(request, "No tienes permisos.")
        return redirect('lista_trabajadores')

    trabajador = get_object_or_404(Trabajador, id=id)
    trabajador.activo = False
    trabajador.save()
    
    messages.success(request, "Trabajador desactivado correctamente.")
    return redirect('lista_trabajadores')

@login_required
def eliminar_ubicacion(request, id):
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado.")
        return redirect('inicio')

    ubicacion = get_object_or_404(Ubicacion, id=id)
    ubicacion.activo = False
    ubicacion.save()
    
    messages.success(request, "Ubicación desactivada.")
    return redirect('inicio') 

@login_required
def eliminar_categoria(request, id):
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado.")
        return redirect('inicio')

    categoria = get_object_or_404(Categoria, id=id)
    categoria.activo = False
    categoria.save()
    
    messages.success(request, "Categoría desactivada.")
    return redirect('inicio')

@login_required
def eliminar_herramienta(request, id):
    if not request.user.is_staff:
        messages.error(request, "No tienes permisos.")
        return redirect('consultar_stock')

    herramienta = get_object_or_404(Herramienta, id=id)

    motivo_texto = ""
    if herramienta.estado == 'EN_MANTENCION':
        herramienta.estado = 'BAJA_POR_DANO'
        motivo_texto = "Daño Irreparable"
    elif herramienta.estado == 'EN_USO':
        herramienta.estado = 'BAJA_POR_PERDIDA'
        motivo_texto = "Pérdida en Obra"
    else:
        herramienta.estado = 'DE_BAJA'
        motivo_texto = "Baja Administrativa"

    herramienta.activo = False
    herramienta.save()

    HistorialBaja.objects.create(
        herramienta=herramienta,
        accion='BAJA',
        motivo=motivo_texto,
        usuario=request.user
    )
    
    messages.success(request, f"Baja procesada: {motivo_texto}. Registro guardado en Historial.")
    return redirect('consultar_stock')

@login_required
def reactivar_herramienta(request, id):
    if not request.user.is_staff:
        messages.error(request, "No tienes permiso para reactivar activos.")
        return redirect('consultar_stock')

    herramienta = get_object_or_404(Herramienta, id=id)
    
    # 1. VERIFICACIÓN DE PRÉSTAMOS ZOMBIES
    # Buscamos si hay algún préstamo abierto para esta herramienta
    prestamos_pendientes = DetallePrestamo.objects.filter(herramienta=herramienta, devuelto=False)
    
    msg_extra = ""
    if prestamos_pendientes.exists():
        ahora = timezone.now()
        for detalle in prestamos_pendientes:
            # Cerramos el préstamo forzosamente
            detalle.devuelto = True
            detalle.fecha_devolucion = ahora
            detalle.estado_devolucion = 'DISPONIBLE'
            detalle.observacion_falla = "Cierre automático por Reactivación de Inventario"
            detalle.save()
            
            # Verificamos si cerramos el préstamo padre
            prestamo_padre = detalle.prestamo
            hermanos_pendientes = DetallePrestamo.objects.filter(prestamo=prestamo_padre, devuelto=False).count()
            if hermanos_pendientes == 0:
                prestamo_padre.fecha_devolucion = ahora
                prestamo_padre.save()
        
        msg_extra = " (Se cerraron préstamos pendientes asociados)."

    # 2. Reactivamos la herramienta
    herramienta.activo = True
    herramienta.estado = 'DISPONIBLE'
    herramienta.save()
    
    # 3. CREAMOS EL REGISTRO DE AUDITORÍA
    HistorialBaja.objects.create(
        herramienta=herramienta,
        accion='REACTIVACION',
        motivo='Reincorporación al Inventario',
        usuario=request.user
    )
    
    messages.success(request, f"¡Éxito! {herramienta.nombre} reactivada.{msg_extra}")
    return redirect('consultar_stock')

@login_required
def estadisticas_uso(request):
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado.")
        return redirect('inicio')

    top_herramientas = Herramienta.objects.annotate(
        num_prestamos=Count('detalleprestamo')
    ).order_by('-num_prestamos')[:5]

    top_trabajadores = Trabajador.objects.annotate(
        num_solicitudes=Count('prestamo__detalleprestamo') 
    ).order_by('-num_solicitudes')[:5]

    return render(request, 'bodega/listas/estadisticas.html', {
        'top_herramientas': top_herramientas,
        'top_trabajadores': top_trabajadores
    })

# ==============================================================================
# 8. NUEVO REPORTE: TRAZABILIDAD TOTAL (HISTORIAL TRANSACCIONES)
# ==============================================================================
@login_required
def historial_transacciones(request):
    if not request.user.is_staff:
        messages.error(request, "Acceso Denegado")
        return redirect('inicio')

    # 1. Captura de parámetros
    query = request.GET.get('q', '')
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')
    orden_param = request.GET.get('orden', '')

    # 2. CONFIGURACIÓN DE ORDENAMIENTO (Mapeo de Campos)
    # Como la tabla es DetallePrestamo, los campos son diferentes (usamos __ para navegar)
    opciones_orden = {
        'fecha': 'prestamo__fecha_solicitud', '-fecha': '-prestamo__fecha_solicitud',
        'herramienta': 'herramienta__nombre', '-herramienta': '-herramienta__nombre',
        'trabajador': 'prestamo__trabajador__nombre', '-trabajador': '-prestamo__trabajador__nombre',
        'bodeguero': 'prestamo__bodeguero__username', '-bodeguero': '-prestamo__bodeguero__username',
        'estado': 'estado_devolucion', '-estado': '-estado_devolucion',
        'devolucion': 'fecha_devolucion', '-devolucion': '-fecha_devolucion',
    }
    # Por defecto: Fecha de préstamo descendente
    criterio_final = opciones_orden.get(orden_param, '-prestamo__fecha_solicitud')

    # 3. Consulta Base
    movimientos = DetallePrestamo.objects.select_related(
        'prestamo', 'herramienta', 'prestamo__trabajador', 'prestamo__bodeguero'
    ).order_by(criterio_final)

    # 4. Filtros
    if query:
        movimientos = movimientos.filter(
            Q(herramienta__nombre__icontains=query) |
            Q(herramienta__codigo_qr__icontains=query) |
            Q(prestamo__trabajador__nombre__icontains=query) |
            Q(prestamo__trabajador__rut__icontains=query)
        )

    if fecha_inicio: movimientos = movimientos.filter(prestamo__fecha_solicitud__date__gte=fecha_inicio)
    if fecha_fin: movimientos = movimientos.filter(prestamo__fecha_solicitud__date__lte=fecha_fin)

    # 5. Retorno
    return render(request, 'bodega/historial_transacciones.html', {
        'movimientos': movimientos,
        'query': query,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'orden_actual': orden_param # Para pintar las flechas
    })