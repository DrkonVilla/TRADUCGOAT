import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Batch(Base):
    __tablename__ = "batches"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    idioma_origen = Column(String(50), default="auto")
    idioma_destino = Column(String(50), default="Español")
    estado = Column(String(20), default="PENDIENTE")  # PENDIENTE, EN_PROGRESO, COMPLETADO, FALLIDO

    # Relación con archivos
    archivos = relationship("Archivo", back_populates="batch", cascade="all, delete-orphan")

class Archivo(Base):
    __tablename__ = "archivos"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    batch_id = Column(String(36), ForeignKey("batches.id"), nullable=False)
    nombre_original = Column(String(255), nullable=False)
    nombre_traducido = Column(String(255), nullable=True)
    texto_original = Column(Text, nullable=True)
    texto_traducido = Column(Text, nullable=True)
    estado = Column(String(20), default="PENDIENTE")  # PENDIENTE, PROCESANDO, COMPLETADO, FALLIDO
    tiempo_procesamiento = Column(Float, default=0.0)
    num_caracteres = Column(Integer, default=0)
    logs_agente = Column(Text, default="[]")  # Almacena una lista de logs formateada en JSON

    batch = relationship("Batch", back_populates="archivos")
