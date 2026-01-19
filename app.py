from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from messenger import enviar_mensaje_whatsapp
from models import db, User, Producto, Servicio, Venta, Categoria, Subcategoria
from datetime import datetime
import re, os, dotenv

from utils import generar_contrasena_segura
from funciones import api_bp, inicializar_estructura_chatbot, preparar_respuesta_whatsapp

dotenv.load_dotenv()

s_key = os.environ.get('SECRET_KEY')
db_uri = os.environ.get('SQLALCHEMY_DATABASE_URI')

app = Flask(__name__)
app.config['SECRET_KEY'] = s_key
app.config['SQLALCHEMY_DATABASE_URI'] =  db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar extensiones
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# REGISTRAR BLUEPRINT DE API
app.register_blueprint(api_bp)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Decorador para verificar si es admin
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Acceso denegado. Se requieren permisos de administrador.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Crear datos iniciales
def crear_datos_iniciales():
    # Crear usuario admin si no existe
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin', 
            email='admin@example.com',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
    
    # Crear categorías de productos
    categorias_productos = [
        'Electrónica', 'Ropa', 'Hogar', 'Deportes', 'Libros', 
        'Juguetes', 'Belleza', 'Alimentos', 'Muebles', 'Herramientas'
    ]
    
    # Crear categorías de servicios
    categorias_servicios = [
        'Consultoría', 'Mantenimiento', 'Educación', 'Salud', 
        'Transporte', 'Reparaciones', 'Diseño', 'Desarrollo', 
        'Marketing', 'Legal'
    ]
    
    admin_user = User.query.filter_by(username='admin').first()
    
    # Crear categorías de productos
    for cat_nombre in categorias_productos:
        if not Categoria.query.filter_by(nombre=cat_nombre, tipo='producto').first():
            categoria = Categoria(
                nombre=cat_nombre, 
                tipo='producto',
                created_by=admin_user.id
            )
            db.session.add(categoria)
            db.session.flush()
            
            # Crear subcategorías
            if cat_nombre == 'Electrónica':
                subcats = ['Smartphones', 'Laptops', 'Tablets', 'Accesorios']
            elif cat_nombre == 'Ropa':
                subcats = ['Hombre', 'Mujer', 'Niños', 'Deportiva']
            elif cat_nombre == 'Hogar':
                subcats = ['Cocina', 'Baño', 'Decoración', 'Limpieza']
            else:
                subcats = [f'{cat_nombre} Básico', f'{cat_nombre} Premium']
            
            for subcat_nombre in subcats:
                subcat = Subcategoria(
                    nombre=subcat_nombre, 
                    categoria_id=categoria.id,
                    created_by=admin_user.id
                )
                db.session.add(subcat)
    
    # Crear categorías de servicios
    for cat_nombre in categorias_servicios:
        if not Categoria.query.filter_by(nombre=cat_nombre, tipo='servicio').first():
            categoria = Categoria(
                nombre=cat_nombre, 
                tipo='servicio',
                created_by=admin_user.id
            )
            db.session.add(categoria)
            db.session.flush()
            
            # Crear subcategorías
            if cat_nombre == 'Consultoría':
                subcats = ['Empresarial', 'Técnica', 'Financiera', 'Marketing']
            elif cat_nombre == 'Mantenimiento':
                subcats = ['Preventivo', 'Correctivo', 'Predictivo', 'General']
            elif cat_nombre == 'Educación':
                subcats = ['Tutorías', 'Cursos', 'Talleres', 'Asesorías']
            else:
                subcats = [f'{cat_nombre} Básico', f'{cat_nombre} Especializado']
            
            for subcat_nombre in subcats:
                subcat = Subcategoria(
                    nombre=subcat_nombre, 
                    categoria_id=categoria.id,
                    created_by=admin_user.id
                )
                db.session.add(subcat)
    
    # Crear productos de ejemplo
    if Producto.query.count() == 0:
        categoria_electronica = Categoria.query.filter_by(nombre='Electrónica', tipo='producto').first()
        subcat_laptops = Subcategoria.query.filter_by(nombre='Laptops', categoria_id=categoria_electronica.id).first()
        
        productos_ejemplo = [
            Producto(
                nombre='Laptop HP EliteBook', 
                descripcion='Laptop de alta gama para profesionales', 
                precio=1200.00, 
                stock=10, 
                vendidos=5,
                categoria_id=categoria_electronica.id,
                subcategoria_id=subcat_laptops.id,
                imagen_url='https://via.placeholder.com/300x200?text=Laptop+HP',
                created_by=admin_user.id
            ),
        ]
        
        for producto in productos_ejemplo:
            db.session.add(producto)
    
    # Crear servicios de ejemplo
    if Servicio.query.count() == 0:
        categoria_consultoria = Categoria.query.filter_by(nombre='Consultoría', tipo='servicio').first()
        subcat_empresarial = Subcategoria.query.filter_by(nombre='Empresarial', categoria_id=categoria_consultoria.id).first()
        
        servicios_ejemplo = [
            Servicio(
                nombre='Consultoría Empresarial', 
                descripcion='Asesoría para optimización de procesos empresariales', 
                precio=100.00, 
                vendidos=8, 
                duracion='2 horas',
                categoria_id=categoria_consultoria.id,
                subcategoria_id=subcat_empresarial.id,
                imagen_url='https://via.placeholder.com/300x200?text=Consultoría',
                created_by=admin_user.id
            ),
        ]
        
        for servicio in servicios_ejemplo:
            db.session.add(servicio)
    
    db.session.commit()

