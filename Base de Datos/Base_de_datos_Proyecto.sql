DROP DATABASE Proyecto_Final;

CREATE DATABASE Proyecto_Final;

USE Proyecto_Final;

/** Tabla Perfiles en la cual almacenara información de los diferentes perfiles que van a ser que pueden ser o profesorado o directivo **/

	CREATE TABLE Perfiles (
		id_perfil INT AUTO_INCREMENT PRIMARY KEY,
		nombre VARCHAR(50) UNIQUE NOT NULL
	);

/** Tabla Profesores en la cual se almacena el dni del profesor como llave primaria los nombre y los apellidos el correo para en un futuro realizar un logeo, 
	los puntos para gestionar la guardia y el perfil que contiene cada profesor **/
    
	CREATE TABLE Profesores (
    dni VARCHAR(9) PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellidos VARCHAR(150) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    puntos_guardia INT DEFAULT 0,
    id_perfil_profesores INT NOT NULL,
    FOREIGN KEY (id_perfil_profesores) REFERENCES Perfiles(id_perfil)
	);

/** Tabla Grupos en el cual se almacenara el id del grupo y el nombre que contiene cada grupo. **/

	CREATE TABLE Grupos (
		id_grupo INT AUTO_INCREMENT PRIMARY KEY,
		nombre VARCHAR(50) UNIQUE NOT NULL
	);

/** Tabla Días de la semana, en la cual almacenara los días de la semana que hay dando clase por si en un futuro no hay clase un día como por ejemplo un Viernes y es de Lunes a Jueves, 
	en vez de realizar un ENUM en cada tabla realizo esta tabla y así es mas facil modificar los datos en un futuro **/

	CREATE TABLE Dias_Semana (
		id_dia INT AUTO_INCREMENT PRIMARY KEY,
		nombre VARCHAR(10) UNIQUE NOT NULL
	);

/** Tabla Tramos Horarios en el cual almacenara los horarios que hay en el instituto esto lo realizo para que no haya que modificarlo en todas las tablas 
	y se modifique nada más que en esta **/

	CREATE TABLE Tramos_Horarios (
		id_tramo INT AUTO_INCREMENT PRIMARY KEY,
		horario VARCHAR(20) UNIQUE NOT NULL
	);

/** Tabla Asignaturas en la cual se almacenara la información de cada asignatura **/

    CREATE TABLE Asignaturas (
    id_asignatura INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE NOT NULL
	);
    
    CREATE TABLE Aulas (
    id_aula INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE NOT NULL
    );

/** Tabla Horarios en la cual almacenara todos los horarios de cada profesor la clave primaria sera un identificador que sera auto incremental, 
	el dni del profesor para ver cada hora que tiene asignado cada profesor, el id del díua en el cual se realiza la hora, el tramo de horario en el cual realiza la hora y el id del grupo
    con el que va a dar clase, ponemos una restricción que la combinación del dni del profesor, el id del dia y el id del tramo horario no se pueda repetir, pongo como clave 
    foranea el dni del profesor, el id del día, el id del tramo horario, el id del grupo y el id de la asignatura **/

	CREATE TABLE Horarios (
    id_horario INT AUTO_INCREMENT PRIMARY KEY,
    dni_profesor_horarios VARCHAR(9) NOT NULL,
    id_dia_horarios INT NOT NULL,
    id_tramo_horarios INT NOT NULL,
    id_grupo_horarios INT,
    id_asignatura_horarios INT NOT NULL,
    id_aula INT,
    UNIQUE (dni_profesor_horarios, id_dia_horarios, id_tramo_horarios),
    FOREIGN KEY (dni_profesor_horarios) REFERENCES Profesores(dni) ON DELETE CASCADE,
    FOREIGN KEY (id_dia_horarios) REFERENCES Dias_Semana(id_dia),
    FOREIGN KEY (id_tramo_horarios) REFERENCES Tramos_Horarios(id_tramo),
    FOREIGN KEY (id_grupo_horarios) REFERENCES Grupos(id_grupo),
    FOREIGN KEY (id_asignatura_horarios) REFERENCES Asignaturas(id_asignatura),
    FOREIGN KEY (id_aula) REFERENCES Aulas(id_aula)
);

/** Tabla Guardias almacenara las guardias que se realicen cada guardia que se realice almacenara **/

	CREATE TABLE Guardias (
    id_guardia INT AUTO_INCREMENT PRIMARY KEY,
    dni_profesor_guardias VARCHAR(9) NOT NULL,
    id_dia_guardias INT NOT NULL,
    id_tramo_guardias INT NOT NULL,
    id_aula_guardias INT,
    UNIQUE (dni_profesor_guardias, id_dia_guardias, id_tramo_guardias),
    FOREIGN KEY (dni_profesor_guardias) REFERENCES Profesores(dni) ON DELETE CASCADE,
    FOREIGN KEY (id_dia_guardias) REFERENCES Dias_Semana(id_dia),
    FOREIGN KEY (id_tramo_guardias) REFERENCES Tramos_Horarios(id_tramo),
    FOREIGN KEY (id_aula_guardias) REFERENCES Aulas(id_aula)
);

-- Tabla Ausencias
CREATE TABLE Ausencias (
    id_ausencia INT AUTO_INCREMENT PRIMARY KEY,
    dni_profesor_ausencias VARCHAR(9) NOT NULL,
    fecha DATE NOT NULL,
    id_tramo_ausencias INT NOT NULL,
    motivo TEXT,
    FOREIGN KEY (dni_profesor_ausencias) REFERENCES Profesores(dni) ON DELETE CASCADE,
    FOREIGN KEY (id_tramo_ausencias) REFERENCES Tramos_Horarios(id_tramo),
    UNIQUE (dni_profesor_ausencias, fecha, id_tramo_ausencias)
);

-- Tabla Incidencias
CREATE TABLE Incidencias (
    id_incidencia INT AUTO_INCREMENT PRIMARY KEY,
    id_guardia_incidencias INT NOT NULL,
    texto TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_guardia_incidencias) REFERENCES Guardias(id_guardia) ON DELETE CASCADE
);

-- Tabla Tareas
CREATE TABLE Tareas (
    id_tarea INT AUTO_INCREMENT PRIMARY KEY,
    id_ausencia_tareas INT NOT NULL,
    id_grupo_tareas INT NOT NULL,
    texto TEXT NOT NULL,
    FOREIGN KEY (id_ausencia_tareas) REFERENCES Ausencias(id_ausencia) ON DELETE CASCADE,
    FOREIGN KEY (id_grupo_tareas) REFERENCES Grupos(id_grupo),
    UNIQUE (id_ausencia_tareas, id_grupo_tareas)
);

-- Tabla Actividades Extraescolares
CREATE TABLE Actividades_Extraescolares (
    id_actividad INT AUTO_INCREMENT PRIMARY KEY,
    id_grupo_actividades_extraescolares INT NOT NULL,
    fecha DATE NOT NULL,
    id_tramo_actividades_extraescolares INT NOT NULL,
    dni_profesor_actividades_extraescolares VARCHAR(9) NOT NULL,
    afecta_grupo_completo BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (id_grupo_actividades_extraescolares) REFERENCES Grupos(id_grupo),
    FOREIGN KEY (id_tramo_actividades_extraescolares) REFERENCES Tramos_Horarios(id_tramo),
    FOREIGN KEY (dni_profesor_actividades_extraescolares) REFERENCES Profesores(dni),
    UNIQUE (id_grupo_actividades_extraescolares, fecha, id_tramo_actividades_extraescolares)
);