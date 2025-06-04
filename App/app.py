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
                with connection.cursor() as cursor:
                    try:
                        reader = csv.DictReader(TextIOWrapper(archivo, encoding='utf-8'))
                        insertados = 0
                        for row in reader:
                            cursor.execute("SELECT COUNT(*) FROM Profesores WHERE dni = %s OR email = %s", (row['dni'], row['email']))
                            if cursor.fetchone()[0] == 0:
                                cursor.execute("""
                                    INSERT INTO Profesores (dni, nombre, apellidos, email, password, puntos_guardia, id_perfil_profesores)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                                """, (row['dni'], row['nombre'], row['apellidos'], row['email'], row['password'], row.get('puntos_guardia', 0), row['id_perfil_profesores']))
                                insertados += 1
                        connection.commit()
                        mensaje = f"Se han insertado {insertados} profesores nuevos."
                    except Exception as e:
                        mensaje = f"Error al procesar el archivo: {str(e)}"
                connection.close()
            else:
                mensaje = "El archivo debe ser CSV."

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
                with connection.cursor() as cursor:
                    try:
                        reader = csv.DictReader(TextIOWrapper(archivo, encoding='utf-8'))
                        insertados = 0
                        for row in reader:
                            cursor.execute("""
                                SELECT COUNT(*) FROM Horarios
                                WHERE dni_profesor_horarios = %s AND id_dia_horarios = %s AND id_tramo_horarios = %s
                            """, (row['dni_profesor'], row['id_dia'], row['id_tramo']))
                            if cursor.fetchone()[0] == 0:
                                cursor.execute("""
                                    INSERT INTO Horarios (dni_profesor_horarios, id_dia_horarios, id_tramo_horarios, id_grupo_horarios, id_asignatura_horarios, id_aula)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                """, (row['dni_profesor'], row['id_dia'], row['id_tramo'], row.get('id_grupo'), row['id_asignatura'], row.get('id_aula')))
                                insertados += 1
                        connection.commit()
                        mensaje = f"Se han insertado {insertados} registros de horario nuevos."
                    except Exception as e:
                        mensaje = f"Error al procesar el archivo: {str(e)}"
                connection.close()
            else:
                mensaje = "El archivo debe ser CSV."

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

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)