# Crear tablas y datos iniciales
with app.app_context():
    db.create_all()
    crear_datos_iniciales()

# Funciones auxiliares
def validar_email(email):
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(pattern, email) is not None

def validar_password(password):
    # Mínimo 8 caracteres, al menos una mayúscula, una minúscula y un número
    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres"
    
    if not any(c.isupper() for c in password):
        return False, "La contraseña debe tener al menos una letra mayúscula"
    
    if not any(c.islower() for c in password):
        return False, "La contraseña debe tener al menos una letra minúscula"
    
    if not any(c.isdigit() for c in password):
        return False, "La contraseña debe tener al menos un número"
    
    return True, "Contraseña válida"

# RUTAS PRINCIPALES
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('Tu cuenta está desactivada. Contacta al administrador.', 'error')
                return redirect(url_for('login'))
            
            login_user(user)
            user.last_login = datetime.now()
            db.session.commit()
            flash('¡Inicio de sesión exitoso!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión', 'info')
    return redirect(url_for('login'))

@app.route('/vender/<tipo>/<int:id>')
@login_required
def vender(tipo, id):
    if tipo == 'producto':
        item = Producto.query.get(id)
        if item and item.stock > 0:
            item.vendidos += 1
            item.stock -= 1
            
            venta = Venta(
                tipo='producto',
                item_id=id,
                cantidad=1,
                total=item.precio,
                vendedor_id=current_user.id
            )
            db.session.add(venta)
            db.session.commit()
            flash(f'Producto {item.nombre} vendido exitosamente', 'success')
    elif tipo == 'servicio':
        item = Servicio.query.get(id)
        if item:
            item.vendidos += 1
            
            venta = Venta(
                tipo='servicio',
                item_id=id,
                cantidad=1,
                total=item.precio,
                vendedor_id=current_user.id
            )
            db.session.add(venta)
            db.session.commit()
            flash(f'Servicio {item.nombre} vendido exitosamente', 'success')
    
    return redirect(url_for('dashboard'))

