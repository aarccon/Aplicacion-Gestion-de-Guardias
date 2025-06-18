DROP DATABASE Proyecto_Final;

CREATE DATABASE Proyecto_Final;

USE Proyecto_Final;

/** 
  Tabla Perfiles: esta tabla almacena los distintos perfiles de usuarios que va a tener la aplicación,
  que van a ser, Profesorado y Dirección.

  La clave primaria es id_perfil, generado automáticamente.
  
  El campo nombre de esta tabla representa el nombre del perfil (como "Profesorado y Dirección") y se define
  como único para asi evitar perfiles duplicados y que no haya dos perfiles iguales como por ejemplo el de profesores.
**/

	CREATE TABLE Perfiles (
		id_perfil INT AUTO_INCREMENT PRIMARY KEY,
		nombre VARCHAR(50) UNIQUE NOT NULL
	);

/** 
  Tabla Profesores: esta tabla se almacena los datos de los profesores y equipo directivo del instituto.

  - La clave primaria es el dni, este campo es unico ya que ningún profesor contiene el mismo dni de otro compañero .
  - Almacenamos los datos personales de cada profesor: nombre, apellidos y correo electrónico (Recomendable que se use el coorporativo del instituto).
  - El campo puntos sirve para llevar una gestión de las guardias de los profesores como indico en el proyecto esta pensado para que haya una igualdad en la asignación de guardias.
  - El campo id_perfil_profesores indica el perfil que tiene asignada cada profesor y como podemos comprobar es una clave foránea que hace referencia a la tabla Perfiles. 
    hacia la tabla Perfiles.
**/
    
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

/** 
  Tabla Grupos: esta tabla se almacena información sobre los distintos grupos que hay en el instituto.

  - La clave primaria es id_grupo, generado automáticamente.
  - El campo nombre indica el nombre del grupo ("1º ESO A", "2º Bachillerato B") y lo indicamos como UNICO para evitar duplicados como pasa en la tabla Perfiles.
**/

	CREATE TABLE Grupos (
		id_grupo INT AUTO_INCREMENT PRIMARY KEY,
		nombre VARCHAR(50) UNIQUE NOT NULL
	);

/** 
  Tabla Dias_Semana:esta tabla se almacenan los días de la semana en los que se imparten clases.

  - La clave primaria es id_dia,generado automáticamente.
  - El campo nombre indica los diferentes días de la semana ("Lunes", "Martes", etc) y lo indicamos como UNICO para evitar dias duplicados como he comentado anteriormente.


  He optado por crear una tabla en lugar de usar un ENUM en cada tabla que use estos campos por si en un futuro se realiza una modificación de los días como por ejemplo que un Viernes ya no
  sea lectivo.
**/

	CREATE TABLE Dias_Semana (
		id_dia INT AUTO_INCREMENT PRIMARY KEY,
		nombre VARCHAR(10) UNIQUE NOT NULL
	);

/** 
  Tabla Tramos_Horarios: esta tabla se almacenan los distintos tramos horarios que hay en el instituto.

  - La clave primaria es id_tramo,generado automáticamente.
  - El campo horario indica los tramos horario ("08:15 - 09:15", "09:15 - 10:15", etc.) y lo indicamos como UNICO para evitar horas duplicadas como he comentado anteriormente.

  He optado por crear esta tabla para poder centrar la gestión de los horarios igual que con los días y así no tener que modificar un gran número de tablas en caso de que se realice
  un cambio en los tramos horarios como he indicado en el caso también de los Días de la Semana
**/

	CREATE TABLE Tramos_Horarios (
		id_tramo INT AUTO_INCREMENT PRIMARY KEY,
		horario VARCHAR(20) UNIQUE NOT NULL
	);

/** 
  Tabla Asignaturas: esta tabla se almacena la información de cada asignatura que se da en el instituto.

  - La clave primaria es id_asignatura, generado automáticamente.
  - El campo nombre indica el nombre de las asignaturas ("Lengua Castellana", "Matemáticas", etc.) y lo indicamos como UNICO para evitar Asignaturas duplicadas como he comentado anteriormente.

  Mediante esta tabla se va a poder unir asignaturas con profesores, horarios, etc.
**/

    CREATE TABLE Asignaturas (
    id_asignatura INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE NOT NULL
	);
    
/** 
  Tabla Aulas: esta tabla contiene la información de las distintas aulas del centro educativo.

  - La clave primaria es id_aula,generado automáticamente.
  - El campo nombre indica el nombredel aula ("Laboratorio", "Sala de Música", etc.) y lo indicamos como UNICO para evitar Aulas duplicadas como he comentado anteriormente.

  Esta tabla permite asociar aulas a los horarios de clase, a las guardias u otras actividades lectivas de manera estructurada.
**/

    CREATE TABLE Aulas (
    id_aula INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE NOT NULL
    );

