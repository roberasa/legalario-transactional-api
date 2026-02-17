# legalario-transactional-api

Backend desarrollado con **FastAPI** que implementa:

- API transaccional (síncrona y asíncrona)
- Idempotencia mediante header
- WebSocket para actualizaciones en tiempo real
- Integración con OpenAI para generación de resúmenes
- Persistencia con SQLAlchemy
- Automatización (RPA) integrada

---

## 🏗 Arquitectura

El proyecto está diseñado bajo principios de:

- Separación de responsabilidades
- Desacoplamiento de integraciones externas
- Preparación para escalabilidad
- Enfoque event-driven (extensible a Kafka/Redis)

Estructura principal:

src/
├── main.py # Entrypoint principal
├── database.py # Configuración de base de datos
├── models.py # Modelos ORM
├── schemas.py # Esquemas Pydantic

## 1. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux / Mac
venv\Scripts\activate     # Windows

## 2. Instalar dependencias
pip install -r requirements.txt

## 3. Configurar variables de entorno
export OPENAI_API_KEY=tu_api_key

## 4. Ejecutar servidor
python -m uvicorn src.main:app --reload

Servidor disponible en:

http://localhost:8000

Documentación automática:

http://localhost:8000/docs

🗄 Base de datos

Actualmente utiliza SQLite para entorno local.

Está preparado para migrarse fácilmente a:

PostgreSQL

MySQL

Solo sería necesario cambiar la cadena de conexión en database.py.

🤖 RPA

El proyecto incluye un script:

rpa.py


Funcionalidad:

Abre Wikipedia

Busca un término

Extrae el primer párrafo

Envía el contenido al endpoint /assistant/summarize

Ejecutar:

python rpa.py