@app.route('/admin/usuario/nuevo', methods=['GET', 'POST'])
@login_required
@admin_required
def nuevo_usuario():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            role = request.form.get('role', 'usuario')
            
            # Validaciones
            if User.query.filter_by(username=username).first():
                flash('El nombre de usuario ya existe', 'error')
                return redirect(url_for('nuevo_usuario'))
                        
            valid_pass, msg = validar_password(password)
            if not valid_pass:
                flash(msg, 'error')
                return redirect(url_for('nuevo_usuario'))
            
            # Crear usuario
            user = User(
                username=username,
                role=role
            )
            user.set_password(password)

            msg = f"""Tu registro en la plataforma de vecinos ha sido realizada con exito. 
            Registra tus productos y servicios en (url)
            *usuario*: {username}
            *clave*: {password}"""
            enviar_msg = enviar_mensaje_whatsapp(username, msg)
            if enviar_msg in (200, 201, 202):
                db.session.add(user)
                db.session.commit()
            flash('Usuario creado exitosamente', 'success')
            return redirect(url_for('admin_usuarios'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear el usuario: {str(e)}', 'error')
    # elif request.method == 'GET':
        
    return render_template('nuevo_usuario.html', psw=generar_contrasena_segura())

@app.route('/admin/usuario/<int:user_id>/toggle')
@login_required
@admin_required
def toggle_usuario(user_id):
    if user_id == current_user.id:
        flash('No puedes modificar tu propio estado', 'error')
        return redirect(url_for('admin_usuarios'))
    
    user = User.query.get_or_404(user_id)
    nuevo_estado = user.toggle_active()
    db.session.commit()
    
    estado = "activada" if nuevo_estado else "desactivada"
    flash(f'Cuenta {estado} exitosamente', 'success')
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/usuario/<int:user_id>/cambiar_rol', methods=['POST'])
@login_required
@admin_required
def cambiar_rol_usuario(user_id):
    if user_id == current_user.id:
        flash('No puedes modificar tu propio rol', 'error')
        return redirect(url_for('admin_usuarios'))
    
    user = User.query.get_or_404(user_id)
    nuevo_rol = request.form.get('role')
    
    if nuevo_rol in ['admin', 'usuario']:
        user.role = nuevo_rol
        db.session.commit()
        flash(f'Rol cambiado a {nuevo_rol} exitosamente', 'success')
    
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/usuario/<int:user_id>/eliminar')
@login_required
@admin_required
def eliminar_usuario(user_id):
    if user_id == current_user.id:
        flash('No puedes eliminar tu propia cuenta', 'error')
        return redirect(url_for('admin_usuarios'))
    
    user = User.query.get_or_404(user_id)
    
    # Verificar si el usuario tiene registros asociados
    if Producto.query.filter_by(created_by=user_id).first() or \
       Servicio.query.filter_by(created_by=user_id).first():
        flash('No se puede eliminar el usuario porque tiene registros asociados', 'error')
        return redirect(url_for('admin_usuarios'))
    
    db.session.delete(user)
    db.session.commit()
    flash('Usuario eliminado exitosamente', 'success')
    return redirect(url_for('admin_usuarios'))



@app.route('/categorias/nueva', methods=['POST'])
@login_required
@admin_required
def nueva_categoria():
    nombre = request.form.get('nombre')
    tipo = request.form.get('tipo')
    
    if nombre and tipo:
        if Categoria.query.filter_by(nombre=nombre, tipo=tipo).first():
            flash('Esta categoría ya existe', 'error')
        else:
            categoria = Categoria(
                nombre=nombre, 
                tipo=tipo,
                created_by=current_user.id
            )
            db.session.add(categoria)
            db.session.commit()
            flash('Categoría creada exitosamente', 'success')
    
    return redirect(url_for('gestion_categorias'))

@app.route('/subcategorias/nueva', methods=['POST'])
@login_required
@admin_required
def nueva_subcategoria():
    nombre = request.form.get('nombre')
    categoria_id = request.form.get('categoria_id')
    
    if nombre and categoria_id:
        if Subcategoria.query.filter_by(nombre=nombre, categoria_id=categoria_id).first():
            flash('Esta subcategoría ya existe', 'error')
        else:
            subcategoria = Subcategoria(
                nombre=nombre, 
                categoria_id=int(categoria_id),
                created_by=current_user.id
            )
            db.session.add(subcategoria)
            db.session.commit()
            flash('Subcategoría creada exitosamente', 'success')
    
    return redirect(url_for('gestion_categorias'))

# RUTA PARA SUBRECATEGORÍAS (AJAX - disponible para todos los usuarios autenticados)
@app.route('/api/subcategorias/<int:categoria_id>')
@login_required
def get_subcategorias(categoria_id):
    subcategorias = Subcategoria.query.filter_by(categoria_id=categoria_id).all()
    return jsonify([{'id': s.id, 'nombre': s.nombre} for s in subcategorias])


# Agregar una función para contexto común
@app.context_processor
def inject_user_data():
    if current_user.is_authenticated:
        return {
            'es_admin': current_user.is_admin(),
            'current_user': current_user
        }
    return {}


###
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin():
        # Administradores ven TODO
        total_productos = Producto.query.count()
        total_servicios = Servicio.query.count()
        productos_vendidos = sum(p.vendidos for p in Producto.query.all())
        servicios_vendidos = sum(s.vendidos for s in Servicio.query.all())
        productos = Producto.query.all()
        servicios = Servicio.query.all()
        ventas_realizadas = Venta.query.filter_by(vendedor_id=current_user.id).count()
    else:
        # Usuarios normales solo ven lo que ellos crearon
        total_productos = Producto.query.filter_by(created_by=current_user.id).count()
        total_servicios = Servicio.query.filter_by(created_by=current_user.id).count()
        
        # Productos creados por el usuario
        mis_productos = Producto.query.filter_by(created_by=current_user.id).all()
        productos_vendidos = sum(p.vendidos for p in mis_productos)
        
        # Servicios creados por el usuario
        mis_servicios = Servicio.query.filter_by(created_by=current_user.id).all()
        servicios_vendidos = sum(s.vendidos for s in mis_servicios)
        
        productos = mis_productos
        servicios = mis_servicios
        ventas_realizadas = Venta.query.filter_by(vendedor_id=current_user.id).count()
    
    return render_template('dashboard.html',
                         page_title='Dashboard',
                         total_productos=total_productos,
                         total_servicios=total_servicios,
                         productos_vendidos=productos_vendidos,
                         servicios_vendidos=servicios_vendidos,
                         productos=productos,
                         servicios=servicios,
                         ventas_realizadas=ventas_realizadas,
                         es_admin=current_user.is_admin())


# Actualizar rutas de productos y servicios para que todos puedan crear
@app.route('/productos/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_producto():
    categorias = Categoria.query.filter_by(tipo='producto').all()
    
    if request.method == 'POST':
        try:
            # Verificar si es admin o usuario normal
            if current_user.is_admin():
                # Admins pueden asignar cualquier creador (o dejarlo como ellos)
                created_by = int(request.form.get('created_by', current_user.id))
            else:
                # Usuarios normales solo pueden crear para sí mismos
                created_by = current_user.id
            
            producto = Producto(
                nombre=request.form.get('nombre'),
                descripcion=request.form.get('descripcion'),
                precio=float(request.form.get('precio')),
                stock=int(request.form.get('stock', 0)),
                categoria_id=int(request.form.get('categoria')) if request.form.get('categoria') else None,
                subcategoria_id=int(request.form.get('subcategoria')) if request.form.get('subcategoria') else None,
                imagen_url=request.form.get('imagen_url', ''),
                created_by=created_by
            )
            
            db.session.add(producto)
            db.session.commit()
            flash('Producto creado exitosamente', 'success')
            return redirect(url_for('dashboard'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear el producto: {str(e)}', 'error')
    
    # Pasar lista de usuarios solo si es admin
    usuarios = User.query.all() if current_user.is_admin() else None
    
    return render_template('nuevo_producto.html', 
                         categorias=categorias,
                         usuarios=usuarios,
                         es_admin=current_user.is_admin())

@app.route('/servicios/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_servicio():
    categorias = Categoria.query.filter_by(tipo='servicio').all()
    
    if request.method == 'POST':
        try:
            # Verificar si es admin o usuario normal
            if current_user.is_admin():
                # Admins pueden asignar cualquier creador
                created_by = int(request.form.get('created_by', current_user.id))
            else:
                # Usuarios normales solo pueden crear para sí mismos
                created_by = current_user.id
            
            servicio = Servicio(
                nombre=request.form.get('nombre'),
                descripcion=request.form.get('descripcion'),
                precio=float(request.form.get('precio')),
                duracion=request.form.get('duracion'),
                categoria_id=int(request.form.get('categoria')) if request.form.get('categoria') else None,
                subcategoria_id=int(request.form.get('subcategoria')) if request.form.get('subcategoria') else None,
                imagen_url=request.form.get('imagen_url', ''),
                created_by=created_by
            )
            
            db.session.add(servicio)
            db.session.commit()
            flash('Servicio creado exitosamente', 'success')
            return redirect(url_for('dashboard'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear el servicio: {str(e)}', 'error')
    
    # Pasar lista de usuarios solo si es admin
    usuarios = User.query.all() if current_user.is_admin() else None
    
    return render_template('nuevo_servicio.html',
                         categorias=categorias,
                         usuarios=usuarios,
                         es_admin=current_user.is_admin())

# Agregar función para editar/eliminar productos (solo admin o creador)
@app.route('/productos/<int:id>/eliminar')
@login_required
def eliminar_producto(id):
    producto = Producto.query.get_or_404(id)
    
    # Verificar permisos
    if not current_user.is_admin() and producto.created_by != current_user.id:
        flash('No tienes permisos para eliminar este producto', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        db.session.delete(producto)
        db.session.commit()
        flash('Producto eliminado exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el producto: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/servicios/<int:id>/eliminar')
@login_required
def eliminar_servicio(id):
    servicio = Servicio.query.get_or_404(id)
    
    # Verificar permisos
    if not current_user.is_admin() and servicio.created_by != current_user.id:
        flash('No tienes permisos para eliminar este servicio', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        db.session.delete(servicio)
        db.session.commit()
        flash('Servicio eliminado exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el servicio: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))
###

@app.route('/admin/usuarios')
@login_required
@admin_required
def admin_usuarios():
    usuarios = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin_usuarios.html',
                         page_title='Administrar Usuarios',
                         usuarios=usuarios)


@app.route('/categorias')
@login_required
@admin_required
def gestion_categorias():
    categorias_productos = Categoria.query.filter_by(tipo='producto').all()
    categorias_servicios = Categoria.query.filter_by(tipo='servicio').all()
    return render_template('categorias.html',
                         page_title='Gestionar Categorías',
                         categorias_productos=categorias_productos,
                         categorias_servicios=categorias_servicios)

@app.route('/perfil')
@login_required
def perfil():
    # Obtener estadísticas del usuario
    productos_creados = Producto.query.filter_by(created_by=current_user.id).count()
    servicios_creados = Servicio.query.filter_by(created_by=current_user.id).count()
    ventas_realizadas = Venta.query.filter_by(vendedor_id=current_user.id).count()
    
    return render_template('perfil.html',
                         page_title='Mi Perfil',
                         productos_creados=productos_creados,
                         servicios_creados=servicios_creados,
                         ventas_realizadas=ventas_realizadas)

def crear_datos_iniciales():
    """
    Función actualizada para crear datos iniciales incluyendo estructura del chatbot.
    """
    # Crear usuario admin (código existente)
    # ...
    
    # Inicializar estructura del chatbot
    inicializar_estructura_chatbot()
    
    # Crear negocios de ejemplo
    if Negocio.query.count() == 0:
        # Obtener categorías
        subcat_medicos = Subcategoria.query.filter_by(nombre='Médicos').first()
        subcat_panaderias = Subcategoria.query.filter_by(nombre='Panaderías').first()
        
        # Negocio de ejemplo: Médico
        if subcat_medicos:
            negocio_medico = Negocio(
                nombre='Dr. Carlos Freire',
                descripcion_corta='Médico general con 15 años de experiencia. Atención primaria integral.',
                descripcion_larga='Especialista en medicina general con enfoque preventivo. Atención a niños y adultos. Consultorio equipado con tecnología moderna.',
                subcategoria_id=subcat_medicos.id,
                tipo='servicio',
                telefono_contacto='+593987654321',
                whatsapp_contacto='+593987654321',
                email_contacto='dr.carlos.freire@clinica.com',
                direccion='Av. Principal 123, Centro Médico San José',
                ubicacion='Quito, Ecuador',
                url_presentacion='https://tuservidor.com/files/presentacion_carlos.pdf',
                url_imagen_perfil='https://via.placeholder.com/300x300?text=Dr.+Carlos+Freire',
                tipo_media='document',
                servicios=json.dumps(['Consulta General', 'Control de Presión', 'Vacunación', 'Chequeos Anuales']),
                horarios=json.dumps({'lunes_viernes': '8:00-18:00', 'sabado': '9:00-13:00'}),
                precio_estimado=50.00,
                palabras_clave='medico, doctor, salud, consulta, general, pediatria',
                calificacion_promedio=4.8,
                total_resenas=24,
                created_by=admin_user.id
            )
            db.session.add(negocio_medico)
        
        # Negocio de ejemplo: Panadería
        if subcat_panaderias:
            negocio_panaderia = Negocio(
                nombre='Panadería El Buen Pan',
                descripcion_corta='Panadería tradicional con más de 20 años de experiencia. Productos frescos diariamente.',
                descripcion_larga='Especialistas en panadería y pastelería tradicional. Contamos con más de 50 variedades de pan y 30 tipos de pasteles. Productos horneados con ingredientes naturales.',
                subcategoria_id=subcat_panaderias.id,
                tipo='producto',
                telefono_contacto='+593912345678',
                whatsapp_contacto='+593912345678',
                direccion='Calle Panamérica 456, Sector Norte',
                ubicacion='Guayaquil, Ecuador',
                url_presentacion='https://tuservidor.com/files/catalogo_panaderia.pdf',
                url_imagen_perfil='https://via.placeholder.com/300x300?text=Panaderia+El+Buen+Pan',
                tipo_media='image',
                servicios=json.dumps(['Panadería Tradicional', 'Pastelería Finа', 'Pedidos Especiales', 'Catering']),
                horarios=json.dumps({'lunes_domingo': '5:00-22:00'}),
                precio_estimado=2.50,
                palabras_clave='panaderia, pan, pasteles, dulces, reposteria, horneados',
                calificacion_promedio=4.5,
                total_resenas=18,
                created_by=admin_user.id
            )
            db.session.add(negocio_panaderia)
        
        db.session.commit()

# ... (rutas existentes)

# NUEVAS RUTAS PARA GESTIÓN DE NEGOCIOS (opcional, para administración web)
@app.route('/admin/negocios')
@login_required
@admin_required
def admin_negocios():
    """
    Panel de administración de negocios.
    """
    negocios = Negocio.query.order_by(Negocio.created_at.desc()).all()
    return render_template('admin_negocios.html',
                         page_title='Administrar Negocios',
                         negocios=negocios)

@app.route('/admin/negocios/nuevo', methods=['GET', 'POST'])
@login_required
@admin_required
def nuevo_negocio():
    """
    Crear nuevo negocio desde la interfaz web.
    """
    categorias = Categoria.query.filter_by(nivel=1).all()
    
    if request.method == 'POST':
        try:
            negocio = Negocio(
                nombre=request.form.get('nombre'),
                descripcion_corta=request.form.get('descripcion_corta'),
                descripcion_larga=request.form.get('descripcion_larga'),
                subcategoria_id=int(request.form.get('subcategoria_id')),
                tipo=request.form.get('tipo'),
                telefono_contacto=request.form.get('telefono_contacto'),
                whatsapp_contacto=request.form.get('whatsapp_contacto'),
                email_contacto=request.form.get('email_contacto'),
                direccion=request.form.get('direccion'),
                ubicacion=request.form.get('ubicacion'),
                url_presentacion=request.form.get('url_presentacion'),
                url_imagen_perfil=request.form.get('url_imagen_perfil'),
                precio_estimado=float(request.form.get('precio_estimado', 0)),
                created_by=current_user.id
            )
            
            db.session.add(negocio)
            db.session.commit()
            flash('Negocio creado exitosamente', 'success')
            return redirect(url_for('admin_negocios'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear el negocio: {str(e)}', 'error')
    
    return render_template('nuevo_negocio.html',
                         categorias=categorias,
                         page_title='Nuevo Negocio')

# RUTAS PARA EDITAR PRODUCTOS
@app.route('/productos/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_producto(id):
    producto = Producto.query.get_or_404(id)
    
    # Verificar permisos (solo admin o el creador)
    if not current_user.is_admin() and producto.created_by != current_user.id:
        flash('No tienes permisos para editar este producto', 'error')
        return redirect(url_for('dashboard'))
    
    categorias = Categoria.query.filter_by(tipo='producto').all()
    
    if request.method == 'POST':
        try:
            producto.nombre = request.form.get('nombre')
            producto.descripcion = request.form.get('descripcion')
            producto.precio = float(request.form.get('precio'))
            producto.stock = int(request.form.get('stock', 0))
            
            # Manejo de categorías (opcional)
            cat_id = request.form.get('categoria')
            subcat_id = request.form.get('subcategoria')
            
            if cat_id:
                producto.categoria_id = int(cat_id)
            if subcat_id:
                producto.subcategoria_id = int(subcat_id)
                
            producto.imagen_url = request.form.get('imagen_url')
            
            db.session.commit()
            flash('Producto actualizado exitosamente', 'success')
            return redirect(url_for('dashboard'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar el producto: {str(e)}', 'error')
    
    return render_template('editar_item.html', 
                         item=producto, 
                         tipo='producto',
                         categorias=categorias,
                         page_title='Editar Producto')

# RUTAS PARA EDITAR SERVICIOS
@app.route('/servicios/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_servicio(id):
    servicio = Servicio.query.get_or_404(id)
    
    # Verificar permisos
    if not current_user.is_admin() and servicio.created_by != current_user.id:
        flash('No tienes permisos para editar este servicio', 'error')
        return redirect(url_for('dashboard'))
    
    categorias = Categoria.query.filter_by(tipo='servicio').all()
    
    if request.method == 'POST':
        try:
            servicio.nombre = request.form.get('nombre')
            servicio.descripcion = request.form.get('descripcion')
            servicio.precio = float(request.form.get('precio'))
            servicio.duracion = request.form.get('duracion')
            
            # Manejo de categorías
            cat_id = request.form.get('categoria')
            subcat_id = request.form.get('subcategoria')
            
            if cat_id:
                servicio.categoria_id = int(cat_id)
            if subcat_id:
                servicio.subcategoria_id = int(subcat_id)
                
            servicio.imagen_url = request.form.get('imagen_url')
            
            db.session.commit()
            flash('Servicio actualizado exitosamente', 'success')
            return redirect(url_for('dashboard'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar el servicio: {str(e)}', 'error')
    
    return render_template('editar_item.html', 
                         item=servicio, 
                         tipo='servicio',
                         categorias=categorias,
                         page_title='Editar Servicio')

@app.route('/api/vendedores/<int:subcategoria_id>')
def get_vendedores_por_subcategoria(subcategoria_id):
    # Buscamos productos y servicios que pertenezcan a esta subcategoría
    productos = Producto.query.filter_by(subcategoria_id=subcategoria_id).all()
    servicios = Servicio.query.filter_by(subcategoria_id=subcategoria_id).all()
    
    # Extraemos los IDs de los creadores (vendedores) únicos
    vendedores_ids = set([p.created_by for p in productos] + [s.created_by for s in servicios])
    
    resultados = []
    for v_id in vendedores_ids:
        user = User.query.get(v_id)
        if user:
            # Aquí podrías personalizar para que devuelva el nombre del negocio 
            # si tuvieras una tabla 'Negocio', pero usaremos el username según tu app.py
            resultados.append({
                'id': user.id,
                'nombre_vendedor': user.username,
                'rol': user.role
            })
            
    return jsonify(resultados)

if __name__ == '__main__':
    app.run(debug=True, port=5000)