/** 
  Tabla Horarios: esta tabla contiene los horarios de todos los profesores y equipo directivo que hay en el instituto

  - La clave primaria es id_horario, generado automáticamente.
  - En la tabla se almacenan los siguientes campos:
      - dni_profesor_horarios: dni del profesor que le van asignar a esa hora y como podemos comprobar es una clave foránea que hace referencia a la tabla Profesores
      - id_dia_horarios: día de la semana en la cual va a impartir clase y como podemos comprobar es una clave foránea que hace referencia a la tabla Dias_Semana
      - id_tramo_horarios: el tramo horario en el cual va a dar clase y como podemos comprobar es una clave foránea que hace referencia a la tabla Tramos_Horarios
      - id_grupo_horarios: el grupo/grupos que va a dar clase durante ese tramo horario y ese día. Y como podemos comprobar es una clave foránea que hace referencia a la tabla Grupos
      - id_asignatura_horarios: la asignatura que va a impartir a ese grupo, en ese tramo horario y en ese día. Y como podemos comprobar es una clave foránea que hace referencia a la tabla Asignaturas
      - id_aula: el aula en la cual va a dar clase, y como podemos comprobar es una clave foránea que hace referencia a la tabla Aulas

  - Una de las cosas que he tenido en cuenta es los siguientes datos juntos (dni_profesor_horarios, id_dia_horarios, id_tramo_horarios), así puedo asegurar que un profesor no esta dando dos
	clases a la misma hora (a no ser que se divida).
**/

	CREATE TABLE Horarios (
    id_horario INT AUTO_INCREMENT PRIMARY KEY,
    dni_profesor_horarios VARCHAR(9) NOT NULL,
    id_dia_horarios INT NOT NULL,
    id_tramo_horarios INT NOT NULL,
    id_grupo_horarios INT,
    id_asignatura_horarios INT,
    id_aula INT,
    UNIQUE (dni_profesor_horarios, id_dia_horarios, id_tramo_horarios),
    FOREIGN KEY (dni_profesor_horarios) REFERENCES Profesores(dni) ON DELETE CASCADE,
    FOREIGN KEY (id_dia_horarios) REFERENCES Dias_Semana(id_dia),
    FOREIGN KEY (id_tramo_horarios) REFERENCES Tramos_Horarios(id_tramo),
    FOREIGN KEY (id_grupo_horarios) REFERENCES Grupos(id_grupo),
    FOREIGN KEY (id_asignatura_horarios) REFERENCES Asignaturas(id_asignatura),
    FOREIGN KEY (id_aula) REFERENCES Aulas(id_aula)
);

/** 
  Tabla Guardias: en esta tabla estamos almacenando las guardias que va a realizar el profesorado.
  La clave primaria es id_guardia, que se genera automáticamente.
  
  - En la tabla se almacenan los siguientes campos:
	  - dni_profesor_guardias: dni del profesor que va a cubrir esa hora y como podemos comprobar es una clave foránea que hace referencia a la tabla Profesores, con borrado en cascada.
      - id_dia_guardias: día de la semana en la cual se va a cubrir la guardia y como podemos comprobar es una clave foránea que hace referencia a la tabla Dias_Semana
      - id_tramo_guardias: el tramo horario en el cual se va a cubrir la guardia y como podemos comprobar es una clave foránea que hace referencia a la tabla Tramos_Horarios
      - id_aula: el aula en la cual va a cubrir la guardia, y como podemos comprobar es una clave foránea que hace referencia a la tabla Aulas
  
  Como he dicho anteriormente pongo una restricción para que un profesor no tenga más de una guardia asignada en el mismo día y tramo horario.
**/

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

/** 
  Tabla Ausencias: en esta tabla estamos almacenando las ausencias de los profesores.
  La clave primaria es id_ausencia, que se genera automáticamente.
  
  - En la tabla se almacenan los siguientes campos:
	 - dni_profesor_ausencias: DNI del profesor o equipo directivo que no se encuentra en el centro y como podemos comprobar es una clave foránea que hace referencia a la tabla Profesores
	 - fecha: fecha en la que el profesor o equipo directivo ha faltado.
	 - id_tramo_ausencias: tramo horario en el que el profesor o equipo directivo ha faltado y como podemos comprobar es una clave foránea que hace referencia a la tabla Tramos_Horarios
	 - motivo: el profesor o equipo directivo aquí pueden indicar el motivo por el cual han faltado.
	 - reincorporado_profesor: cuando un profesor o un miembro del equipo directivo falta puede comunicar su reincorporación que tendrá que ser validada por un miembro del equipo directivo
	 - validacion_direccion: como he dicho anteriormente este campo se realiza la validación final para comprobar que un profesor ya no esta ausente.

   Como he dicho anteriormente pongo una restricción para que un profesor no registre las mismas ausencias en el mismo tramo y en la misma fecha.º
**/

