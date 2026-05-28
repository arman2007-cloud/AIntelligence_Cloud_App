# AIntelligence - Cloud App y Panel Web

## Descripción del Proyecto
Esta plataforma constituye el núcleo centralizado del sistema AIntelligence. Actúa como un panel de control web encargado de la gestión de usuarios, la persistencia de datos relacionales, la orquestación de tareas asíncronas en segundo plano y la distribución dinámica del agente de automatización local. El sistema está diseñado para operar en un entorno de producción basado en Linux, administrado mediante contenedores de Docker.

## Arquitectura y Componentes Tecnológicos
El backend está desarrollado sobre un framework web de Python, lo que permite gestionar tanto las peticiones HTTP del panel de usuario como los endpoints de la API consumidos por los agentes remotos.

* **Base de Datos:** PostgreSQL se utiliza como motor relacional para el almacenamiento de leads, configuraciones de usuarios y registros del sistema.
* **Procesamiento de Tareas:** Celery se encarga de la ejecución de procesos asíncronos y pesados en segundo plano, evitando el bloqueo del hilo principal de la aplicación web.
* **Broker de Mensajes:** Se emplea Redis (alojado en Upstash de forma gestionada con soporte SSL) como canal de comunicación y almacenamiento de resultados para Celery.
* **Integraciones Externas:** El sistema se comunica con flujos automatizados en N8N mediante webhooks específicos y procesa peticiones de inteligencia artificial utilizando los de modelos de lenguaje de Google Gemini.

## Configuración del Archivo de Entorno (.env)
La aplicación depende de un archivo de configuración física denominado `.env` ubicado en la raíz del proyecto. Este archivo está excluido del control de versiones por motivos de seguridad. Para nuevos despliegues, se debe duplicar el archivo `.env.example`, renombrarlo a `.env` y completar los siguientes parámetros:

* `DATABASE_URL`: Cadena de conexión completa al servidor PostgreSQL.
* `REDIS_URL` / `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND`: Dirección de conexión segura (rediss://) provista por el proveedor de Redis (Upstash) incluyendo credenciales y el parámetro de validación SSL.
* `SECRET_KEY`: Clave criptográfica utilizada para cifrar las sesiones de los usuarios en el navegador.
* `ADMIN_SETUP_PASSWORD`: Contraseña maestra requerida para la inicialización y configuración de roles de administración.
* `WORKER_API_KEY`: Token de seguridad utilizado para validar la comunicación legítima entre el bot local y la API de la nube.
* `API_BASE_URL`: URL absoluta del punto de acceso de la API en el servidor de producción.
* `GEMINI_API_KEY`: Clave de acceso oficial para el consumo de modelos fundacionales en Google AI Studio.
* `N8N_WEBHOOK_URL`: Dirección URL del webhook configurado en la instancia de N8N para el procesamiento de leads.
* `N8N_API_KEY`: Credencial de autenticación para interactuar de forma segura con la API interna de N8N.
* `DRIVE_FOLDER_ID`: Identificador alfanumérico único de la carpeta de Google Drive donde se depositan los informes finales.

## Despliegue del Agente de Automatización (Carpeta bot_releases)
El panel web cuenta con una funcionalidad que permite a los usuarios autorizados descargar el ejecutable del bot ya empaquetado. Para que este flujo funcione sin errores del lado del servidor, es de carácter obligatorio configurar la estructura manual en el entorno de producción:

1. Crear un directorio en la raíz del proyecto en el servidor denominado exactamente `bot_releases`.
2. Depositar dentro de dicha carpeta el archivo compilado ejecutable bajo el nombre `AIntelligence_Bot.exe`.
3. Depositar el archivo de configuración `credentials.json` obtenido de la consola de Google Cloud, el cual es necesario para que el bot gestione sus conexiones con las API de Google tras ser descargado.

Al estar este directorio fuera del control de versiones Git, las actualizaciones de código web no sobrescribirán ni eliminarán estos archivos binarios del servidor.

## Mantenimiento y Actualizaciones en el Servidor (Docker)
Toda la infraestructura de la aplicación web y sus servicios en segundo plano está contenerizada. Si se realiza cualquier modificación en el código fuente (pull desde GitHub), se cambian las variables de entorno o se instalan nuevas dependencias, es obligatorio reconstruir los contenedores.

Para aplicar los cambios de manera segura, se debe acceder al servidor a través de SSH (o desde la terminal integrada del panel) y ejecutar los siguientes comandos en el directorio raíz del proyecto:

```bash
# 1. Detener y eliminar los contenedores actuales de forma segura
docker compose down

# 2. Reconstruir las imágenes con el nuevo código y levantar el sistema
docker compose up -d --build
