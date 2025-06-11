import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
import pymysql
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from config import get_db_connection, SECRET_KEY
from pymongo import MongoClient
from config import MONGO_URI, MONGO_DB, MONGO_COLECCION
from flask import jsonify
from datetime import datetime, date
import csv
from io import TextIOWrapper
from flask import current_app

mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client[MONGO_DB]
coleccion_mensajes = mongo_db[MONGO_COLECCION]
db=mongo_client

app = Flask(__name__)
app.config['PREFERRED_URL_SCHEME'] = 'https'
app.secret_key = SECRET_KEY

# Función que se activa cuando se accede a la raíz del sitio web, esta función vale para redirigir a los usuarios que se encuentran logueados o no logueados cuando
# acceden a la raíz

@app.route('/')
def root():
    # Comprobamos que el usuario que ha iniciado sesión contiene su DNI guardado en la sesión
    if 'usuario_dni' in session:

        # Si el usuario se ha logueado con el DNI lo lleva a la página principal que es /home
        return redirect(url_for('home'))
    
    # Si el usuario no se encuentra logueado, lo lleva a la página de logueo que es /login
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        dni = request.form['dni']
        password = request.form['password']
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT nombre, password, id_perfil_profesores FROM Profesores WHERE dni = %s", (dni,))
            user = cursor.fetchone()
        connection.close()

        if user and check_password_hash(user['password'], password):
            session['usuario_dni'] = dni
            session['username'] = user['nombre']
            return redirect(url_for('home'))
        return render_template('login.html', mensaje="DNI o contraseña incorrectos.")

    return render_template('login.html')

# Función que se activa cuando accedemos a /home
@app.route('/home')
def home():
    # Comprobamos que el usuario se ha autenticado
    if 'usuario_dni' in session:
        # Realizamos una conexión a la base de datos
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Realizamos una consulta a la base de datos en la cual nos devolverá el perfil que tiene el profesor con el DNI que se ha logueado.
            cursor.execute("SELECT id_perfil_profesores FROM Profesores WHERE dni = %s", (session['usuario_dni'],))
            perfil = cursor.fetchone()
        connection.close()

        # Si el perfil que nos devuelve del usuario es 1, indicamos que es un profesor y hace que cargue la plantilla html para profesores
        if perfil and perfil['id_perfil_profesores'] == 1:
            return render_template('home_profesor.html', username=session.get('username'))
        else:
            # En caso de ser dirección u otro diferente carga la plantilla html de dirección que es la home
            return render_template('home.html', username=session.get('username'))
    return redirect(url_for('login'))

#HORARIOS#

# Función que muestra el horario del profesor que se encuentra actualmente logueado.
@app.route('/horario')
def ver_horario():
    # En caso de que no haya una sesión iniciada, lo redirige al login para que el usuario se logue
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    # Se realiza una conexión a la base de datos
    connection = get_db_connection()
    with connection.cursor() as cursor:
        # Realizamos la primera consulta la cual obtendrá todos los días de la semana que hay en esa tabla y lo ordena por el identificador y los valores que devuelve
        # los almacena en la variable días.
        cursor.execute("SELECT * FROM Dias_Semana ORDER BY id_dia")
        dias = cursor.fetchall()

        # Realizamos una segunda consulta en la cual obtenemos todos los tramos horarios que hay en esa tabla, esta se encuentra ordenador por el identificador 
        # y los valores que devuelve los almacena en la variable tramos.
        cursor.execute("SELECT * FROM Tramos_Horarios ORDER BY id_tramo")
        tramos = cursor.fetchall()

        # Realizamos esta tercera consulta en la cual obtenemos el horario del profesor que hay actualmente logueado.
        cursor.execute("""
            SELECT horarios.id_dia_horarios, horarios.id_tramo_horarios, asignaturas.nombre AS asignatura, grupo.nombre AS grupo, aula.nombre AS aula
            FROM Horarios horarios
            JOIN Asignaturas asignaturas ON horarios.id_asignatura_horarios = asignaturas.id_asignatura
            LEFT JOIN Grupos grupo ON horarios.id_grupo_horarios = grupo.id_grupo
            LEFT JOIN Aulas aula ON horarios.id_aula = aula.id_aula
            WHERE horarios.dni_profesor_horarios = %s
        """, (session['usuario_dni'],))
        datos = cursor.fetchall()

    # Cerramos la conexión de la base de datos
    connection.close()

    # Crear diccionario clave: (id_dia, id_tramo) => valor con asignatura, grupo y aula
    horario = {}
    for fila in datos:
        clave = (fila['id_dia_horarios'], fila['id_tramo_horarios'])
        horario[clave] = {
            'asignatura': fila['asignatura'],
            'grupo': fila['grupo'] or '',
            'aula': fila['aula'] or ''
        }

    return render_template("ver_horario.html", dias=dias, tramos=tramos, horario=horario)