CREATE TABLE Ausencias (
    id_ausencia INT AUTO_INCREMENT PRIMARY KEY,
    dni_profesor_ausencias VARCHAR(9) NOT NULL,
    fecha DATE NOT NULL,
    id_tramo_ausencias INT NOT NULL,
    motivo TEXT,
    reincorporado_profesor BOOLEAN DEFAULT FALSE,
    validacion_direccion BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (dni_profesor_ausencias) REFERENCES Profesores(dni) ON DELETE CASCADE,
    FOREIGN KEY (id_tramo_ausencias) REFERENCES Tramos_Horarios(id_tramo),
    UNIQUE (dni_profesor_ausencias, fecha, id_tramo_ausencias)
);

/** 
  Tabla Incidencias: en esta tabla se recogen todas las incidencias que han surgido durante la guardia.
  La clave primaria es id_incidencia, que se genera automáticamente.
  
  - En la tabla se almacenan los siguientes campos:
	  - id_guardia_incidencias: identificador de la guardia en la que se indica la incidencia por parte del profesorado y como podemos comprobar es una clave foránea que hace referencia a la tabla Guardias .
	  - texto: igual que sucede cuando un profesor se encuentra ausente aquí se indica la información de la incidencia.
	  - timestamp: este campo almacena la hora en la que se comunica la incidencia en tiempo real, es decir la que esta ahora mismo sucediendo.
**/

CREATE TABLE Incidencias (
    id_incidencia INT AUTO_INCREMENT PRIMARY KEY,
    id_guardia_incidencias INT NOT NULL,
    texto TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_guardia_incidencias) REFERENCES Guardias(id_guardia) ON DELETE CASCADE
);

/** 
  Tabla Tareas: en esta tabla se recogen todas las tareas que crean los profesores cuando se encuentran ausentes para que sean realizadas por los alumnos.
  La clave primaria es id_tarea, que se genera automaticamente.

  - En la tabla se almacenan los siguientes campos:
    - id_ausencia_tareas: identificador de la ausencia en la que se indica la tarea por parte del profesorado ausente y como podemos comprobar es una clave foránea que hace referencia a la tabla Ausencias.
    - id_grupo_tareas: identificador del grupo en el que sucede la ausencia por parte del profesorado ausente y como podemos comprobar es una clave foránea que hace referencia a la tabla Grupos.
    - texto: igual que sucede cuando un profesor se encuentra ausente o indica una incidencia se indica la información de la incidencia.
    - archivo: almacena el archivo que puede subir el profesor con la tarea.
**/
CREATE TABLE Tareas (
    id_tarea INT AUTO_INCREMENT PRIMARY KEY,
    id_ausencia_tareas INT NOT NULL,
    id_grupo_tareas INT NOT NULL,
    texto TEXT NOT NULL,
    archivo VARCHAR(255) DEFAULT NULL,
    FOREIGN KEY (id_ausencia_tareas) REFERENCES Ausencias(id_ausencia) ON DELETE CASCADE,
    FOREIGN KEY (id_grupo_tareas) REFERENCES Grupos(id_grupo),
    UNIQUE (id_ausencia_tareas, id_grupo_tareas)
);

/** 
  Tabla Actividades_Extraescolares: en esta tabla se recogen todas las actividades extraescolares programadas que se realizan fuera y dentro del horario escolar y que afectan a un grupo o a varios grupos.
  La clave primaria es id_actividad, que se genera automáticamente.

  - En la tabla se almacenan los siguientes campos:
    - id_grupo_actividades_extraescolares: identificador del grupo al que está asociada la actividad extraescolar. Es una clave foránea que hace referencia a la tabla Grupos.
    - fecha: fecha en la que se realiza la actividad extraescolar.
    - id_tramo_actividades_extraescolares: identificador del tramo horario en el que se desarrolla la actividad. Es una clave foránea que hace referencia a la tabla Tramos_Horarios.
    - dni_profesor_actividades_extraescolares: DNI del profesor responsable o acompañante en la actividad. Es una clave foránea que hace referencia a la tabla Profesores.
    - afecta_grupo_completo: campo booleano que indica si la actividad afecta a todo el grupo (TRUE) o solo a algunos alumnos (FALSE). Por defecto es FALSE.
**/

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
    UNIQUE (id_grupo_actividades_extraescolares, fecha, id_tramo_actividades_extraescolares,dni_profesor_actividades_extraescolares)
);