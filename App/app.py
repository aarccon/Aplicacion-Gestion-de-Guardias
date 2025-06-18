import datetime
import csv
import pymysql
import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from config import get_db_connection, SECRET_KEY
from pymongo import MongoClient
from config import MONGO_URI, MONGO_DB, MONGO_COLECCION
from datetime import datetime, date
from io import TextIOWrapper
from flask import current_app
from bson.objectid import ObjectId

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

# HORARIOS #

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
            SELECT Horarios.id_dia_horarios, Horarios.id_tramo_horarios, Asignaturas.nombre AS asignatura, Grupos.nombre AS grupo, Aulas.nombre AS aula
            FROM Horarios
            JOIN Asignaturas ON Horarios.id_asignatura_horarios = Asignaturas.id_asignatura
            LEFT JOIN Grupos ON Horarios.id_grupo_horarios = Grupos.id_grupo
            LEFT JOIN Aulas ON Horarios.id_aula = Aulas.id_aula
            WHERE Horarios.dni_profesor_horarios = %s
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

# Función que nos permite ver el horario de cualquier profesor que hay en el instituto
@app.route('/horario/otros', methods=['GET', 'POST'])
def ver_horario_profesores():

    # En caso de que no haya una sesión iniciada, lo redirige al login para que el usuario se logue
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    # Se realiza una conexión a la base de datos
    connection = get_db_connection()

    # Se inicializan las variables: horario que es una lista vacia en la cual almacenara los horarios de los profesores y profesor_seleccionado: almacena el profesor que indiquemos en el formulario 
    horario = []
    profesor_seleccionado = None

    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        # Realizamos la primera consulta la cual obtendrá el dni, los nombres y apellidos de todoso los profesores que hay en la base de datos y esto lo almacenanos en la variable profesores.
        cursor.execute("SELECT dni, CONCAT(nombre, ' ', apellidos) AS nombre_completo FROM Profesores  ORDER BY apellidos ASC")
        profesores = cursor.fetchall()

        # En el caso que solicitemos datos guardamos en la variable profesor_seleccionado el dni del profesor que hemos seleccionado en el formulario.
        if request.method == 'POST':
            profesor_seleccionado = request.form['dni_profesor']
            # Realizamos la segunda consulta la cual obtendrá el horario completo de ese profesor
            cursor.execute("""
                SELECT Dias_Semana.nombre AS dia, Tramos_Horarios.horario, Grupos.nombre AS grupo, Asignaturas.nombre AS asignatura, Aulas.nombre AS aula
                FROM Horarios
                JOIN Dias_Semana ON Horarios.id_dia_horarios = Dias_Semana.id_dia
                JOIN Tramos_Horarios ON Horarios.id_tramo_horarios = Tramos_Horarios.id_tramo
                LEFT JOIN Grupos ON Horarios.id_grupo_horarios = Grupos.id_grupo
                JOIN Asignaturas ON Horarios.id_asignatura_horarios = Asignaturas.id_asignatura
                LEFT JOIN Aulas ON Horarios.id_aula = Aulas.id_aula
                WHERE Horarios.dni_profesor_horarios = %s
                ORDER BY Dias_Semana.id_dia, Tramos_Horarios.id_tramo
            """, (profesor_seleccionado,))
            horario = cursor.fetchall()

    # Cerramos la conexión de la base de datos
    connection.close()
    return render_template("ver_horario_profesores.html", profesores=profesores, horario=horario, profesor_dni=profesor_seleccionado)

#INSERCCIÓN DE DATOS #

