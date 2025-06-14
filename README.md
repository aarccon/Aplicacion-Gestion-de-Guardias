# Aplicacion-Gestion-de-Guardias
Proyecto Final de Antonio Arcediano Consuegra

# 📚 Aplicación de Gestión de Guardias - IES Ciudad Jardín

Plataforma web desarrollada en Flask para gestionar **ausencias, guardias, tareas** y **actividades extraescolares** en el IES Ciudad Jardín.

---

## 🚀 Instalación y Despliegue

La aplicación ha sido diseñada para funcionar tanto en entorno local como en producción. Está basada en **Flask** y **MySQL**, con integración opcional de **MongoDB** para el sistema de mensajería.

---

### ✅ 1. Instalación en local

#### Requisitos previos:
- Python 3.10 o superior  
- MySQL Server (o XAMPP)  
- MongoDB (opcional)  
- `pip` y `virtualenv`  
- Editor de código (VS Code recomendado)

#### Pasos:
```bash
git clone https://github.com/aarccon/Aplicacion-Gestion-de-Guardias.git
cd Aplicacion-Gestion-de-Guardias
python -m venv venv
venv\Scripts\activate   # En Windows
pip install -r requirements.txt
```

#### Crear archivo `.env`:
```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=tu_contraseña
DB_NAME=Proyecto_Final
MONGO_URI=mongodb://localhost:27017/
SECRET_KEY=clave_super_secreta
```

#### Ejecutar app:
```bash
flask run
```
Accede desde: [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

### 🔧 2. Despliegue con Waitress (entorno de producción)

1. Añadir al final de `app.py`:
```python
from waitress import serve

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=8080)
```

2. Ejecutar:
```bash
python app.py
```

3. Accede desde la red local: `http://localhost:8080`

---

### 🌐 3. Cloudflare Tunnel (acceso remoto)

1. Instalar desde la [guía oficial](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation)

2. Ejecutar:
```bash
cloudflared tunnel --url http://localhost:8080
```

3. Se generará una URL pública como:  
👉 `https://miapp.trycloudflare.com`

---

### ⚙️ 4. Configuraciones necesarias

#### `.env`:
```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=tu_contraseña
DB_NAME=Proyecto_Final
MONGO_URI=mongodb://localhost:27017/
SECRET_KEY=clave_super_secreta
```

#### Estructura de carpetas:
```
static/
├── archivos_tareas/
├── img/
├── css/
```

#### Usuarios iniciales:
- Crear manualmente o mediante CSV un usuario con perfil **Dirección**.

---