import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
import pymysql
import os
from werkzeug.security import generate_password_hash, check_password_hash
from config import get_db_connection, SECRET_KEY
from pymongo import MongoClient
from config import MONGO_URI, MONGO_DB, MONGO_COLECCION
from flask import jsonify
from datetime import datetime, date
import csv
from io import TextIOWrapper

mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client[MONGO_DB]
coleccion_mensajes = mongo_db[MONGO_COLECCION]
db=mongo_client

app = Flask(__name__)
app.secret_key = SECRET_KEY

@app.route('/')
def root():
    if 'usuario_dni' in session:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/home')
def home():
    if 'usuario_dni' in session:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT id_perfil_profesores FROM Profesores WHERE dni = %s", (session['usuario_dni'],))
            perfil = cursor.fetchone()
        connection.close()

        if perfil and perfil['id_perfil_profesores'] == 1:
            return render_template('home_profesor.html', username=session.get('username'))
        else:
            return render_template('home.html', username=session.get('username'))
    return redirect(url_for('login'))

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
                                cursor.execute("""
                                    INSERT INTO Profesores (dni, nombre, apellidos, email, password, puntos_guardia, id_perfil_profesores)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                                """, (
                                    row['dni'],
                                    row['nombre'],
                                    row['apellidos'],
                                    row['email'],
                                    row['password'],
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

@app.route('/horario')
def ver_horario():
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM Dias_Semana ORDER BY id_dia")
        dias = cursor.fetchall()

        cursor.execute("SELECT * FROM Tramos_Horarios ORDER BY id_tramo")
        tramos = cursor.fetchall()

        cursor.execute("""
            SELECT
                h.id_dia_horarios,
                h.id_tramo_horarios,
                a.nombre AS asignatura,
                g.nombre AS grupo,
                au.nombre AS aula
            FROM Horarios h
            JOIN Asignaturas a ON h.id_asignatura_horarios = a.id_asignatura
            LEFT JOIN Grupos g ON h.id_grupo_horarios = g.id_grupo
            LEFT JOIN Aulas au ON h.id_aula = au.id_aula
            WHERE h.dni_profesor_horarios = %s
        """, (session['usuario_dni'],))
        datos = cursor.fetchall()

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
    
# Sigue sin comentar
@app.route('/guardias/asignadas')
def guardias_asignadas():
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT ds.nombre AS dia, th.horario, g.aula_zona
            FROM Guardias g
            JOIN Dias_Semana ds ON g.id_dia_guardias = ds.id_dia
            JOIN Tramos_Horarios th ON g.id_tramo_guardias = th.id_tramo
            WHERE g.dni_profesor_guardias = %s
            ORDER BY ds.id_dia, th.id_tramo
        """, (session['usuario_dni'],))
        guardias = cursor.fetchall()
    connection.close()
    return render_template('guardias_asignadas.html', guardias=guardias)

@app.route('/guardias/asignar', methods=['GET', 'POST'])
def asignar_guardia():
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    mensaje = ""
    connection = get_db_connection()

    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        # Obtener días, tramos y profesores
        cursor.execute("SELECT id_dia, nombre FROM Dias_Semana")
        dias = cursor.fetchall()

        cursor.execute("SELECT id_tramo, horario FROM Tramos_Horarios")
        tramos = cursor.fetchall()

        cursor.execute("SELECT dni, CONCAT(nombre, ' ', apellidos) AS nombre_completo FROM Profesores")
        profesores = cursor.fetchall()

        if request.method == 'POST':
            profesor_dni = request.form['profesor_dni']
            dia = request.form['dia']
            tramo = request.form['tramo']
            aula = request.form['aula']

            # Validar que hay una ausencia registrada hoy para ese tramo
            cursor.execute("""
                SELECT COUNT(*) AS existe
                FROM Ausencias
                WHERE fecha = CURDATE() AND id_tramo_ausencias = %s
            """, (tramo,))
            hay_ausencia = cursor.fetchone()['existe'] > 0

            if not hay_ausencia:
                mensaje = "No hay ninguna ausencia registrada para ese tramo hoy."
            else:
                # Verificar si el profesor tiene la asignatura 'Guardia'
                cursor.execute("""
                    SELECT COUNT(*) AS tiene_guardia
                    FROM Horarios h
                    JOIN Asignaturas a ON h.id_asignatura_horarios = a.id_asignatura
                    WHERE h.dni_profesor_horarios = %s AND a.nombre LIKE 'Guardia%%'
                """, (profesor_dni,))
                tiene_guardia = cursor.fetchone()['tiene_guardia'] > 0

                if not tiene_guardia:
                    mensaje = "El profesor no tiene asignada la asignatura de Guardia y no puede cubrir guardias."
                else:
                    # Verificar si el profesor tiene clase en ese día y tramo
                    cursor.execute("""
                        SELECT COUNT(*) AS total
                        FROM Horarios
                        WHERE dni_profesor_horarios = %s AND id_dia_horarios = %s AND id_tramo_horarios = %s
                    """, (profesor_dni, dia, tramo))
                    ocupado = cursor.fetchone()['total'] > 0

                    if ocupado:
                        mensaje = "El profesor tiene clase en ese horario y no se puede asignar guardia."
                    else:
                        try:
                            cursor.execute("""
                                INSERT INTO Guardias (dni_profesor_guardias, id_dia_guardias, id_tramo_guardias, aula_zona)
                                VALUES (%s, %s, %s, %s)
                            """, (profesor_dni, dia, tramo, aula))

                            cursor.execute("""
                                UPDATE Profesores
                                SET puntos_guardia = puntos_guardia + 1
                                WHERE dni = %s
                            """, (profesor_dni,))

                            connection.commit()
                            mensaje = "Guardia asignada correctamente."
                        except pymysql.err.IntegrityError:
                            mensaje = "Ya existe una guardia registrada para ese profesor en ese tramo."

    connection.close()
    return render_template('asignar_guardia.html', dias=dias, tramos=tramos, profesores=profesores, mensaje=mensaje)


@app.route('/incidencias/reportar', methods=['GET', 'POST'])
def reportar_incidencia():
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    mensaje = ""
    if request.method == 'POST':
        id_guardia = request.form['id_guardia']
        texto = request.form['texto']

        if not all([id_guardia, texto]):
            mensaje = "Todos los campos son obligatorios."
        else:
            connection = get_db_connection()
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

    return render_template('reportar_incidencia.html', mensaje=mensaje)

@app.route('/tareas/registrar', methods=['GET', 'POST'])
def registrar_tarea():
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    mensaje = ""
    connection = get_db_connection()

    if request.method == 'POST':
        id_ausencia = request.form['id_ausencia']
        id_grupo = request.form['id_grupo']
        texto = request.form['texto']

        if not all([id_ausencia, id_grupo, texto]):
            mensaje = "Todos los campos son obligatorios."
        else:
            with connection.cursor() as cursor:
                try:
                    cursor.execute("""
                        INSERT INTO Tareas (id_ausencia_tareas, id_grupo_tareas, texto)
                        VALUES (%s, %s, %s)
                    """, (id_ausencia, id_grupo, texto))
                    connection.commit()
                    mensaje = "Tarea registrada correctamente."
                except pymysql.err.IntegrityError:
                    mensaje = "Ya existe una tarea para esa ausencia y grupo."

    # Cargar ausencias del profesor logueado para mostrarlas en el desplegable
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("""
            SELECT a.id_ausencia, a.fecha, t.horario
            FROM Ausencias a
            JOIN Tramos_Horarios t ON a.id_tramo_ausencias = t.id_tramo
            WHERE a.dni_profesor_ausencias = %s
            ORDER BY a.fecha, t.id_tramo
        """, (session['usuario_dni'],))
        ausencias = cursor.fetchall()

    connection.close()
    return render_template('registrar_tarea.html', mensaje=mensaje, ausencias=ausencias)

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
    dni = session['usuario_dni']
    hoy = date.today()

    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("""
            SELECT a.id_ausencia, t.horario, a.fecha
            FROM Ausencias a
            JOIN Tramos_Horarios t ON a.id_tramo_ausencias = t.id_tramo
            WHERE a.dni_profesor_ausencias = %s AND a.fecha = %s
              AND a.reincorporado_profesor = FALSE
        """, (dni, hoy))
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
              AND a.validacción_direccion = FALSE
        """, (hoy,))
        ausencias = cursor.fetchall()

        if request.method == 'POST':
            ids_validadas = request.form.getlist('validadas')
            for id_aus in ids_validadas:
                cursor.execute("""
                    UPDATE Ausencias
                    SET validacción_direccion = TRUE
                    WHERE id_ausencia = %s
                """, (id_aus,))
            connection.commit()
            mensaje = "Reincorporaciones validadas correctamente."

    connection.close()
    return render_template('validar_reincorporacion.html', ausencias=ausencias, mensaje=mensaje)

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
            "timestamp": datetime.datetime.utcnow(),
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

@app.route('/guardias/hoy', methods=['GET', 'POST'])
def guardias_hoy():
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    mensaje = ""
    connection = get_db_connection()
    hoy = date.today()
    guardias = []
    incidencias = []

    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        # Obtener todas las guardias del día actual
        cursor.execute("""
            SELECT g.id_guardia, p.nombre, p.apellidos, th.horario, g.aula_zona
            FROM Guardias g
            JOIN Profesores p ON g.dni_profesor_guardias = p.dni
            JOIN Tramos_Horarios th ON g.id_tramo_guardias = th.id_tramo
            WHERE g.id_dia_guardias = WEEKDAY(%s) + 1
            ORDER BY th.id_tramo
        """, (hoy,))
        guardias = cursor.fetchall()

        # Registrar nueva incidencia
        if request.method == 'POST':
            id_guardia = request.form['id_guardia']
            texto = request.form['texto']
            if texto.strip():
                cursor.execute("""
                    INSERT INTO Incidencias (id_guardia_incidencias, texto)
                    VALUES (%s, %s)
                """, (id_guardia, texto.strip()))
                connection.commit()
                mensaje = "Incidencia registrada correctamente."

        # Obtener todas las incidencias del día
        cursor.execute("""
            SELECT i.texto, i.timestamp, p.nombre, p.apellidos
            FROM Incidencias i
            JOIN Guardias g ON i.id_guardia_incidencias = g.id_guardia
            JOIN Profesores p ON g.dni_profesor_guardias = p.dni
            WHERE DATE(i.timestamp) = %s
            ORDER BY i.timestamp DESC
        """, (hoy,))
        incidencias = cursor.fetchall()

    connection.close()
    return render_template('guardias_hoy.html', guardias=guardias, incidencias=incidencias, mensaje=mensaje)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)