@app.route('/horario/otros', methods=['GET', 'POST'])
def ver_horario_profesores():
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    connection = get_db_connection()
    horario = []
    profesor_seleccionado = None

    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT dni, CONCAT(nombre, ' ', apellidos) AS nombre_completo FROM Profesores")
        profesores = cursor.fetchall()

        if request.method == 'POST':
            profesor_seleccionado = request.form['dni_profesor']
            cursor.execute("""
                SELECT ds.nombre AS dia, th.horario, g.nombre AS grupo, a.nombre AS asignatura, au.nombre AS aula
                FROM Horarios h
                JOIN Dias_Semana ds ON h.id_dia_horarios = ds.id_dia
                JOIN Tramos_Horarios th ON h.id_tramo_horarios = th.id_tramo
                LEFT JOIN Grupos g ON h.id_grupo_horarios = g.id_grupo
                JOIN Asignaturas a ON h.id_asignatura_horarios = a.id_asignatura
                LEFT JOIN Aulas au ON h.id_aula = au.id_aula
                WHERE h.dni_profesor_horarios = %s
                ORDER BY ds.id_dia, th.id_tramo
            """, (profesor_seleccionado,))
            horario = cursor.fetchall()

    connection.close()
    return render_template("ver_horario_profesores.html", profesores=profesores, horario=horario, profesor_dni=profesor_seleccionado)

#INSERCCIÓN DE DATOS #

