"""
Transactional API - Main Entrypoint

Este archivo es el corazón del backend.
Aquí inicializo la aplicación, configuro integraciones externas
y defino todos los endpoints del sistema.

Incluye:
- Transacciones síncronas y asíncronas
- Notificaciones en tiempo real con WebSockets
- Integración con OpenAI para generar resúmenes
"""

# ==============================
# IMPORTS BÁSICOS
# ==============================

import os  # Para leer variables de entorno (como la API key)
import asyncio  # Para simular procesamiento asíncrono
from typing import List  # Tipado fuerte para listas


# ==============================
# IMPORTS DE FASTAPI
# ==============================

from fastapi import (
    FastAPI,              # Clase principal para crear la app
    Header,               # Para leer headers HTTP (usado en idempotencia)
    Depends,              # Inyección de dependencias (DB session)
    BackgroundTasks,      # Ejecutar tareas en background
    HTTPException,        # Manejo de errores HTTP
    WebSocket,            # Manejo de WebSockets
    WebSocketDisconnect,  # Manejo de desconexiones
)

from fastapi.middleware.cors import CORSMiddleware  # Permite conexión frontend-backend

from sqlalchemy.orm import Session  # Tipo para sesiones de base de datos

from openai import OpenAI  # Cliente oficial de OpenAI


# ==============================
# IMPORTS INTERNOS DEL PROYECTO
# ==============================

from src.database import engine, SessionLocal  # Conexión a BD
from src.models import Transaction, SummaryRequest  # Modelos ORM
from src.schemas import (
    TransactionCreate,
    TransactionResponse,
    SummaryCreate,
    SummaryResponse,
)


# ==============================================================================
# OPENAI CLIENT
# ==============================================================================

# Leo la API key desde variable de entorno por seguridad
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Si no existe la key, detengo la aplicación.
# Esto evita que el sistema arranque en estado inválido.
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set in environment variables.")

# Inicializo el cliente de OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)


def open_ai(text: str) -> str:
    """
    Esta función encapsula la integración con OpenAI.
    Mantiene desacoplado el proveedor externo del resto del sistema.
    """

    try:
        # Hago una llamada al modelo de OpenAI
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                # Mensaje de sistema: define comportamiento del modelo
                {
                    "role": "system",
                    "content": "You are an assistant that summarizes text clearly and concisely."
                },
                # Mensaje del usuario: el texto que queremos resumir
                {
                    "role": "user",
                    "content": f"Summarize the following text:\n\n{text}"
                }
            ],
            temperature=0.3,  # Controla creatividad (bajo = más preciso)
        )

        # Extraigo el texto generado por el modelo
        return response.choices[0].message.content

    except Exception as e:
        # Si falla OpenAI, convierto el error en error HTTP controlado
        raise HTTPException(status_code=500, detail=f"OpenAI error: {str(e)}")


# ==============================================================================
# APPLICATION INITIALIZATION
# ==============================================================================

# Creo la aplicación FastAPI
app = FastAPI(title="Transactional API")

# Configuración de CORS para permitir comunicación con el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Origen permitido
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Creo tablas automáticamente en entorno demo
# En producción esto normalmente lo manejaría con migraciones.
Transaction.metadata.create_all(bind=engine)
SummaryRequest.metadata.create_all(bind=engine)


# ==============================================================================
# WEBSOCKET CONNECTION MANAGER
# ==============================================================================

class ConnectionManager:
    """
    Maneja múltiples conexiones WebSocket activas.
    Permite enviar mensajes en tiempo real a todos los clientes conectados.
    """

    def __init__(self):
        # Lista de conexiones activas
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        # Acepta conexión WebSocket
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        # Remueve conexión cuando cliente se desconecta
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        # Envía mensaje a todos los clientes conectados
        for connection in self.active_connections:
            await connection.send_json(message)


# Instancia global del manager
manager = ConnectionManager()


# ==============================================================================
# DATABASE DEPENDENCY
# ==============================================================================

