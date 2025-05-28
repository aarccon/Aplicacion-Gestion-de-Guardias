import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
from config import get_db_connection, SECRET_KEY

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
        id_perfil = request.form['id_perfil_profesores']
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

@app.route('/horario')
def ver_horario():
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT ds.nombre AS dia, th.horario, g.nombre AS grupo, a.nombre AS asignatura, h.aula
            FROM Horarios h
            JOIN Dias_Semana ds ON h.id_dia_horarios = ds.id_dia
            JOIN Tramos_Horarios th ON h.id_tramo_horarios = th.id_tramo
            LEFT JOIN Grupos g ON h.id_grupo_horarios = g.id_grupo
            JOIN Asignaturas a ON h.id_asignatura_horarios = a.id_asignatura
            WHERE h.dni_profesor_horarios = %s
            ORDER BY ds.id_dia, th.id_tramo
        """, (session['usuario_dni'],))
        horario = cursor.fetchall()
    connection.close()
    return render_template('ver_horario.html', horario=horario)

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
    if request.method == 'POST':
        dni = request.form['dni']
        dia = request.form['dia']
        tramo = request.form['tramo']
        aula = request.form['aula']

        if not all([dni, dia, tramo, aula]):
            mensaje = "Todos los campos son obligatorios."
        else:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                try:
                    cursor.execute("""
                        INSERT INTO Guardias (dni_profesor_guardias, id_dia_guardias, id_tramo_guardias, aula_zona)
                        VALUES (%s, %s, %s, %s)
                    """, (dni, dia, tramo, aula))
                    connection.commit()
                    mensaje = "Guardia asignada correctamente."
                except pymysql.err.IntegrityError:
                    mensaje = "Ya existe una guardia registrada con esos datos."
            connection.close()

    return render_template('asignar_guardia.html', mensaje=mensaje)

@app.route('/tareas/registrar', methods=['GET', 'POST'])
def registrar_tarea():
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    mensaje = ""
    if request.method == 'POST':
        id_ausencia = request.form['id_ausencia']
        id_grupo = request.form['id_grupo']
        texto = request.form['texto']

        if not all([id_ausencia, id_grupo, texto]):
            mensaje = "Todos los campos son obligatorios."
        else:
            connection = get_db_connection()
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
            connection.close()

    return render_template('registrar_tarea.html', mensaje=mensaje)

@app.route('/ausencias/comunicar', methods=['GET', 'POST'])
def comunicar_ausencia():
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    mensaje = ""
    if request.method == 'POST':
        dni = session['usuario_dni']
        fecha = request.form['fecha']
        tramo = request.form['tramo']
        grupo = request.form['grupo']
        aula = request.form['aula']
        motivo = request.form['motivo']

        if not all([fecha, tramo, grupo, aula]):
            mensaje = "Todos los campos son obligatorios."
        else:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                try:
                    cursor.execute("""
                        INSERT INTO Ausencias (dni_profesor_ausencias, fecha, id_tramo_ausencias, id_grupo_ausencias, aula_zona, motivo)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (dni, fecha, tramo, grupo, aula, motivo))
                    connection.commit()
                    mensaje = "Ausencia comunicada correctamente."
                except pymysql.err.IntegrityError:
                    mensaje = "Ya existe una ausencia registrada con esos datos."
            connection.close()

    return render_template('comunicar_ausencia.html', mensaje=mensaje)

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

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

print("Rutas registradas:")
print(app.url_map)

if __name__ == '__main__':
    app.run(debug=True)