@app.route('/profesores/registrar', methods=['GET', 'POST'])
def registrar_profesor():
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    mensaje = ""
    if request.method == 'POST':
        dni = request.form['dni']
        nombre = request.form['nombre']
        apellidos = request.form['apellidos']
        email = request.form['email']
        password = request.form['password']
        id_perfil = int(request.form['perfil'])  # Desplegable actualizado
        password_hash = generate_password_hash(password)

        if not all([dni, nombre, apellidos, email, password, id_perfil]):
            mensaje = "Todos los campos son obligatorios."
        else:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                try:
                    cursor.execute("""
                        INSERT INTO Profesores (dni, nombre, apellidos, email, password, id_perfil_profesores)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (dni, nombre, apellidos, email, password_hash, id_perfil))
                    connection.commit()
                    mensaje = "Profesor registrado correctamente."
                except pymysql.err.IntegrityError:
                    mensaje = "El profesor ya existe con ese DNI o correo."
            connection.close()

    return render_template('registrar_profesor.html', mensaje=mensaje)

# Subida de Archivos CSV

@app.route('/subida_profesorado', methods=['GET', 'POST'])
def subir_profesores():
    mensaje = ""
    if request.method == 'POST':
        if 'archivo' not in request.files:
            mensaje = "No se ha subido ningún archivo."
        else:
            archivo = request.files['archivo']
            if archivo.filename.endswith('.csv'):
                connection = get_db_connection()
                try:
                    archivo_stream = TextIOWrapper(archivo, encoding='utf-8')
                    reader = csv.DictReader(archivo_stream)
                    
                    insertados = 0
                    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                        for row in reader:
                            cursor.execute(
                                "SELECT COUNT(*) AS cuenta FROM Profesores WHERE dni = %s OR email = %s",
                                (row['dni'], row['email'])
                            )
                            resultado = cursor.fetchone()
                            if resultado['cuenta'] == 0:
                                password_encriptada = generate_password_hash(row['password'])
                                cursor.execute("""
                                    INSERT INTO Profesores (dni, nombre, apellidos, email, password, puntos_guardia, id_perfil_profesores)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                                """, (
                                    row['dni'],
                                    row['nombre'],
                                    row['apellidos'],
                                    row['email'],
                                    password_encriptada,
                                    int(row.get('puntos_guardia', 0)),
                                    int(row['id_perfil_profesores'])
                                ))
                                insertados += 1
                    connection.commit()
                    mensaje = f"Se han insertado {insertados} profesores nuevos."
                except Exception as ex:
                    mensaje = f"Error al procesar el archivo: {str(ex)}"
                finally:
                    connection.close()
            else:
                mensaje = "El archivo debe ser .csv"

    return render_template('subir_profesores.html', mensaje=mensaje)


@app.route('/subida_horarios', methods=['GET', 'POST'])
def subir_horarios():

    mensaje = ""
    if request.method == 'POST':
        if 'archivo' not in request.files:
            mensaje = "No se ha subido ningún archivo."
        else:
            archivo = request.files['archivo']
            if archivo.filename.endswith('.csv'):
                connection = get_db_connection()
                try:
                    archivo_stream = TextIOWrapper(archivo, encoding='utf-8')
                    reader = csv.DictReader(archivo_stream)

                    # Validar que se han detectado cabeceras
                    if not reader.fieldnames:
                        mensaje = "El archivo CSV no contiene cabeceras válidas."
                        return render_template('subir_horarios.html', mensaje=mensaje)

                    columnas_esperadas = ['dni_profesor_horarios', 'id_dia_horarios', 'id_tramo_horarios', 'id_grupo_horarios', 'id_asignatura_horarios', 'id_aula']
                    print("Cabeceras detectadas:", reader.fieldnames)

                    for col in columnas_esperadas:
                        if col not in reader.fieldnames:
                            mensaje = f"Falta la columna '{col}' en el archivo CSV."
                            return render_template('subir_horarios.html', mensaje=mensaje)

                    insertados = 0
                    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                        for row in reader:
                            print("Fila leída:", row)
                            cursor.execute("""
                                SELECT COUNT(*) AS total
                                FROM Horarios
                                WHERE dni_profesor_horarios = %s AND id_dia_horarios = %s AND id_tramo_horarios = %s
                            """, (
                                row['dni_profesor_horarios'],
                                int(row['id_dia_horarios']),
                                int(row['id_tramo_horarios'])
                            ))
                            existe = cursor.fetchone()['total'] > 0

                            if not existe:
                                cursor.execute("""
                                    INSERT INTO Horarios (dni_profesor_horarios, id_dia_horarios, id_tramo_horarios, id_grupo_horarios, id_asignatura_horarios, id_aula)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                """, (
                                    row['dni_profesor_horarios'],
                                    int(row['id_dia_horarios']),
                                    int(row['id_tramo_horarios']),
                                    int(row['id_grupo_horarios']) if row['id_grupo_horarios'] else None,
                                    int(row['id_asignatura_horarios']),
                                    int(row['id_aula']) if row['id_aula'] else None
                                ))
                                insertados += 1

                        connection.commit()
                        mensaje = f"Se han insertado {insertados} registros de horario nuevos."
                except Exception as e:
                    mensaje = f"Error al procesar el archivo: {str(e)}"
                finally:
                    connection.close()
            else:
                mensaje = "El archivo debe ser .csv"

    return render_template('subir_horarios.html', mensaje=mensaje)

# Visualización de Horario del Profesor y Filtración para Visualizar Horarios de Otros Profesores

# Gestión de Puntuaciones #

@app.route('/puntuaciones', methods=['GET', 'POST'])
def gestionar_puntuaciones():
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    connection = get_db_connection()
    mensaje = ""

    if request.method == 'POST':
        with connection.cursor() as cursor:
            if 'resetear' in request.form:
                cursor.execute("UPDATE Profesores SET puntos_guardia = 0")
                mensaje = "Todas las puntuaciones se han restablecido."

            elif 'subir' in request.form:
                dni = request.form['subir']
                cursor.execute("UPDATE Profesores SET puntos_guardia = puntos_guardia + 1 WHERE dni = %s", (dni,))
                mensaje = f"Puntos aumentados para el profesor {dni}."

            elif 'bajar' in request.form:
                dni = request.form['bajar']
                cursor.execute("""
                    UPDATE Profesores
                    SET puntos_guardia = CASE
                        WHEN puntos_guardia > 0 THEN puntos_guardia - 1
                        ELSE 0
                    END
                    WHERE dni = %s
                """, (dni,))
                mensaje = f"Puntos reducidos para el profesor {dni}."

            connection.commit()

    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("""
            SELECT dni, nombre, apellidos, puntos_guardia
            FROM Profesores
            ORDER BY puntos_guardia DESC
        """)
        puntuaciones = cursor.fetchall()

    connection.close()
    return render_template('gestionar_puntuaciones.html', puntuaciones=puntuaciones, mensaje=mensaje)

# Gestionar Guardias #

@app.route('/guardias/gestionar', methods=['GET', 'POST'])
def gestionar_guardias():
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    connection = get_db_connection()
    mensaje = ""
    
    fecha_actual = date.today()
    dia_semana = fecha_actual.weekday() + 1

    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        # Obtener todos los tramos con ausencia para ese día
        cursor.execute("""
            SELECT th.id_tramo, th.horario, a.nombre AS aula_nombre,
                (
                    SELECT GROUP_CONCAT(CONCAT(p.nombre, ' ', p.apellidos) SEPARATOR ', ')
                    FROM Guardias g
                    JOIN Profesores p ON g.dni_profesor_guardias = p.dni
                    WHERE g.id_dia_guardias = %s AND g.id_tramo_guardias = th.id_tramo
                ) AS profesores_asignados
            FROM Tramos_Horarios th
            JOIN Ausencias aus ON aus.id_tramo_ausencias = th.id_tramo AND aus.fecha = %s
            LEFT JOIN Aulas a ON a.id_aula = aus.id_tramo_ausencias
            GROUP BY th.id_tramo, th.horario, a.nombre
            ORDER BY th.id_tramo
        """, (dia_semana, fecha_actual))
        guardias_dia = cursor.fetchall()

        # Buscar profesores con Guardia y sin otra asignatura, y que no estén ausentes
        profesores_disponibles = {}
        for guardia in guardias_dia:
            cursor.execute("""
                SELECT p.dni, p.nombre, p.apellidos
                FROM Profesores p
                WHERE EXISTS (
                    SELECT 1 FROM Horarios h
                    JOIN Asignaturas a ON h.id_asignatura_horarios = a.id_asignatura
                    WHERE h.dni_profesor_horarios = p.dni
                      AND h.id_dia_horarios = %s
                      AND h.id_tramo_horarios = %s
                      AND a.nombre LIKE 'Guardia%%'
                )
                AND NOT EXISTS (
                    SELECT 1 FROM Horarios h
                    JOIN Asignaturas a ON h.id_asignatura_horarios = a.id_asignatura
                    WHERE h.dni_profesor_horarios = p.dni
                      AND h.id_dia_horarios = %s
                      AND h.id_tramo_horarios = %s
                      AND a.nombre NOT LIKE 'Guardia%%'
                )
                AND NOT EXISTS (
                    SELECT 1 FROM Ausencias aus
                    WHERE aus.dni_profesor_ausencias = p.dni
                      AND aus.fecha = %s
                )
            """, (dia_semana, guardia['id_tramo'], dia_semana, guardia['id_tramo'], fecha_actual))
            profesores_disponibles[guardia['id_tramo']] = cursor.fetchall()

        # Procesar asignaciones
        if request.method == 'POST':
            for clave, valores in request.form.lists():
                if clave.startswith("tramo_"):
                    tramo_id = int(clave.split("_")[1])
                    for dni_profesor in valores:
                        cursor.execute("""
                            INSERT IGNORE INTO Guardias (dni_profesor_guardias, id_dia_guardias, id_tramo_guardias)
                            VALUES (%s, %s, %s)
                        """, (dni_profesor, dia_semana, tramo_id))
                        cursor.execute("""
                            UPDATE Profesores SET puntos_guardia = puntos_guardia + 1 WHERE dni = %s
                        """, (dni_profesor,))
            connection.commit()
            mensaje = "Guardias asignadas correctamente."

    connection.close()
    return render_template('gestionar_guardias.html',
                           guardias_dia=guardias_dia,
                           profesores_disponibles=profesores_disponibles,
                           mensaje=mensaje)


@app.route('/guardias/asignadas')
def guardias_asignadas():
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    connection = get_db_connection()
    hoy = date.today()

    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("""
            SELECT 
                th.horario,
                IFNULL(a.nombre, 'No especificada') AS aula_nombre,
                t.texto AS tarea,
                t.archivo
            FROM Guardias g
            JOIN Tramos_Horarios th ON g.id_tramo_guardias = th.id_tramo
            LEFT JOIN Aulas a ON g.id_aula_guardias = a.id_aula
            LEFT JOIN Ausencias au ON au.fecha = %s 
                                AND au.id_tramo_ausencias = g.id_tramo_guardias
            LEFT JOIN Tareas t ON t.id_ausencia_tareas = au.id_ausencia
            WHERE g.dni_profesor_guardias = %s
            AND g.id_dia_guardias = WEEKDAY(%s) + 1
            ORDER BY th.id_tramo
        """, (hoy, session['usuario_dni'], hoy))
        guardias = cursor.fetchall()

    connection.close()
    return render_template('guardias_asignadas.html', guardias=guardias)

# Reportacion de Incidencias
@app.route('/incidencias/reportar', methods=['GET', 'POST']) 
def reportar_incidencia():
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    mensaje = ""
    guardias_profesor = []

    connection = get_db_connection()
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        # Obtener las guardias asignadas al profesor
        cursor.execute("""
            SELECT g.id_guardia, d.nombre AS dia, t.horario, a.nombre AS aula
            FROM Guardias g
            JOIN Dias_Semana d ON g.id_dia_guardias = d.id_dia
            JOIN Tramos_Horarios t ON g.id_tramo_guardias = t.id_tramo
            LEFT JOIN Aulas a ON g.id_aula_guardias = a.id_aula
            WHERE g.dni_profesor_guardias = %s
        """, (session['usuario_dni'],))
        guardias_profesor = cursor.fetchall()

    if request.method == 'POST':
        id_guardia = request.form['id_guardia']
        texto = request.form['texto']

        if not all([id_guardia, texto]):
            mensaje = "Todos los campos son obligatorios."
        else:
            with connection.cursor() as cursor:
                try:
                    cursor.execute("""
                        INSERT INTO Incidencias (id_guardia_incidencias, texto)
                        VALUES (%s, %s)
                    """, (id_guardia, texto))
                    connection.commit()
                    mensaje = "Incidencia reportada correctamente."
                except Exception as e:
                    mensaje = f"Error al registrar la incidencia: {str(e)}"

    connection.close()
    return render_template('reportar_incidencia.html', mensaje=mensaje, guardias=guardias_profesor)

@app.route('/incidencias/reportadas', methods=['GET'])
def incidencias_reportadas():
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')

    query = """
        SELECT 
            p.nombre AS profesor,
            g.id_dia_guardias,
            d.nombre AS dia,
            g.id_tramo_guardias,
            th.horario,
            IFNULL(a.nombre, 'No especificada') AS aula,
            i.texto,
            i.timestamp AS fecha
        FROM Incidencias i
        JOIN Guardias g ON i.id_guardia_incidencias = g.id_guardia
        JOIN Profesores p ON g.dni_profesor_guardias = p.dni
        JOIN Dias_Semana d ON g.id_dia_guardias = d.id_dia
        JOIN Tramos_Horarios th ON g.id_tramo_guardias = th.id_tramo
        LEFT JOIN Aulas a ON g.id_aula_guardias = a.id_aula
        WHERE 1=1
    """

    filtros = []
    params = []

    if fecha_inicio:
        query += " AND DATE(i.timestamp) >= %s"
        params.append(fecha_inicio)
    if fecha_fin:
        query += " AND DATE(i.timestamp) <= %s"
        params.append(fecha_fin)

    query += " ORDER BY i.timestamp DESC"

    connection = get_db_connection()
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute(query, tuple(params))
        incidencias = cursor.fetchall()
    connection.close()

    return render_template('incidencias_reportadas.html', incidencias=incidencias)


@app.route('/tareas/registrar', methods=['GET', 'POST'])
def registrar_tarea():
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    mensaje = ""
    connection = get_db_connection()

    if request.method == 'POST':
        id_ausencia = request.form['id_ausencia']
        texto = request.form['texto']
        archivo = request.files.get('archivo')

        archivo_nombre = None
        if archivo and archivo.filename:
            filename = secure_filename(archivo.filename)
            carpeta_destino = os.path.join(current_app.root_path, "static", "tareas")
            os.makedirs(carpeta_destino, exist_ok=True)
            ruta_archivo = os.path.join(carpeta_destino, filename)
            archivo.save(ruta_archivo)
            archivo_nombre = filename

        if not all([id_ausencia, texto]):
            mensaje = "Todos los campos obligatorios deben estar completos."
        else:
            with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                # Obtener el grupo del horario correspondiente a la ausencia
                cursor.execute("""
                    SELECT h.id_grupo_horarios
                    FROM Horarios h
                    JOIN Ausencias a ON h.dni_profesor_horarios = a.dni_profesor_ausencias
                                     AND h.id_tramo_horarios = a.id_tramo_ausencias
                    WHERE a.id_ausencia = %s
                    LIMIT 1
                """, (id_ausencia,))
                resultado = cursor.fetchone()

                if resultado and resultado['id_grupo_horarios']:
                    id_grupo = resultado['id_grupo_horarios']

                    try:
                        cursor.execute("""
                            INSERT INTO Tareas (id_ausencia_tareas, id_grupo_tareas, texto, archivo)
                            VALUES (%s, %s, %s, %s)
                        """, (id_ausencia, id_grupo, texto, archivo_nombre))
                        connection.commit()
                        mensaje = "Tarea registrada correctamente."
                    except pymysql.err.IntegrityError:
                        mensaje = "Ya existe una tarea para esa ausencia y grupo."
                else:
                    mensaje = "No se pudo asociar la ausencia a un grupo. Verifica que el profesor tenga horario asignado ese día."

    # Cargar ausencias futuras
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("""
            SELECT a.id_ausencia, a.fecha, t.horario
            FROM Ausencias a
            JOIN Tramos_Horarios t ON a.id_tramo_ausencias = t.id_tramo
            WHERE a.dni_profesor_ausencias = %s AND a.fecha >= CURDATE()
            ORDER BY a.fecha, t.id_tramo
        """, (session['usuario_dni'],))
        ausencias = cursor.fetchall()

    connection.close()
    return render_template('registrar_tarea.html', mensaje=mensaje, ausencias=ausencias)

# Gestión de Ausencias #

@app.route('/ausencias/comunicar', methods=['GET', 'POST'])
def comunicar_ausencia():
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    mensaje = ""
    connection = get_db_connection()

    if request.method == 'POST':
        dni = session['usuario_dni']
        fecha = request.form['fecha']
        tramos = request.form.getlist('tramo')
        motivo = request.form['motivo']

        if not fecha or not tramos:
            mensaje = "Todos los campos son obligatorios."
        else:
            try:
                fecha_dt = datetime.strptime(fecha, '%Y-%m-%d').date()
                if fecha_dt < date.today():
                    mensaje = "No puedes registrar una ausencia en una fecha pasada."
                else:
                    with connection.cursor() as cursor:
                        errores = []
                        for tramo in tramos:
                            try:
                                cursor.execute("""
                                    INSERT INTO Ausencias (dni_profesor_ausencias, fecha, id_tramo_ausencias, motivo)
                                    VALUES (%s, %s, %s, %s)
                                """, (dni, fecha, tramo, motivo))
                            except pymysql.err.IntegrityError:
                                errores.append(f"Ya existe una ausencia para el tramo {tramo} en esa fecha.")
                        connection.commit()
                    if errores:
                        mensaje = "Algunas ausencias no se registraron: " + "; ".join(errores)
                    else:
                        mensaje = "Ausencia(s) comunicada(s) correctamente."
            except ValueError:
                mensaje = "La fecha introducida no es válida."

    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT id_tramo, horario FROM Tramos_Horarios")
        tramos = cursor.fetchall()
    connection.close()

    return render_template('comunicar_ausencia.html', tramos=tramos, mensaje=mensaje)

@app.route('/ausencias/reincorporacion', methods=['GET', 'POST'])
def comunicar_reincorporacion():
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    mensaje = ""
    connection = get_db_connection()
    hoy = date.today()

    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("""
            SELECT a.id_ausencia, t.horario, a.fecha, p.nombre, p.apellidos
            FROM Ausencias a
            JOIN Tramos_Horarios t ON a.id_tramo_ausencias = t.id_tramo
            JOIN Profesores p ON a.dni_profesor_ausencias = p.dni
            WHERE a.fecha = %s
              AND a.reincorporado_profesor = FALSE
        """, (hoy,))
        ausencias = cursor.fetchall()

        if request.method == 'POST':
            ids_reincorporados = request.form.getlist('reincorporados')
            for id_aus in ids_reincorporados:
                cursor.execute("""
                    UPDATE Ausencias
                    SET reincorporado_profesor = TRUE
                    WHERE id_ausencia = %s
                """, (id_aus,))
            connection.commit()
            mensaje = "Reincorporación enviada para validación de dirección."

    connection.close()
    return render_template('comunicar_reincorporacion.html', ausencias=ausencias, mensaje=mensaje)

@app.route('/ausencias/validar_reincorporacion', methods=['GET', 'POST'])
def validar_reincorporacion():
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    connection = get_db_connection()

    with connection.cursor() as cursor:
        cursor.execute("SELECT id_perfil_profesores FROM Profesores WHERE dni = %s", (session['usuario_dni'],))
        perfil = cursor.fetchone()

        if perfil['id_perfil_profesores'] != 2:  # Solo dirección
            connection.close()
            return redirect(url_for('home'))

    mensaje = ""
    hoy = date.today()

    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("""
            SELECT a.id_ausencia, p.nombre, p.apellidos, t.horario, a.fecha
            FROM Ausencias a
            JOIN Profesores p ON a.dni_profesor_ausencias = p.dni
            JOIN Tramos_Horarios t ON a.id_tramo_ausencias = t.id_tramo
            WHERE a.fecha = %s
              AND a.reincorporado_profesor = TRUE
              AND a.validacion_direccion = FALSE
        """, (hoy,))
        ausencias = cursor.fetchall()

        if request.method == 'POST':
            ids_validadas = request.form.getlist('validadas')
            for id_aus in ids_validadas:
                cursor.execute("""
                    UPDATE Ausencias
                    SET validacion_direccion = TRUE
                    WHERE id_ausencia = %s
                """, (id_aus,))
            connection.commit()
            mensaje = "Reincorporaciones validadas correctamente."

    connection.close()
    return render_template('validar_reincorporacion.html', ausencias=ausencias, mensaje=mensaje)

# CHAT #

@app.route('/chat')
def chat():
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))
    mensajes = list(coleccion_mensajes.find({"archivado": False}).sort("timestamp", -1))
    return render_template('chat.html', mensajes=mensajes)

@app.route('/chat/mensajes')
def obtener_mensajes():
    mensajes = list(coleccion_mensajes.find({"archivado": False}).sort("timestamp", -1))
    for m in mensajes:
        m["_id"] = str(m["_id"])
        m["timestamp"] = m["timestamp"].strftime("%d/%m/%Y %H:%M")
    return jsonify(mensajes)

@app.route('/chat/enviar', methods=['POST'])
def enviar_mensaje():
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    mensaje = request.form['mensaje']
    if mensaje.strip():
        coleccion_mensajes.insert_one({
            "autor": session['usuario_dni'],
            "nombre": session['username'],
            "mensaje": mensaje.strip(),
            "timestamp": datetime.utcnow(),
            "archivado": False
        })
    return redirect(url_for('chat'))

@app.route('/chat/archivar/<id>')
def archivar_mensaje(id):
    if session.get('usuario_dni') != '00000000A':  # Control de admin
        return redirect(url_for('chat'))
    from bson.objectid import ObjectId
    coleccion_mensajes.update_one({'_id': ObjectId(id)}, {'$set': {'archivado': True}})
    return redirect(url_for('chat'))

@app.route('/chat/eliminar/<id>')
def eliminar_mensaje(id):
    if session.get('usuario_dni') != '00000000A':  # Control de admin
        return redirect(url_for('chat'))
    from bson.objectid import ObjectId
    coleccion_mensajes.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('chat'))

# Actividades Extraescolares #

@app.route('/actividades/registrar', methods=['GET', 'POST'])
def registrar_actividad_extraescolar():
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    connection = get_db_connection()
    mensaje = ""

    if request.method == 'POST':
        grupo = request.form['grupo']
        fecha = request.form['fecha']
        tramos = request.form.getlist('tramos')
        afecta_completo = 'afecta_completo' in request.form
        profesores = request.form.getlist('profesores')

        with connection.cursor() as cursor:
            for tramo in tramos:
                cursor.execute("""
                    INSERT INTO Actividades_Extraescolares (
                        id_grupo_actividades_extraescolares, fecha, id_tramo_actividades_extraescolares,
                        dni_profesor_actividades_extraescolares, afecta_grupo_completo
                    ) VALUES (%s, %s, %s, %s, %s)
                """, (grupo, fecha, tramo, session['usuario_dni'], afecta_completo))

                for dni in profesores:
                    cursor.execute("""
                        INSERT INTO Ausencias (dni_profesor_ausencias, fecha, id_tramo_ausencias, motivo)
                        VALUES (%s, %s, %s, %s)
                    """, (dni, fecha, tramo, "Acompaña actividad extraescolar"))

        connection.commit()
        mensaje = "Actividad registrada correctamente."

    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT id_grupo, nombre FROM Grupos")
        grupos = cursor.fetchall()
        cursor.execute("SELECT id_tramo, horario FROM Tramos_Horarios")
        tramos = cursor.fetchall()
        cursor.execute("SELECT dni, nombre, apellidos FROM Profesores")
        profesores = cursor.fetchall()

    connection.close()
    return render_template('registrar_actividad_extraescolar.html', grupos=grupos, tramos=tramos,
                           profesores=profesores, mensaje=mensaje)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)