def get_db():
    """
    Maneja el ciclo de vida de la sesión de base de datos.
    Se crea por request y se cierra automáticamente.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==============================================================================
# BACKGROUND WORKER (ASYNC SIMULATION)
# ==============================================================================

async def process_transaction(transaction_id: str):
    """
    Simula procesamiento asíncrono.
    En producción esto sería reemplazado por Redis o RabbitMQ.
    """
    db = SessionLocal()
    try:
        # Busco la transacción en BD
        transaction = db.query(Transaction).filter(
            Transaction.id == transaction_id
        ).first()

        if not transaction:
            return

        # Simulo tiempo de procesamiento
        await asyncio.sleep(5)

        try:
            # Si todo sale bien → estado procesado
            transaction.status = "procesado"
            db.commit()
            db.refresh(transaction)

            # Notifico a todos los clientes conectados
            await manager.broadcast({
                "transaction_id": transaction.id,
                "status": transaction.status
            })

        except Exception:
            # Si falla → estado fallido
            transaction.status = "fallido"
            db.commit()
            db.refresh(transaction)

            await manager.broadcast({
                "transaction_id": transaction.id,
                "status": transaction.status
            })

    finally:
        db.close()


# ==============================================================================
# HEALTH CHECK
# ==============================================================================

@app.get("/")
def root():
    # Endpoint simple para verificar que la API está viva
    return {"message": "API running"}


# ==============================================================================
# TRANSACTION ENDPOINTS
# ==============================================================================

@app.get("/transactions", response_model=List[TransactionResponse])
def list_transactions(db: Session = Depends(get_db)):
    # Devuelve todas las transacciones ordenadas por fecha
    return db.query(Transaction).order_by(
        Transaction.created_at.desc()
    ).all()


@app.post("/transactions/create", response_model=TransactionResponse)
def create_transaction(
    transaction: TransactionCreate,
    idempotency_key: str = Header(...),  # Header obligatorio
    db: Session = Depends(get_db)
):
    # Verifico si ya existe una transacción con ese idempotency key
    existing = db.query(Transaction).filter(
        Transaction.idempotency_key == idempotency_key
    ).first()

    # Si ya existe, la devuelvo (idempotencia)
    if existing:
        return existing

    # Si no existe, creo una nueva
    new_transaction = Transaction(
        user_id=transaction.user_id,
        amount=transaction.amount,
        type=transaction.type,
        status="pendiente",
        idempotency_key=idempotency_key
    )

    db.add(new_transaction)
    db.commit()
    db.refresh(new_transaction)

    return new_transaction


@app.post("/transactions/async-process", response_model=TransactionResponse)
def async_process_transaction(
    transaction: TransactionCreate,
    background_tasks: BackgroundTasks,
    idempotency_key: str = Header(...),
    db: Session = Depends(get_db)
):
    # Verifico idempotencia
    existing = db.query(Transaction).filter(
        Transaction.idempotency_key == idempotency_key
    ).first()

    if existing:
        return existing

    # Creo transacción en estado pendiente
    new_transaction = Transaction(
        user_id=transaction.user_id,
        amount=transaction.amount,
        type=transaction.type,
        status="pendiente",
        idempotency_key=idempotency_key
    )

    db.add(new_transaction)
    db.commit()
    db.refresh(new_transaction)

    # Lanzo procesamiento en background
    background_tasks.add_task(
        lambda: asyncio.run(process_transaction(new_transaction.id))
    )

    return new_transaction


@app.get("/transactions/{transaction_id}", response_model=TransactionResponse)
def get_transaction(transaction_id: str, db: Session = Depends(get_db)):
    # Obtengo una transacción por ID
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return transaction


# ==============================================================================
# AI ASSISTANT ENDPOINT
# ==============================================================================

@app.post("/assistant/summarize", response_model=SummaryResponse)
def summarize_text(payload: SummaryCreate, db: Session = Depends(get_db)):
    # Llamo a OpenAI para generar resumen
    summary = open_ai(payload.text)

    # Persisto tanto el texto original como el resumen
    record = SummaryRequest(
        input_text=payload.text,
        output_summary=summary
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return record


# ==============================================================================
# WEBSOCKET STREAM
# ==============================================================================

@app.websocket("/transactions/stream")
async def transaction_stream(websocket: WebSocket):
    # Cliente se conecta
    await manager.connect(websocket)
    try:
        while True:
            # Mantengo la conexión viva
            await websocket.receive_text()
    except WebSocketDisconnect:
        # Cliente se desconecta
        manager.disconnect(websocket)
