from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

# Tablas existentes (User, Producto, Servicio, Venta) permanecen igual
# ...

# CATEGORÍAS JERÁRQUICAS
class Categoria(db.Model):
    __tablename__ = 'categorias'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # 'producto', 'servicio', 'mixto'
    nivel = db.Column(db.Integer, default=1)  # 1: principal, 2: subcategoría, 3: especialidad
    parent_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=True)
    orden = db.Column(db.Integer, default=0)
    icono = db.Column(db.String(50), nullable=True)
    descripcion = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relaciones
    subcategorias = db.relationship('Subcategoria', backref='categoria', lazy=True, cascade='all, delete-orphan')
    children = db.relationship('Categoria', backref=db.backref('parent', remote_side=[id]), lazy=True)
    
    def __repr__(self):
        return f'<Categoria {self.nombre} (Nivel {self.nivel})>'

class Subcategoria(db.Model):
    __tablename__ = 'subcategorias'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=False)
    nivel = db.Column(db.Integer, default=2)  # 2: subcategoría, 3: especialidad
    parent_id = db.Column(db.Integer, db.ForeignKey('subcategorias.id'), nullable=True)
    descripcion = db.Column(db.Text, nullable=True)
    icono = db.Column(db.String(50), nullable=True)
    keywords = db.Column(db.Text, nullable=True)  # Palabras clave para búsqueda
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relaciones
    children = db.relationship('Subcategoria', backref=db.backref('parent', remote_side=[id]), lazy=True)
    
    def __repr__(self):
        return f'<Subcategoria {self.nombre}>'

# NUEVO MODELO: NEGOCIO/PROFILE
class Negocio(db.Model):
    __tablename__ = 'negocios'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer)
    nombre = db.Column(db.String(200), nullable=False)
    descripcion_corta = db.Column(db.String(300), nullable=False)
    descripcion_larga = db.Column(db.Text, nullable=True)
    
    # Contacto
    telefono_contacto = db.Column(db.String(20), nullable=True)
    whatsapp_contacto = db.Column(db.String(20), nullable=True)
    email_contacto = db.Column(db.String(100), nullable=True)
    sitio_web = db.Column(db.String(200), nullable=True)
    
    # Ubicación
    direccion = db.Column(db.String(300), nullable=True)
    latitud = db.Column(db.Numeric(10, 8), nullable=True)
    longitud = db.Column(db.Numeric(11, 8), nullable=True)
    ubicacion = db.Column(db.String(100), nullable=True)  # Barrio, ciudad
    
    # Multimedia
    url_presentacion = db.Column(db.String(500), nullable=True)  # PDF, video, imagen
    url_imagen_perfil = db.Column(db.String(500), nullable=True)
    tipo_media = db.Column(db.String(20), default='document')  # 'document', 'image', 'video'
    galeria = db.Column(db.Text, nullable=True)  # JSON con URLs de imágenes
    
    # Información adicional
    servicios = db.Column(db.Text, nullable=True)  # JSON con lista de servicios
    horarios = db.Column(db.Text, nullable=True)  # JSON con horarios
    precio_estimado = db.Column(db.Numeric(10, 2), nullable=True)
    palabras_clave = db.Column(db.Text, nullable=True)
    
    # Estadísticas
    visitas = db.Column(db.Integer, default=0)
    total_agendamientos = db.Column(db.Integer, default=0)
    calificacion_promedio = db.Column(db.Numeric(3, 2), default=0)
    total_resenas = db.Column(db.Integer, default=0)
    
    # Estado
    activo = db.Column(db.Boolean, default=True)
    destacado = db.Column(db.Boolean, default=False)
    verificacion = db.Column(db.String(20), default='pendiente')  # 'verificado', 'pendiente', 'rechazado'
    
    # Relaciones
    agendamientos = db.relationship('Agendamiento', backref='negocio', lazy=True)
    resenas = db.relationship('Resena', backref='negocio', lazy=True)
    
    def __repr__(self):
        return f'<Negocio {self.nombre}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion_corta': self.descripcion_corta,
            'telefono': self.telefono_contacto,
            'ubicacion': self.ubicacion,
            'calificacion': float(self.calificacion_promedio) if self.calificacion_promedio else None,
        }

# NUEVO MODELO: AGENDAMIENTO/LEAD
class Agendamiento(db.Model):
    __tablename__ = 'agendamientos'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Información del cliente
    cliente_nombre = db.Column(db.String(100), nullable=False)
    cliente_telefono = db.Column(db.String(20), nullable=False)
    cliente_email = db.Column(db.String(100), nullable=True)
    
    # Relación con negocio
    id_negocio = db.Column(db.Integer, db.ForeignKey('negocios.id'), nullable=False)
    
    # Detalles del agendamiento
    fecha_solicitud = db.Column(db.DateTime, default=datetime.now)
    fecha_agendada = db.Column(db.DateTime, nullable=True)
    estado = db.Column(db.String(20), default='pendiente')  # 'pendiente', 'confirmado', 'cancelado', 'completado'
    nota = db.Column(db.Text, nullable=True)
    
    # Metadata
    origen = db.Column(db.String(50), default='whatsapp')  # 'whatsapp', 'web', 'telefono'
    _metadata = db.Column(db.Text, nullable=True)  # JSON con información adicional
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<Agendamiento {self.id} - {self.cliente_nombre}>'

# MODELO OPCIONAL: RESEÑAS
class Resena(db.Model):
    __tablename__ = 'resenas'
    
    id = db.Column(db.Integer, primary_key=True)
    negocio_id = db.Column(db.Integer, db.ForeignKey('negocios.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    nombre_cliente = db.Column(db.String(100), nullable=False)
    calificacion = db.Column(db.Integer, nullable=False)  # 1-5
    comentario = db.Column(db.Text, nullable=True)
    verificado = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<Resena {self.id} - {self.calificacion} estrellas>'
    
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    role = db.Column(db.String(20), default='usuario')  # 'admin' o 'usuario'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    last_login = db.Column(db.DateTime, nullable=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def toggle_active(self):
        self.is_active = not self.is_active
        return self.is_active

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    precio = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    vendidos = db.Column(db.Integer, default=0)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'))
    subcategoria_id = db.Column(db.Integer, db.ForeignKey('subcategorias.id'))
    categoria = db.relationship('Categoria', backref=db.backref('productos', lazy=True))
    subcategoria = db.relationship('Subcategoria', backref=db.backref('productos', lazy=True))
    imagen_url = db.Column(db.String(255))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
class Servicio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    precio = db.Column(db.Float, nullable=False)
    vendidos = db.Column(db.Integer, default=0)
    duracion = db.Column(db.String(50))
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'))
    subcategoria_id = db.Column(db.Integer, db.ForeignKey('subcategorias.id'))
    categoria = db.relationship('Categoria', backref=db.backref('servicios', lazy=True))
    subcategoria = db.relationship('Subcategoria', backref=db.backref('servicios', lazy=True))
    imagen_url = db.Column(db.String(255))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class Venta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=datetime.now)
    tipo = db.Column(db.String(10))  # 'producto' o 'servicio'
    item_id = db.Column(db.Integer, nullable=False)
    cantidad = db.Column(db.Integer, default=1)
    total = db.Column(db.Float, nullable=False)
    vendedor_id = db.Column(db.Integer, db.ForeignKey('user.id'))