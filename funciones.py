"""
Módulo para funciones relacionadas con el chatbot y API de búsqueda.
Contiene endpoints y lógica para el agente IA en n8n.
"""
import time
from flask import Blueprint, jsonify, request
from flask_login import login_required
from models import Producto, Servicio, db, Categoria, Subcategoria, Negocio, Agendamiento, User
from datetime import datetime, timedelta
import json

# Crear blueprint para las rutas de API
api_bp = Blueprint('api', __name__, url_prefix='/api')

# ============================================
# 1. ESTRUCTURA DE BASE DE DATOS MEJORADA
# ============================================

def inicializar_estructura_chatbot():
    """
    Inicializa la estructura de categorías jerárquicas para el chatbot.
    Se ejecuta al inicio de la aplicación.
    """
    # Categorías principales (Nivel 1)
    categorias_principales = [
        ('Servicios Profesionales', 'servicio'),
        ('Alimentos y Bebidas', 'producto'),
        ('Salud y Bienestar', 'servicio'),
        ('Educación', 'servicio'),
        ('Tecnología', 'producto'),
        ('Hogar y Construcción', 'producto'),
        ('Automotriz', 'servicio'),
        ('Entretenimiento', 'servicio'),
        ('Moda y Belleza', 'producto'),
        ('Otros', 'mixto')
    ]
    
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        return
    
    # Crear categorías principales
    for nombre, tipo in categorias_principales:
        if not Categoria.query.filter_by(nombre=nombre).first():
            categoria = Categoria(
                nombre=nombre,
                tipo=tipo,
                nivel=1,
                orden=len(Categoria.query.filter_by(nivel=1).all()) + 1,
                created_by=admin_user.id
            )
            db.session.add(categoria)
            db.session.flush()
            
            # Crear subcategorías según la categoría principal
            subcategorias = obtener_subcategorias_por_categoria(nombre)
            for subcat_nombre in subcategorias:
                subcategoria = Subcategoria(
                    nombre=subcat_nombre,
                    categoria_id=categoria.id,
                    nivel=2,
                    created_by=admin_user.id
                )
                db.session.add(subcategoria)

# ============================================
# 2. ENDPOINTS PARA EL CHATBOT (n8n)
# ============================================

@api_bp.route('/categorias', methods=['GET'])
def get_categorias():
    """Retorna las categorías principales para el primer nivel del chatbot."""
    categorias = Categoria.query.filter_by(nivel=1).order_by(Categoria.orden).all()
    return jsonify([
        {'id': c.id, 'nombre': c.nombre, 'tipo': c.tipo} 
        for c in categorias
    ])
    
    return jsonify({'categorias': resultado, 'total': len(resultado)})

@api_bp.route('/subcategorias/<int:categoria_id>', methods=['GET'])
def get_subcategorias(categoria_id):
    """Retorna las subcategorías de una categoría específica."""
    subcategorias = Subcategoria.query.filter_by(categoria_id=categoria_id).all()
    return jsonify([
        {'id': s.id, 'nombre': s.nombre} 
        for s in subcategorias
    ])

@api_bp.route('/vendedores/<int:subcategoria_id>', methods=['GET'])
def get_vendedores_por_subcategoria(subcategoria_id):
    """
    Busca negocios que tengan productos o servicios en una subcategoría.
    """
    # Buscar IDs de usuarios que tienen items en esa subcategoría
    prod_users = db.session.query(Producto.created_by).filter_by(subcategoria_id=subcategoria_id).distinct()
    serv_users = db.session.query(Servicio.created_by).filter_by(subcategoria_id=subcategoria_id).distinct()
    
    user_ids = [r[0] for r in prod_users.all()] + [r[0] for r in serv_users.all()]
    user_ids = list(set(user_ids)) # Unificar IDs únicos

    # Obtener los negocios de esos usuarios
    negocios = Negocio.query.filter(Negocio.usuario_id.in_(user_ids), Negocio.activo == True).all()
    
    return jsonify([
        {'id': n.id, 'nombre': n.nombre, 'descripcion': n.descripcion_corta} 
        for n in negocios
    ])