# Función que permite insertar un usuario en la aplicación.
@app.route('/profesores/registrar', methods=['GET', 'POST'])
def registrar_profesor():
    # En caso de que no haya una sesión iniciada, lo redirige al login para que el usuario se logue
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    # La variable mensaje guardará el mensaje de exito o error que se va a mostrar en la pantalla
    mensaje = ""
    if request.method == 'POST':
        # Obtenemos los datos del formulario cuando se va a realizar el registro
        dni = request.form['dni']
        nombre = request.form['nombre']
        apellidos = request.form['apellidos']
        email = request.form['email']
        password = request.form['password']
        id_perfil = int(request.form['perfil'])

        # Se realiza la encriptación de la contraseña usando hash seguro.
        password_hash = generate_password_hash(password)

        # Se comprueba que todos los campos esten rellenados.
        if not all([dni, nombre, apellidos, email, password, id_perfil]):
            # En caso de que no esten todos los campos completos mostramos el siguiente mensaje
            mensaje = "Todos los campos son obligatorios."
        else:
            # Si están todos los campos realizamos una conexión a la base de datos.
            connection = get_db_connection()
            with connection.cursor() as cursor:
                try:
                    # Realizamos la insercción de los datos en la tabla Profesores
                    cursor.execute("""
                        INSERT INTO Profesores (dni, nombre, apellidos, email, password, id_perfil_profesores)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (dni, nombre, apellidos, email, password_hash, id_perfil))
                    # Confirmamos los cambios que hemos realizado en la base de datos
                    connection.commit()
                    # Cuando se haga la insercción correctamente mostrará este mensaje
                    mensaje = "Profesor registrado correctamente."
                except pymysql.err.IntegrityError:
                    # Cuando la insercción de fallo mostrará este mensaje
                    mensaje = "El profesor ya existe con ese DNI o correo."
            # Se cierra la conexión a la base de datos
            connection.close()

    return render_template('registrar_profesor.html', mensaje=mensaje)

# Subida de Archivos CSV

# Función en la que se permite subir un archivo csv para poder registrar muchos profesores a la vez.
@app.route('/subida_profesorado', methods=['GET', 'POST'])
def subir_profesores():

    # La variable mensaje guardará el mensaje de exito o error que se va a mostrar en la pantalla
    mensaje = ""
    if request.method == 'POST':
        # Comprobamos que hemos subido un archivo.
        if 'archivo' not in request.files:
            mensaje = "No se ha subido ningún archivo."
        else:
            archivo = request.files['archivo']
            # Comprobamos que el fichero tenga extensión .csv.
            if archivo.filename.endswith('.csv'):

                # Se realiza una conexión a la base de datos
                connection = get_db_connection()
                try:
                    archivo_stream = TextIOWrapper(archivo, encoding='utf-8')
                    reader = csv.DictReader(archivo_stream)
                    
                    insertados = 0 # Es un contador en el cual se irá incrementando conforme se vaya realizando las insercciones en la base de datos.
                    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                        for row in reader:

                            # Se usa un cursor para leer las filas de forma más clara.
                            cursor.execute(
                                # Comprobamos si hay un profesor con el mismo DNI o email que hay en esa línea.
                                "SELECT COUNT(*) AS cuenta FROM Profesores WHERE dni = %s OR email = %s",
                                (row['dni'], row['email'])
                            )
                            resultado = cursor.fetchone()
                            if resultado['cuenta'] == 0:
                                # Se realiza la encriptación del nuevo profesor.
                                password_encriptada = generate_password_hash(row['password'])
                                # Insertamos al nuevo profesor en la base de datos
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
                                insertados += 1 # Incrementamos el valor del contador.

                    # Guardamos los cambios en la base de datos.    
                    connection.commit()

                    # Devolvemos un mensaje indicando los profesores que se han insertado
                    mensaje = f"Se han insertado {insertados} profesores nuevos."
                except Exception as ex:
                    # Si hay algún tipo de error, mostramos el mensaje de error.
                    mensaje = f"Error al procesar el archivo: {str(ex)}"
                finally:
                    # Cerramos la conexión con la base de datos.
                    connection.close()
            else:
                # En caso de que el archivo no sea csv indicamos un mensaje diciendo que el archivo debe ser csv
                mensaje = "El archivo debe ser .csv"

    return render_template('subir_profesores.html', mensaje=mensaje)

# Función en la que se permite subir un archivo csv para poder registrar todos los horarios de los profesores a la vez.
@app.route('/subida_horarios', methods=['GET', 'POST'])
def subir_horarios():

    # La variable mensaje guardará el mensaje de exito o error que se va a mostrar en la pantalla
    mensaje = ""
    if request.method == 'POST':
        # Comprobamos que se ha subido un archivo correctamente
        if 'archivo' not in request.files:
            mensaje = "No se ha subido ningún archivo."
        else:
            archivo = request.files['archivo']

            # Comprobamos que el archivo tenga una extensión .csv
            if archivo.filename.endswith('.csv'):

                # Se realiza una conexión a la base de datos
                connection = get_db_connection()
                try:
                    archivo_stream = TextIOWrapper(archivo, encoding='utf-8')
                    reader = csv.DictReader(archivo_stream)

                    # Comprobamos que el archivo que hemos subido contiene cabeceras validas.
                    if not reader.fieldnames:
                        mensaje = "El archivo CSV no contiene cabeceras válidas."
                        return render_template('subir_horarios.html', mensaje=mensaje)
                    
                    # Indicamos las columnas que vamos a esperar del fichero csv
                    columnas_esperadas = ['dni_profesor_horarios', 'id_dia_horarios', 'id_tramo_horarios', 'id_grupo_horarios', 'id_asignatura_horarios', 'id_aula']
                    print("Cabeceras detectadas:", reader.fieldnames)

                    # Comprobamos que todas las columnas que se van a esperar en el fichero csv se encuentran presente
                    for col in columnas_esperadas:
                        if col not in reader.fieldnames:
                            mensaje = f"Falta la columna '{col}' en el archivo CSV."
                            return render_template('subir_horarios.html', mensaje=mensaje)

                    insertados = 0 # Es un contador en el cual se irá incrementando conforme se vaya realizando las insercciones en la base de datos.

                    # Recorremos cada fila del archivo csv que contiene los horarios
                    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                        for row in reader:
                            print("Fila leída:", row)

                            # Realizamos una comprobación de que no haya un registro con el mismo profesor, día y tramo horario
                            cursor.execute("""
                                SELECT COUNT(*) AS total FROM Horarios WHERE dni_profesor_horarios = %s AND id_dia_horarios = %s AND id_tramo_horarios = %s
                            """, (
                                row['dni_profesor_horarios'],
                                int(row['id_dia_horarios']),
                                int(row['id_tramo_horarios'])
                            ))
                            existe = cursor.fetchone()['total'] > 0

                            # En caso de que no exista se realiza la insercción en la base de datos del registro.
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
                                insertados += 1 # Cuando se realiza una insercción se aumenta el contador de los registros que hemos insertado.

                        # Guardamos los cambios en la base de datos
                        connection.commit()

                        # Mostramos un mensaje con los registros de horarios que se han insertado nuevos.
                        mensaje = f"Se han insertado {insertados} registros de horario nuevos."
                except Exception as e:
                    # En caso de que se produzca un error en el proceso de lectura e insercción mostrará el mensaje.
                    mensaje = f"Error al procesar el archivo: {str(e)}"
                finally:
                    # Cerramos la conexión con la base de datos
                    connection.close()
            else:
                # En caso de que el archivo no sea csv mostramos un mensaje indicando que el archivo no tiene el formato .csv
                mensaje = "El archivo debe ser .csv"

    return render_template('subir_horarios.html', mensaje=mensaje)

# Gestión de Puntuaciones #

@app.route('/puntuaciones', methods=['GET', 'POST'])
def gestionar_puntuaciones():

    # En caso de que no haya una sesión iniciada, lo redirige al login para que el usuario se logue
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    # Realizamos la conexión con la base de datos.
    connection = get_db_connection()
    # La variable mensaje guardará el mensaje de exito o error que se va a mostrar en la pantalla
    mensaje = "" 

    if request.method == 'POST':
        with connection.cursor() as cursor:
            # Si pulsamos el botón de Resablecer las puntuaciones, todas las puntuaciones se ponen a 0
            if 'resetear' in request.form:
                cursor.execute("UPDATE Profesores SET puntos_guardia = 0")
                mensaje = "Todas las puntuaciones se han restablecido."

            # Si pulsamos el botón de Subir, subimos la puntuación de ese profesor un punto
            elif 'subir' in request.form:
                dni = request.form['subir']
                cursor.execute("UPDATE Profesores SET puntos_guardia = puntos_guardia + 1 WHERE dni = %s", (dni,))
                # Consulta que obtiene el nombre y apellidos del profesor
                cursor.execute("SELECT nombre, apellidos FROM Profesores WHERE dni = %s", (dni,))
                profesor = cursor.fetchone()
                mensaje = f"Puntos aumentados para el profesor {profesor['nombre']} {profesor['apellidos']}."

            # Si pulsamos el botón de Bajar, bajamos la puntuación de ese profesor un punto
            elif 'bajar' in request.form:
                dni = request.form['bajar']
                cursor.execute("""
                    UPDATE Profesores SET puntos_guardia = CASE
                        WHEN puntos_guardia > 0 THEN puntos_guardia - 1
                        ELSE 0
                    END
                    WHERE dni = %s
                """, (dni,))
                # Consulta que obtiene el nombre y apellidos del profesor
                cursor.execute("SELECT nombre, apellidos FROM Profesores WHERE dni = %s", (dni,))
                profesor = cursor.fetchone()
                mensaje = f"Puntos reducidos para el profesor {profesor['nombre']} {profesor['apellidos']}."

            # Confirmamos los cambios en la base de datos
            connection.commit()

    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        # Consulta para mostrar la puntuación de los profesores ordenados por puntos.
        cursor.execute("""
            SELECT dni, nombre, apellidos, puntos_guardia FROM Profesores ORDER BY apellidos ASC, puntos_guardia DESC
        """)
        puntuaciones = cursor.fetchall()

    # Cerramos la conexión con la base de datos
    connection.close()
    return render_template('gestionar_puntuaciones.html', puntuaciones=puntuaciones, mensaje=mensaje)

# Gestionar Guardias #

# Función para llevar a cabo la gestión de la guardia de los profesores
@app.route('/guardias/gestionar', methods=['GET', 'POST'])
def gestionar_guardias():
    # En caso de que no haya una sesión iniciada, lo redirige al login para que el usuario se logue
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    # Establecemos la conexión con la base de datos
    connection = get_db_connection()
    # La variable mensaje guardará el mensaje de exito o error que se va a mostrar en la pantalla
    mensaje = ""
    
    # La variable fecha_actual almacenara la fecha y el día de la semana actual
    fecha_actual = date.today()
    dia_semana = fecha_actual.weekday() + 1

    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        # Primera consulta en el cual obtenemos todos los tramos horaris que contiene ausencias en el día de hoy
        cursor.execute("""
            SELECT Tramos_Horarios.id_tramo, Tramos_Horarios.horario, Aulas.nombre AS aula_nombre,
                (
                    SELECT GROUP_CONCAT(CONCAT(Profesores.nombre, ' ', Profesores.apellidos) SEPARATOR ', ') FROM Guardias
                    JOIN Profesores ON Guardias.dni_profesor_guardias = Profesores.dni
                    WHERE Guardias.id_dia_guardias = %s AND Guardias.id_tramo_guardias = Tramos_Horarios.id_tramo
                ) AS profesores_asignados
            FROM Tramos_Horarios
            JOIN Ausencias ON Ausencias.id_tramo_ausencias = Tramos_Horarios.id_tramo AND Ausencias.fecha = %s
            LEFT JOIN Aulas ON Aulas.id_aula = Ausencias.id_tramo_ausencias
            GROUP BY Tramos_Horarios.id_tramo, Tramos_Horarios.horario, Aulas.nombre ORDER BY Tramos_Horarios.id_tramo
        """, (dia_semana, fecha_actual))
        guardias_dia = cursor.fetchall()

        # Diccionario en el cual almacenamos los profesores que hay disponibles en los tramos.
        profesores_disponibles = {}
        for guardia in guardias_dia:
            # Segunda consulta en la que busca a los profesores que se encuentran en Guardia y no están ausentes.
            cursor.execute("""
                SELECT Profesores.dni, Profesores.nombre, Profesores.apellidos
                FROM Profesores
                WHERE EXISTS (
                    SELECT 1 FROM Horarios
                    JOIN Asignaturas ON Horarios.id_asignatura_horarios = Asignaturas.id_asignatura
                    WHERE Horarios.dni_profesor_horarios = Profesores.dni
                      AND Horarios.id_dia_horarios = %s
                      AND Horarios.id_tramo_horarios = %s
                      AND Asignaturas.nombre LIKE 'Guardia%%'
                )
                AND NOT EXISTS (
                    SELECT 1 FROM Horarios
                    JOIN Asignaturas ON Horarios.id_asignatura_horarios = Asignaturas.id_asignatura
                    WHERE Horarios.dni_profesor_horarios = Profesores.dni
                      AND Horarios.id_dia_horarios = %s
                      AND Horarios.id_tramo_horarios = %s
                      AND Asignaturas.nombre NOT LIKE 'Guardia%%'
                )
                AND NOT EXISTS (
                    SELECT 1 FROM Ausencias
                    WHERE Ausencias.dni_profesor_ausencias = Profesores.dni
                      AND Ausencias.fecha = %s
                )
            """, (dia_semana, guardia['id_tramo'], dia_semana, guardia['id_tramo'], fecha_actual))
            profesores_disponibles[guardia['id_tramo']] = cursor.fetchall()

        # Proceso en el cual se realiza las asignaciones
        if request.method == 'POST':
            for clave, valores in request.form.lists():
                # Identificamos los campos que empiezan por "tramo" para así obtener los tramos seleccionados
                if clave.startswith("tramo_"):
                    tramo_id = int(clave.split("_")[1])
                    for dni_profesor in valores:
                        # Insertamos la guardia en el caso de que no existiera antes.
                        cursor.execute("""
                            INSERT IGNORE INTO Guardias (dni_profesor_guardias, id_dia_guardias, id_tramo_guardias)
                            VALUES (%s, %s, %s)
                        """, (dni_profesor, dia_semana, tramo_id))
                        # Actualizamos los puntos cuando se asigne una guardia incrmentandolo de uno en uno
                        cursor.execute("""
                            UPDATE Profesores SET puntos_guardia = puntos_guardia + 1 WHERE dni = %s
                        """, (dni_profesor,))
            # Guardamos los cambios realizados en la base de datos            
            connection.commit()
            mensaje = "Guardias asignadas correctamente."
    # Cerramos la conexión con la base de datos
    connection.close()
    return render_template('gestionar_Guardias.html', guardias_dia=guardias_dia, profesores_disponibles=profesores_disponibles, mensaje=mensaje)


# Función que muestra las guardias que se le ha asignado al profesor donde ha iniciado sesión
@app.route('/guardias/asignadas')
def guardias_asignadas():
    # En caso de que no haya una sesión iniciada, lo redirige al login para que el usuario se logue    
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    # Establecemos la conexión con la base de datos
    connection = get_db_connection()
    # La variable hoy almacena la fecha actual.
    hoy = date.today()

    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        # Realizamos esta primera consulta en la cual vamos a obtener las guardias que se le han asignado al profesor en el día de hoy
        cursor.execute("""
            SELECT Tramos_Horarios.horario,
                   COALESCE(Aulas.nombre, 'No especificada') AS aula_nombre,
                   Tareas.texto AS tarea,
                   Tareas.archivo
            FROM Guardias
            JOIN Tramos_Horarios ON Guardias.id_tramo_guardias = Tramos_Horarios.id_tramo
            LEFT JOIN Aulas ON Guardias.id_aula_guardias = Aulas.id_aula
            LEFT JOIN Ausencias ON Ausencias.fecha = %s
                                  AND Ausencias.id_tramo_ausencias = Guardias.id_tramo_guardias
            LEFT JOIN Tareas ON Tareas.id_ausencia_tareas = Ausencias.id_ausencia
            WHERE Guardias.dni_profesor_guardias = %s
              AND Guardias.id_dia_guardias = WEEKDAY(%s) + 1
            ORDER BY Tramos_Horarios.id_tramo
        """, (hoy, session['usuario_dni'], hoy))
        # La variable guardias contiene los resultados de la consulta en una lista de diccionarios
        guardias = cursor.fetchall()

    # Finalizamos la conexión con la base de datos
    connection.close()
    return render_template('guardias_asignadas.html', guardias=guardias)

# Reportacion de Incidencias

# Función para que el profesor este en una guardia pueda reportar incidencias que ha sucedido
@app.route('/incidencias/reportar', methods=['GET', 'POST']) 
def reportar_incidencia():
    
    # En caso de que no haya una sesión iniciada, lo redirige al login para que el usuario se logue   
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    # La variable mensaje almacena el mensaje que muestra en pantalla
    mensaje = ""
    # Listado en el cual se almacenara las guardias que se han asignado en el profesor logueado
    guardias_profesor = []

    # Establecemos la conexión con la base de datos
    connection = get_db_connection()
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        # Esta primera consulta vamos a obtener las guardias que se le han asignado al profesor.
        cursor.execute("""
            SELECT Guardias.id_guardia, Dias_Semana.nombre AS dia, Tramos_Horarios.horario, Aulas.nombre AS aula
            FROM Guardias
            JOIN Dias_Semana ON Guardias.id_dia_guardias = Dias_Semana.id_dia
            JOIN Tramos_Horarios ON Guardias.id_tramo_guardias = Tramos_Horarios.id_tramo
            LEFT JOIN Aulas ON Guardias.id_aula_guardias = Aulas.id_aula
            WHERE Guardias.dni_profesor_guardias = %s
        """, (session['usuario_dni'],))
        # Guardamos en la variable guardias_profesor el resultado de la consulta que hemos realizado anteriormente
        guardias_profesor = cursor.fetchall()

    if request.method == 'POST':
        # Obtenemos el id de la guardia que se ha seleccionado y el texto que ha indicado en la incidencia y lo almacenamos en la variable id_guardia y texto.
        id_guardia = request.form['id_guardia']
        texto = request.form['texto']

        # Comprobamos que todos los campos están rellenados
        if not all([id_guardia, texto]):
            mensaje = "Todos los campos son obligatorios."
        else:
            with connection.cursor() as cursor:
                try:
                    # Realizamos la insercción de la nueva incidencia que ha generado el profesor@ en la base de datos
                    cursor.execute("""
                        INSERT INTO Incidencias (id_guardia_incidencias, texto)
                        VALUES (%s, %s)
                    """, (id_guardia, texto))
                    # Guardamos los cambios que hemos realizado
                    connection.commit()
                    mensaje = "Incidencia reportada correctamente."
                except Exception as e:
                    # En caso de dar algún error este nos mostrará porque no se ha podido registrar la incidencia.
                    mensaje = f"Error al registrar la incidencia: {str(e)}"

    # Cerramos la conexión con la base de datos
    connection.close()
    return render_template('reportar_incidencia.html', mensaje=mensaje, guardias=guardias_profesor)

# Función para visualizar todas las incidencias que se han realizado
@app.route('/incidencias/reportadas', methods=['GET'])
def incidencias_reportadas():
    # En caso de que no haya una sesión iniciada, lo redirige al login para que el usuario se logue   
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    # Obtenemos la fecha de inicio y fin en el cual se quieren realizar las busquedas de las incidencias
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')

    # Esta primera consulta que hacemos en esta función obtenemos las incidencias que se han registrado
    query = """
        SELECT Profesores.nombre AS profesor, Guardias.id_dia_guardias, Dias_Semana.nombre AS dia, Guardias.id_tramo_guardias, Tramos_Horarios.horario, 
        IFNULL(Aulas.nombre, 'No especificada') AS aula, Incidencias.texto, Incidencias.timestamp AS fecha
        FROM Incidencias
        JOIN Guardias ON Incidencias.id_guardia_incidencias = Guardias.id_guardia
        JOIN Profesores ON Guardias.dni_profesor_guardias = Profesores.dni
        JOIN Dias_Semana ON Guardias.id_dia_guardias = Dias_Semana.id_dia
        JOIN Tramos_Horarios ON Guardias.id_tramo_guardias = Tramos_Horarios.id_tramo
        LEFT JOIN Aulas ON Guardias.id_aula_guardias = Aulas.id_aula
        WHERE 1=1
    """

    # Variables en la cual almacena las listas para almacenar los filtros que hay en el formulario y los parámetros de la consulta
    filtros = []
    params = []

    # En caso de que se indique una fecha de inicio, esto se añade en la consulta
    if fecha_inicio:
        query += " AND DATE(Incidencias.timestamp) >= %s"
        params.append(fecha_inicio)
    # En caso de que se indique una fecha de fin, esto se añade en la consulta
    if fecha_fin:
        query += " AND DATE(Incidencias.timestamp) <= %s"
        params.append(fecha_fin)

    # Ordenamos todas las incidencias por fecha de maera descendente es decir de la más reciente a la más antigua
    query += " ORDER BY Incidencias.timestamp DESC"

    # Establecemos la conexión con la base de datos
    connection = get_db_connection()
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute(query, tuple(params))
        # Obtenemos los resultados de la consulta que se ha realizado
        incidencias = cursor.fetchall()
    # Cerramos con la conexión de la base de datos
    connection.close()

    return render_template('incidencias_reportadas.html', incidencias=incidencias)

# Función en la que un profesor que este ausente pueda registrar una tarea para el alumnado
@app.route('/tareas/registrar', methods=['GET', 'POST'])
def registrar_tarea():
    # En caso de que no haya una sesión iniciada, lo redirige al login para que el usuario se logue   
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    # Variable en la que almacenara el mensaje que se mostrará en pantalla
    mensaje = ""
    # Establecemos la conexión con la base de datos.
    connection = get_db_connection()

    if request.method == 'POST':
        # Recuperamos los datos que se han enviado en el formulario.
        id_ausencia = request.form['id_ausencia']
        texto = request.form['texto']
        archivo = request.files.get('archivo')

        archivo_nombre = None
        # En caso de que se haya subido un archivo, lo almacenamos de manera segura
        if archivo and archivo.filename:
            filename = secure_filename(archivo.filename)
            carpeta_destino = os.path.join(current_app.root_path, "static", "tareas")
            os.makedirs(carpeta_destino, exist_ok=True)
            ruta_archivo = os.path.join(carpeta_destino, filename)
            archivo.save(ruta_archivo)
            archivo_nombre = filename

        # Validamos que los campos del formulario obligatorios estén completos
        if not all([id_ausencia, texto]):
            mensaje = "Todos los campos obligatorios deben estar completos."
        else:
            with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                # Consulta en la cual vamos a obtener el grupo asociado al horario del profesor que se encuentra ausente
                cursor.execute("""
                    SELECT Horarios.id_grupo_horarios
                    FROM Horarios
                    JOIN Ausencias ON Horarios.dni_profesor_horarios = Ausencias.dni_profesor_ausencias
                                     AND Horarios.id_tramo_horarios = Ausencias.id_tramo_ausencias
                    WHERE Ausencias.id_ausencia = %s
                    LIMIT 1
                """, (id_ausencia,))
                resultado = cursor.fetchone()

                # Si encontramos el grupo, registramos las tareas
                if resultado and resultado['id_grupo_horarios']:
                    id_grupo = resultado['id_grupo_horarios']

                    try:
                        # Realizamos una insercción en la base de datos con la tarea que se ha creado
                        cursor.execute("""
                            INSERT INTO Tareas (id_ausencia_tareas, id_grupo_tareas, texto, archivo)
                            VALUES (%s, %s, %s, %s)
                        """, (id_ausencia, id_grupo, texto, archivo_nombre))
                        # Guardamos los cambios realizado en la base de datos
                        connection.commit()
                        mensaje = "Tarea registrada correctamente."
                    except pymysql.err.IntegrityError:
                        # En caso de que nos de un fallo nos mostrará el siguiente mensaje 
                        mensaje = "Ya existe una tarea para esa ausencia y grupo."
                else:
                    # Si no encontramos ningun grupo mostrará un mensaje en el cual indicara que no se puede asignar la tarea
                    mensaje = "No se pudo asignar la tarea. Verifica que el profesor tenga horario asignado ese día."

    # Cargamos las ausencias que hay en un futuro
     
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("""
            SELECT Ausencias.id_ausencia, Ausencias.fecha, Tramos_Horarios.horario
            FROM Ausencias
            JOIN Tramos_Horarios ON Ausencias.id_tramo_ausencias = Tramos_Horarios.id_tramo
            WHERE Ausencias.dni_profesor_ausencias = %s AND Ausencias.fecha >= CURDATE()
            ORDER BY Ausencias.fecha, Tramos_Horarios.id_tramo
        """, (session['usuario_dni'],))
        ausencias = cursor.fetchall()

    # Finalizamos la conexión con la base de datos
    connection.close()
    return render_template('registrar_tarea.html', mensaje=mensaje, ausencias=ausencias)

# Gestión de Ausencias #

# Función en la que un profesor en el caso de que se encuentre ausente puede registrar su ausencia
@app.route('/ausencias/comunicar', methods=['GET', 'POST'])
def comunicar_ausencia():
    # En caso de que no haya una sesión iniciada, lo redirige al login para que el usuario se logue
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    # La variable mensaje como se ha indicado anteriormente se va a usar para que almacene el mensaje que se va a mostrar por pantalla.
    mensaje = ""
    # Establecemos la conexión con la base de datos
    connection = get_db_connection()

    if request.method == 'POST':
        dni = session['usuario_dni']
        # Obtenemos el dni del usuario que se encuentra actualmente logeado
        fecha = request.form['fecha']
        tramos = request.form.getlist('tramo')
        motivo = request.form['motivo']

        # Comprobamos que los campos fecha y los tramos del formulario no se encuentre vacio, en caso de que uno de esos dos campos se encuentre vacio mostrará el siguiente mensaje de error.
        if not fecha or not tramos:
            mensaje = "Los campos fecha y tramos son obligatorios"
        else:
            try:
                # Obtenemos la fecha que se nos ha indicado en el formulario.
                fecha_dt = datetime.strptime(fecha, '%Y-%m-%d').date()
                # En el caso de que la fecha sea anterior al día de hoy es decir que sea una fecha pasada nos mostrará el mensaje que no se ha podido registrar la ausencia debido a que es una fecha pasada
                if fecha_dt < date.today():
                    mensaje = "No puedes registrar la ausencia debido a que es una fecha pasada."
                # En el caso de que la fecha sea hoy o la de un futuro entra en este apartado
                else:
                    with connection.cursor() as cursor:
                        # La variable errores es una lista en la cual se podrá almacenar posibles errores.
                        errores = []
                        for tramo in tramos:
                            try:
                                # Insertamos en la tabla Ausencias cada tramo que hemos seleccionado
                                cursor.execute("""
                                    INSERT INTO Ausencias (dni_profesor_ausencias, fecha, id_tramo_ausencias, motivo)
                                    VALUES (%s, %s, %s, %s)
                                """, (dni, fecha, tramo, motivo))
                            except pymysql.err.IntegrityError:
                                # En caso de que haya algún error en la insercción nos mostrará un mensaje en el cual nos indicara que hay ya una ausencia para ese tramo.
                                errores.append(f"Ya existe una ausencia para el tramo {tramo} en esa fecha.")
                        # Guardamos los cambios en la base de datos
                        connection.commit()
                    # Si la lista de errores no se encuentra vacía mostrará todos los errores que ha almacenado
                    if errores:
                        mensaje = "Algunas ausencias no se registraron: " + "; ".join(errores)
                    else:
                        # En caso de que no haya errores indica que las ausencias se han comunicado correctamente.
                        mensaje = "Ausencia(s) comunicada(s) correctamente."
            # En caso de que la fecha que introduzca el profesor/dirección no sea valida mostrará un mensaje en el cual dira que la fecha no es valida
            except ValueError:
                mensaje = "La fecha introducida no es válida."

    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT id_tramo, horario FROM Tramos_Horarios")
        tramos = cursor.fetchall()
    # Cerramos la conexión con la base de datos
    connection.close()

    return render_template('comunicar_ausencia.html', tramos=tramos, mensaje=mensaje)

# Función en el cual se pueden comunicar la reincorporación de los profesores que se encuentran ausentes
@app.route('/ausencias/reincorporacion', methods=['GET', 'POST'])
def comunicar_reincorporacion():
    # En caso de que no haya una sesión iniciada, lo redirige al login para que el usuario se logue   
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    # La variable mensaje almacena el mensaje que muestra en pantalla
    mensaje = ""
    # Establecemos la conexión con la base de datos
    connection = get_db_connection()
    # La variable hoy almacena la fecha actual
    hoy = date.today()

    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        # Consulta en la cual obtenemos todas las ausencias del día de hoy en la cual no se ha comunicado que el profesor@ se ha reincorporado
        cursor.execute("""
            SELECT Ausencias.id_ausencia, Tramos_Horarios.horario, Ausencias.fecha, Profesores.nombre, Profesores.apellidos
            FROM Ausencias
            JOIN Tramos_Horarios ON Ausencias.id_tramo_ausencias = Tramos_Horarios.id_tramo
            JOIN Profesores ON Ausencias.dni_profesor_ausencias = Profesores.dni
            WHERE Ausencias.fecha = %s AND Ausencias.reincorporado_profesor = FALSE
        """, (hoy,))
        # Guardamos el resultado de la consulta en la variable ausencias
        ausencias = cursor.fetchall()

        if request.method == 'POST':
            # Obtenemos los ids de las ausencias que se han reincorporado
            ids_reincorporados = request.form.getlist('reincorporados')
            for id_aus in ids_reincorporados:
                # Actualizamos en la tabla Ausencias e indicamos que el profesor se ha reincorporado.
                cursor.execute("""
                    UPDATE Ausencias SET reincorporado_profesor = TRUE WHERE id_ausencia = %s
                """, (id_aus,))
            # Guardamos los cambios que hemos realizado en la base de datos
            connection.commit()
            # En caso de que se comunique una reincorporación guardamos en la variable mensaje el siguiente mensaje que se mostrará en texto
            mensaje = "Reincorporación enviada para validación de dirección."
    # Cerramos la conexión con la base de datos
    connection.close()
    return render_template('comunicar_reincorporacion.html', ausencias=ausencias, mensaje=mensaje)

@app.route('/ausencias/validar_reincorporacion', methods=['GET', 'POST'])
def validar_reincorporacion():
    # En caso de que no haya una sesión iniciada, lo redirige al login para que el usuario se logue   
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))

    # Establecemos la conexión con la base de datos.
    connection = get_db_connection()
    # La variable mensaje almacena el mensaje que muestra en pantalla
    mensaje = ""
    # La variable hoy contiene la fecha actual
    hoy = date.today()

    with connection.cursor() as cursor:
        # Esta primera consulta obtiene el id del perfil del usuario que ha iniciado sesión
        cursor.execute("SELECT id_perfil_profesores FROM Profesores WHERE dni = %s", (session['usuario_dni'],))
        # El resultado de la consulta lo guardamos en la variable perfil
        perfil = cursor.fetchone()

        # Si el perfil que hemos obtenido en la consulta anterior no es 2, redireccionamos al usuario a la página home
        if perfil['id_perfil_profesores'] != 2:
            # Cerramos la conexión con la base de datos
            connection.close()
            return redirect(url_for('home'))

    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        # Esta segunda consulta obtiene las ausencias reincorporadas que han sido notificadas pero no han sido validadas.
        cursor.execute("""
            SELECT Ausencias.id_ausencia, Profesores.nombre, Profesores.apellidos, Tramos_Horarios.horario, Ausencias.fecha
            FROM Ausencias
            JOIN Profesores ON Ausencias.dni_profesor_ausencias = Profesores.dni
            JOIN Tramos_Horarios ON Ausencias.id_tramo_ausencias = Tramos_Horarios.id_tramo
            WHERE Ausencias.fecha = %s
              AND Ausencias.reincorporado_profesor = TRUE
              AND Ausencias.validacion_direccion = FALSE
        """, (hoy,))
        # El resultado de la consulta lo guardamos en la variable ausencias
        ausencias = cursor.fetchall()

        if request.method == 'POST':
            ids_validadas = request.form.getlist('validadas')
            for id_aus in ids_validadas:
                # Actualizamos la tabla Ausencias en el cual indicamos que la ausencia ya se encuentra validada por Dirección
                cursor.execute("""
                    UPDATE Ausencias
                    SET validacion_direccion = TRUE
                    WHERE id_ausencia = %s
                """, (id_aus,))
            # Guardamos los cambios que hemos realizado en la base de datos.
            connection.commit()
            # Guardamos en la variable el mensaje que se mostrará cuando las reincorporaciones se validen correctamente
            mensaje = "Reincorporaciones validadas correctamente."
    # Cerramos la conexión con la base de datos
    connection.close()
    return render_template('validar_reincorporacion.html', ausencias=ausencias, mensaje=mensaje)

# CHAT #

# Función en la cual mostrará el chat
@app.route('/chat')
def chat():
    # En caso de que no haya una sesión iniciada, lo redirige al login para que el usuario se logue   
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))
    # Obtenemos los mensajes
    mensajes = list(coleccion_mensajes.find({"archivado": False}).sort("timestamp", -1))
    return render_template('chat.html', mensajes=mensajes)

# Función en la cual obtenemos los mensajes del chat en formato json
@app.route('/chat/mensajes')
def obtener_mensajes():
    # Obtenemos todos los mensajes de la colección de mensajes que no se encuentran archivados, almacenandolo de más reciente a mas antiguo
    mensajes = list(coleccion_mensajes.find({"archivado": False}).sort("timestamp", -1))
    # Bucle en el cual recorre todos los mensajes que se han obtenido
    for m in mensajes:
        # Convierte el id del mensaje de MongoDB a una cadena de texto
        m["_id"] = str(m["_id"])
        # Muestra el tiempo de cada mensaje
        m["timestamp"] = m["timestamp"].strftime("%d/%m/%Y %H:%M")
    # Devuelve los mensajes que se han obtenido en formato JSON para así poder procesarlo en el fronted
    return jsonify(mensajes)

# Función que permite enviar mensajes del chat
@app.route('/chat/enviar', methods=['POST'])
def enviar_mensaje():
    # En caso de que no haya una sesión iniciada, lo redirige al login para que el usuario se logue   
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))
    # Obtiene el mensaje que se ha mandado en el chat
    mensaje = request.form['mensaje']
    # Comprobamos que el mensaje que han enviado no se encuentre vacio
    if mensaje.strip():
        coleccion_mensajes.insert_one({
            "autor": session['usuario_dni'], # Obtenemos el DNI del profesor que ha mandado el mensaje
            "nombre": session['username'], # Obtenemos el nombre del profesor que ha mandado el mensaje
            "mensaje": mensaje.strip(), # Obtenemos el mensaje
            "timestamp": datetime.utcnow(), # Obtenemos la fecha y hora actual del mensaje.
            "archivado": False # Indicamos el campo de archivado de la base de datos lo ponemos a False indicando que este mensaje no se encuentra archivado
        })
    # Redirigimos al usuario al chat
    return redirect(url_for('chat'))

# Función que permite archivar mensajes del chat
@app.route('/chat/archivar/<id>')
def archivar_mensaje(id):
    # Si el usuario no se encuentra logeado lo redireccióna a la pagina de logeo
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))
    # Realizamos conexión con la base de datos
    connection = get_db_connection()
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        # Esta primera consulta va a obtener el perfil del usuario para más adelante comprobar si puede archivar el mensaje del chat.
        cursor.execute("SELECT id_perfil_profesores FROM Profesores WHERE dni = %s", (session['usuario_dni'],))
        # La variable perfil obtiene el perfil del profesor y la almacena
        perfil = cursor.fetchone()
    # Cerramos la conexión con la base de datos
    connection.close()
    # Si la variable perfil es nula o es distinta de dos (perfil de dirección) lo redireccióna al chat
    if not perfil or perfil['id_perfil_profesores'] != 2:
        return redirect(url_for('chat'))
    # Archivamos el mensaje en el cual cambiamos el campo archivado a True
    coleccion_mensajes.update_one({'_id': ObjectId(id)}, {'$set': {'archivado': True}})
    # Una vez que se archive el mensaje redigirimos al usuario al chat.
    return redirect(url_for('chat'))

# Función que permite eliminar mensajes del chat
@app.route('/chat/eliminar/<id>')
def eliminar_mensaje(id):
    # Si el usuario no se encuentra logeado lo redireccióna a la pagina de logeo
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))
    # Realizamos conexión con la base de datos
    connection = get_db_connection()
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        # Esta primera consulta va a obtener el perfil del usuario para más adelante comprobar si puede eliminar el mensaje del chat.
        cursor.execute("SELECT id_perfil_profesores FROM Profesores WHERE dni = %s", (session['usuario_dni'],))
        # La variable perfil obtiene el perfil del profesor y la almacena
        perfil = cursor.fetchone()
    # Cerramos la conexión con la base de datos
    connection.close()

    # Si la variable perfil es nula o es distinta de dos (perfil de dirección) lo redireccióna al chat
    if not perfil or perfil['id_perfil_profesores'] != 2:
        return redirect(url_for('chat'))

    # Eliminamos el mensaje que contenga el ID que se ha proporcionado de la colección de mensajes que hay en la base de datos 
    coleccion_mensajes.delete_one({'_id': ObjectId(id)})
    # Una vez que se elimine el mensaje redigirimos al usuario al chat.
    return redirect(url_for('chat'))

# Actividades Extraescolares #

# Función que permite registrar las actividades extraescolares
@app.route('/actividades/registrar', methods=['GET', 'POST'])
def registrar_actividad_extraescolar():
    # En caso de que no haya una sesión iniciada, lo redirige al login para que el usuario se logue  
    if 'usuario_dni' not in session:
        return redirect(url_for('login'))
    # Establecemos la conexión con la base de datos
    connection = get_db_connection()
    # La variable mensaje almacena el mensaje que muestra en pantalla
    mensaje = ""
    # La variable hoy obtiene la fecha actual
    hoy = date.today()

    # Si el metodo es POST; es decir cuando se envia el formulario
    if request.method == 'POST':
        grupo = request.form['grupo'] # Obtenemos el grupo que se ha seleccionado en el formulario
        fecha = request.form['fecha'] # Obtenemos la fecha que se ha seleccionado en el formulario
        tramos = request.form.getlist('tramos') # Obtenemos los tramos que se han seleccionado en el formulario
        afecta_completo = 'afecta_completo' in request.form # Verificamos si la casilla en la cual indicamos si afecta completamente al aula se encuentra marcada
        profesores = request.form.getlist('profesores') # Obtenemos los profesores que se han seleccionado en el formulario.

        with connection.cursor() as cursor:
            # Por cada tramo que se ha seleccionado en el formulario, insertamos la actividad extraescolar en la base de datos
            for tramo in tramos:
                cursor.execute("""
                    INSERT INTO Actividades_Extraescolares ( id_grupo_actividades_extraescolares, fecha, id_tramo_actividades_extraescolares, dni_profesor_actividades_extraescolares, afecta_grupo_completo )
                     VALUES (%s, %s, %s, %s, %s)
                """, (grupo, fecha, tramo, session['usuario_dni'], afecta_completo))

                # Por cada profesor que hemos indicado que va a estar en la actividad extraescolar insertamos en la tabla ausencia la ausencia de ese profesor
                for dni in profesores:
                    cursor.execute("""
                        INSERT INTO Ausencias (dni_profesor_ausencias, fecha, id_tramo_ausencias, motivo)
                        VALUES (%s, %s, %s, %s)
                    """, (dni, fecha, tramo, "Acompaña actividad extraescolar"))
        # Guardamos los cambios en la base de datos
        connection.commit()
        # Almacenamos en la variable mensaje el mensaje que se mostrara en caso de que las insercciones funcione correctamente
        mensaje = "Actividad registrada correctamente."

    # Mediante este cursor obtenemos los datos para poder rellenar el formulario
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT id_grupo, nombre FROM Grupos")
        grupos = cursor.fetchall()
        cursor.execute("SELECT id_tramo, horario FROM Tramos_Horarios")
        tramos = cursor.fetchall()
        cursor.execute("SELECT dni, nombre, apellidos FROM Profesores")
        profesores = cursor.fetchall()

    # Cerramos la conexión con la base de datos
    connection.close()
    return render_template('registrar_actividad_extraescolar.html', grupos=grupos, tramos=tramos, profesores=profesores, mensaje=mensaje)

# Función en la cual cuando el usuario cierre sesión se ejecutara.
@app.route('/logout')
def logout():
    # Limpiamos todos los datos de la sesión que ha estado abierta por el usuario, así cerrando su sesión de manera automatica
    session.clear()
    # Redirecciona al usuario a la página inicial para que inicie sesión de nuevo
    return redirect(url_for('login'))

# Comprobamos si este archivo se esta ejecutando de manera directa
if __name__ == '__main__':
    # Inicializamos la aplicación con Flask en modo debug, esto hace que muestra los errores de manera detallada
    app.run(debug=True)