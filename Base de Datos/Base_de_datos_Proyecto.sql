DROP DATABASE Proyecto_Final;

CREATE DATABASE Proyecto_Final;

USE Proyecto_Final;

/** Tabla Profesores que almacenara el dni del profesor, el nombre, apellidos, email y 
    puntos de guardia que va a tener el profesor y el perfil que tiene si es Profesor o Directivo**/

CREATE TABLE Profesores (
    dni VARCHAR(9) PRIMARY KEY, -- Almacena el DNI del profesor como clave primaria
    nombre VARCHAR(100) NOT NULL,
    apellidos VARCHAR(150) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL, -- Indicamos el email del profesor para en un futuro sera con el que se logeara en la aplicación
    puntos_guardia INT DEFAULT 0,
    perfil ENUM('Profesorado', 'Directivo') NOT NULL
);

/** Tabla Grupos en la cual se almacenara un identificador que se va a ir autoincrementando y el nombre del curso **/ 

CREATE TABLE Grupos (
    id_Grupo INT AUTO_INCREMENT PRIMARY KEY, -- Identificador del grupo
    nombre_Grupo VARCHAR(50) NOT NULL UNIQUE -- Nombre del grupo
);

/** Tabla Horarios en la cual se asignara cada horario del profesor se indentificara que los valores que se introduzca en la base de datos sea de Lunes
    a Viernes y que el tramo de horario es dentro del que hay establecido en el instituto **/

CREATE TABLE Horarios (
    id_horario INT AUTO_INCREMENT PRIMARY KEY, -- Identificador de cada horario que introduzcamos
    dni_profesor VARCHAR(9) NOT NULL, -- Identificador del profesor
    dia ENUM('Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes') NOT NULL, -- Comprobamos que los días del horario solamente sean de Lunes a Viernes y no otro día
    tramo_horario ENUM(
        '08:15-09:15',
        '09:15-10:15',
        '10:15-11:15',
        '11:15-11:45',
        '11:45-12:45',
        '12:45-13:45',
        '13:45-14:45'
    ) NOT NULL, -- Comprobamos que los horas del horario solamente sean dentro del horario escolar y no otra hora del día
    id_grupo_horario INT NOT NULL, -- Indicamos el id del grupo.
    aula VARCHAR(50) NOT NULL, -- Indicamos el aula en el que se esta realizando este horario
    UNIQUE (dni_profesor, dia, tramo_horario),
    FOREIGN KEY (dni_profesor) REFERENCES Profesores(dni),
    FOREIGN KEY (id_grupo_horario) REFERENCES Grupos(id_Grupo)
);


/** Tabla Guardias en la cual almacenaremos la información de las guardias que tiene cada profesor sucede lo mismo que la tabla horarios comprobamos las horas y el día**/

CREATE TABLE Guardias (
    id_Guardia INT AUTO_INCREMENT PRIMARY KEY,
    dni_profesor VARCHAR(9) NOT NULL,
    dia ENUM('Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes') NOT NULL, -- Comprobamos que los días del horario solamente sean de Lunes a Viernes y no otro día
    tramo_horario ENUM(
        '08:15-09:15',
        '09:15-10:15',
        '10:15-11:15',
        '11:15-11:45',
        '11:45-12:45',
        '12:45-13:45',
        '13:45-14:45'
    ) NOT NULL, -- Comprobamos que los horas de las guardias que se asignen solamente sean dentro del horario escolar y no otra hora del día
    aula_zona VARCHAR(50) NOT NULL,
    UNIQUE (dni_profesor, dia, tramo_horario),
    FOREIGN KEY (dni_profesor) REFERENCES Profesores(dni)
);

/** Tabla Ausencias en la cual se indicara las ausencias de cada profesor que ha faltado, comprobaremos como se ha venido realizando en las dos tablas anteriormente 
    que las Ausencias se indique en el tramo de horario correspondiente **/

CREATE TABLE Ausencias (
    id_Ausencia INT AUTO_INCREMENT PRIMARY KEY,
    dni_profesor VARCHAR(9) NOT NULL,
    fecha DATE NOT NULL,
    tramo_horario ENUM(
        '08:15-09:15',
        '09:15-10:15',
        '10:15-11:15',
        '11:15-11:45',
        '11:45-12:45',
        '12:45-13:45',
        '13:45-14:45'
    ) NOT NULL,
    id_Grupo_Ausencias INT NOT NULL,
    aula_zona VARCHAR(50) NOT NULL,
    motivo TEXT,
    FOREIGN KEY (dni_profesor) REFERENCES Profesores(dni),
    FOREIGN KEY (id_Grupo_Ausencias) REFERENCES Grupos(id_Grupo),
    UNIQUE (dni_profesor, fecha, tramo_horario, id_Grupo_Ausencias)
);

/** Tabla Incidencias en la cual se almancenara toda la información de las Incidencias que sucedan **/

CREATE TABLE Incidencias (
    id_Incidencias INT AUTO_INCREMENT PRIMARY KEY,
    id_Guardia_Incidencias INT NOT NULL,
    texto TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_Guardia_Incidencias) REFERENCES Guardias(id_Guardia)
);

/** Tabla Tareas que almacenara la información que indique el profesor cuando se encuentre ausente para cada tramo horario que falte **/

CREATE TABLE Tareas (
    id_Tareas INT AUTO_INCREMENT PRIMARY KEY,
    id_Ausencia_Tareas INT NOT NULL,
    id_Grupo_Tareas INT NOT NULL,
    texto TEXT NOT NULL,
    FOREIGN KEY (id_Ausencia_Tareas) REFERENCES Ausencias(id_Ausencia),
    FOREIGN KEY (id_Grupo_Tareas) REFERENCES Grupos(id_Grupo),
    UNIQUE (id_Ausencia_Tareas, id_Grupo_Tareas) -- Evita que se registren dos tareas para el mismo grupo en la misma ausencia
);

 /** Tabla Actividades_Extraescolares en la cual almacenara las actividades extraescolares que se realicen en clase **/

CREATE TABLE Actividades_Extraescolares (
    id_Actividades_Extraescolares INT AUTO_INCREMENT PRIMARY KEY,
    id_Grupo_Actividades_Extraescolares INT NOT NULL,
    dia DATE NOT NULL,
    hora ENUM(
        '08:15-09:15',
        '09:15-10:15',
        '10:15-11:15',
        '11:15-11:45',
        '11:45-12:45',
        '12:45-13:45',
        '13:45-14:45'
    ) NOT NULL,
    dni_profesor_acompanante VARCHAR(9) NOT NULL,
    afecta_grupo_completo BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (dni_profesor_acompanante) REFERENCES Profesores(dni),
    FOREIGN KEY (id_grupo_Actividades_Extraescolares) REFERENCES Grupos(id_Grupo),
    UNIQUE (id_grupo_Actividades_Extraescolares, dia, hora)
);