@api_bp.route('/buscar', methods=['GET'])
def buscar_negocios():
    """
    Buscar negocios por especialidad o palabra clave.
    Endpoint: GET /api/buscar?q=palabra&especialidad_id=X&limit=10
    """
    query = request.args.get('q', '').strip()
    especialidad_id = request.args.get('especialidad_id', type=int)
    limit = request.args.get('limit', 10, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # Construir consulta base
    consulta = Negocio.query.filter_by(activo=True)
    
    # Filtrar por especialidad si se proporciona
    if especialidad_id:
        consulta = consulta.filter_by(subcategoria_id=especialidad_id)
    
    # Filtrar por palabra clave si se proporciona
    if query:
        search_pattern = f'%{query}%'
        consulta = consulta.filter(
            db.or_(
                Negocio.nombre.ilike(search_pattern),
                Negocio.descripcion_corta.ilike(search_pattern),
                Negocio.descripcion_larga.ilike(search_pattern),
                Negocio.palabras_clave.ilike(search_pattern)
            )
        )
    
    # Obtener resultados paginados
    negocios = consulta.limit(limit).offset(offset).all()
    
    # Formatear resultados
    resultado = []
    for negocio in negocios:
        # Obtener información de la categoría
        subcat = Subcategoria.query.get(negocio.subcategoria_id)
        categoria = Categoria.query.get(subcat.categoria_id) if subcat else None
        
        resultado.append({
            'id': negocio.id,
            'nombre': negocio.nombre,
            'descripcion_corta': negocio.descripcion_corta,
            'categoria': categoria.nombre if categoria else '',
            'subcategoria': subcat.nombre if subcat else '',
            'precio_estimado': float(negocio.precio_estimado) if negocio.precio_estimado else None,
            'calificacion': float(negocio.calificacion_promedio) if negocio.calificacion_promedio else None,
            'ubicacion': negocio.ubicacion
        })
    
    return jsonify({
        'query': query,
        'especialidad_id': especialidad_id,
        'resultados': resultado,
        'total': consulta.count(),
        'limit': limit,
        'offset': offset
    })

@api_bp.route('/perfil/<int:negocio_id>', methods=['GET'])
def obtener_perfil_negocio(negocio_id):
    """
    Obtener perfil completo de un negocio.
    Endpoint: GET /api/perfil/<negocio_id>
    """
    negocio = Negocio.query.get_or_404(negocio_id)
    
    # Obtener información jerárquica
    subcat = Subcategoria.query.get(negocio.subcategoria_id)
    categoria = Categoria.query.get(subcat.categoria_id) if subcat else None
    
    # Formatear respuesta
    perfil = {
        'id': negocio.id,
        'nombre': negocio.nombre,
        'descripcion_corta': negocio.descripcion_corta,
        'descripcion_larga': negocio.descripcion_larga,
        'categoria': {
            'id': categoria.id if categoria else None,
            'nombre': categoria.nombre if categoria else None
        },
        'subcategoria': {
            'id': subcat.id if subcat else None,
            'nombre': subcat.nombre if subcat else None
        },
        'contacto': {
            'telefono': negocio.telefono_contacto,
            'email': negocio.email_contacto,
            'whatsapp': negocio.whatsapp_contacto,
            'web': negocio.sitio_web
        },
        'ubicacion': {
            'direccion': negocio.direccion,
            'latitud': float(negocio.latitud) if negocio.latitud else None,
            'longitud': float(negocio.longitud) if negocio.longitud else None
        },
        'media': {
            'url_presentacion': negocio.url_presentacion,
            'url_imagen_perfil': negocio.url_imagen_perfil,
            'tipo_media': negocio.tipo_media,
            'galeria': json.loads(negocio.galeria) if negocio.galeria else []
        },
        'servicios': json.loads(negocio.servicios) if negocio.servicios else [],
        'horarios': json.loads(negocio.horarios) if negocio.horarios else [],
        'precio_estimado': float(negocio.precio_estimado) if negocio.precio_estimado else None,
        'calificacion': {
            'promedio': float(negocio.calificacion_promedio) if negocio.calificacion_promedio else None,
            'total_resenas': negocio.total_resenas
        },
        'estadisticas': {
            'visitas': negocio.visitas,
            'agendamientos': negocio.total_agendamientos,
            'creado': negocio.created_at.isoformat() if negocio.created_at else None
        },
        'mensaje_confirmacion': f"¿Deseas agendar con {negocio.nombre}?"
    }
    
    # Incrementar contador de visitas
    negocio.visitas += 1
    db.session.commit()
    
    return jsonify(perfil)

@api_bp.route('/negocios/<int:negocio_id>', methods=['GET'])
def get_detalle_negocio(negocio_id):
    """Retorna el perfil completo de un negocio para el Agente IA."""
    negocio = Negocio.query.get_or_404(negocio_id)
    
    # Obtener productos y servicios para mostrar en el perfil
    productos = Producto.query.filter_by(created_by=negocio.usuario_id).all()
    servicios = Servicio.query.filter_by(created_by=negocio.usuario_id).all()
    
    items = []
    for p in productos:
        items.append({'nombre': p.nombre, 'precio': p.precio, 'tipo': 'producto'})
    for s in servicios:
        items.append({'nombre': s.nombre, 'precio': s.precio, 'tipo': 'servicio'})

    return jsonify({
        'id': negocio.id,
        'nombre': negocio.nombre,
        'descripcion': negocio.descripcion_corta,
        'contacto': negocio.telefono_contacto,
        'catalogo_resumen': items[:5] # Enviamos los primeros 5 para no saturar al agente
    })

@api_bp.route('/agendar', methods=['POST'])
def registrar_agendamiento():
    """Registra una solicitud de contacto/agenda desde el chatbot."""
    data = request.json
    try:
        nuevo_age = Agendamiento(
            cliente_nombre=data.get('nombre'),
            cliente_telefono=data.get('telefono'),
            negocio_id=data.get('negocio_id'),
            requerimiento=data.get('nota'),
            fecha_registro=datetime.now(),
            estado='pendiente'
        )
        db.session.add(nuevo_age)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Agendamiento registrado'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 400
    

@api_bp.route('/estadisticas/chatbot', methods=['GET'])
@login_required
def obtener_estadisticas_chatbot():
    """
    Obtener estadísticas del uso del chatbot.
    Solo para administradores.
    """
    # Contar agendamientos por periodo
    ultimos_30_dias = datetime.now().date() - timedelta(days=30)

    agendamientos_recientes = Agendamiento.query.filter(
        Agendamiento.created_at >= ultimos_30_dias
    ).count()
    
    total_agendamientos = Agendamiento.query.count()
    
    # Negocios más consultados
    negocios_populares = db.session.query(
        Negocio.nombre,
        Negocio.visitas,
        Negocio.total_agendamientos
    ).order_by(Negocio.visitas.desc()).limit(10).all()
    
    # Categorías más consultadas
    categorias_populares = db.session.query(
        Categoria.nombre,
        db.func.sum(Negocio.visitas).label('total_visitas')
    ).join(Subcategoria, Categoria.id == Subcategoria.categoria_id
    ).join(Negocio, Subcategoria.id == Negocio.subcategoria_id
    ).group_by(Categoria.id
    ).order_by(db.desc('total_visitas')).limit(5).all()
    
    return jsonify({
        'periodo': '30_dias',
        'agendamientos': {
            'recientes': agendamientos_recientes,
            'total': total_agendamientos,
            'tasa_conversion': (agendamientos_recientes / max(Negocio.query.count(), 1)) * 100
        },
        'negocios_populares': [
            {'nombre': n[0], 'visitas': n[1], 'agendamientos': n[2]}
            for n in negocios_populares
        ],
        'categorias_populares': [
            {'nombre': c[0], 'visitas': c[1]}
            for c in categorias_populares
        ],
        'fecha_consulta': datetime.now().isoformat()
    })

# ============================================
# 3. FUNCIONES AUXILIARES
# ============================================

def obtener_subcategorias_por_categoria(nombre_categoria):
    """
    Devuelve las subcategorías predeterminadas para cada categoría.
    """
    subcategorias_map = {
        'Servicios Profesionales': ['Médicos', 'Abogados', 'Contadores', 'Ingenieros', 'Arquitectos', 'Consultores'],
        'Alimentos y Bebidas': ['Restaurantes', 'Cafeterías', 'Panaderías', 'Supermercados', 'Verdulerías', 'Carnicerías'],
        'Salud y Bienestar': ['Clínicas', 'Farmacias', 'Gimnasios', 'Spa', 'Terapias Alternativas', 'Laboratorios'],
        'Educación': ['Colegios', 'Universidades', 'Academias', 'Tutorías', 'Cursos Online', 'Talleres'],
        'Tecnología': ['Tiendas de Electrónica', 'Reparación de Celulares', 'Desarrollo de Software', 'Soporte Técnico'],
        'Hogar y Construcción': ['Ferreterías', 'Mueblerías', 'Constructoras', 'Decoración', 'Jardinería'],
        'Automotriz': ['Talleres Mecánicos', 'Lavaderos', 'Venta de Autos', 'Accesorios', 'Grúas'],
        'Entretenimiento': ['Cines', 'Teatros', 'Eventos', 'Parques', 'Juegos', 'Streaming'],
        'Moda y Belleza': ['Boutiques', 'Peluquerías', 'Estéticas', 'Joyerías', 'Calzado'],
        'Otros': ['Variedades', 'Servicios Generales', 'Importaciones', 'Regalos']
    }
    
    return subcategorias_map.get(nombre_categoria, ['General'])

def buscar_negocios_inteligente(query, contexto_usuario=None):
    """
    Búsqueda inteligente que considera el contexto del usuario.
    """
    from sqlalchemy import or_
    
    # Preparar términos de búsqueda
    terminos = query.lower().split()
    
    # Buscar coincidencias exactas primero
    negocios = Negocio.query.filter(
        or_(
            Negocio.nombre.ilike(f'%{query}%'),
            Negocio.palabras_clave.ilike(f'%{query}%')
        )
    ).all()
    
    # Si no hay resultados, buscar por términos individuales
    if not negocios:
        for termino in terminos:
            if len(termino) > 2:  # Ignorar palabras muy cortas
                nuevos = Negocio.query.filter(
                    or_(
                        Negocio.nombre.ilike(f'%{termino}%'),
                        Negocio.descripcion_corta.ilike(f'%{termino}%'),
                        Negocio.palabras_clave.ilike(f'%{termino}%')
                    )
                ).all()
                negocios.extend(nuevos)
    
    # Eliminar duplicados
    negocios_unicos = list({n.id: n for n in negocios}.values())
    
    # Ordenar por relevancia (visitas + agendamientos)
    negocios_unicos.sort(key=lambda x: (x.visitas * 0.3 + x.total_agendamientos * 0.7), reverse=True)
    
    return negocios_unicos[:10]  # Limitar a 10 resultados

# ============================================
# 4. FUNCIONES PARA N8N
# ============================================

def preparar_respuesta_whatsapp(negocio, tipo_mensaje='informacion'):
    """
    Prepara la respuesta estructurada para enviar por WhatsApp.
    """
    if tipo_mensaje == 'informacion':
        return {
            'type': 'template',
            'template': {
                'name': 'negocio_info',
                'language': {'code': 'es'},
                'components': [
                    {
                        'type': 'body',
                        'parameters': [
                            {'type': 'text', 'text': negocio.nombre},
                            {'type': 'text', 'text': negocio.descripcion_corta[:100]},
                            {'type': 'text', 'text': f"⭐ {negocio.calificacion_promedio or 'N/A'}"},
                            {'type': 'text', 'text': negocio.telefono_contacto or 'No disponible'}
                        ]
                    },
                    {
                        'type': 'button',
                        'sub_type': 'quick_reply',
                        'index': 0,
                        'parameters': [{'type': 'payload', 'payload': f'agendar_{negocio.id}'}]
                    }
                ]
            }
        }
    elif tipo_mensaje == 'confirmacion_agendamiento':
        return {
            'type': 'interactive',
            'interactive': {
                'type': 'button',
                'body': {'text': f"¿Confirmas el agendamiento con {negocio.nombre}?"},
                'action': {
                    'buttons': [
                        {'type': 'reply', 'reply': {'id': f'confirmar_{negocio.id}', 'title': '✅ Sí, confirmar'}},
                        {'type': 'reply', 'reply': {'id': 'cancelar', 'title': '❌ Cancelar'}}
                    ]
                }
            }
        }
    
    return {'type': 'text', 'text': 'Información no disponible'}


# ============================================
# 5. UTILIDADES DE FORMATO PARA WHATSAPP
# ============================================

def preparar_respuesta_whatsapp(tipo_mensaje, negocio=None, datos=None):
    """
    Genera el JSON estructurado que espera el nodo de WhatsApp en n8n
    basado en los campos actuales de la tabla Negocio.
    """
    if tipo_mensaje == 'perfil_negocio' and negocio:
        # Formato optimizado para mostrar el perfil tras la selección
        texto = (
            f"🏪 *{negocio.nombre}*\n"
            f"📝 {negocio.descripcion_corta}\n\n"
            f"📞 Contacto: {negocio.telefono_contacto}\n"
            f"--------------------------\n"
            f"¿Deseas que te contactemos con este negocio?"
        )
        return {'type': 'text', 'text': texto}
    
    elif tipo_mensaje == 'lista_simple':
        # Para menús numerados devueltos por la IA
        return {'type': 'text', 'text': datos}

    return {'type': 'text', 'text': 'Información no disponible'}