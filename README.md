# 🚀 IntegraHub - Plataforma de Integración Empresarial

**IntegraHub** es una solución de arquitectura orientada a servicios diseñada para gestionar el ciclo de vida de pedidos (Order-to-Cash), integrando canales modernos (Web/API) con sistemas legados (Archivos CSV) y notificaciones asíncronas.

Este proyecto implementa patrones de integración empresarial como **Point-to-Point**, **Pub/Sub**, **Dead Letter Channel (DLQ)** y **Idempotent Consumer**.

---

## 📋 Arquitectura del Sistema

El sistema corre 100% contenerizado sobre Docker y consta de los siguientes microservicios:

* **Frontend (Demo Portal):** React + Nginx (Puerto 3000).
* **Backend (Orders API):** FastAPI con OAuth2/JWT (Puerto 8000).
* **Message Broker:** RabbitMQ para mensajería asíncrona (Puerto 5672/15672).
* **Inventory Worker:** Consumidor resiliente con Reintentos y DLQ.
* **Notification Service:** Suscriptor de eventos (Fanout) para alertas.
* **Legacy Service:** Proceso Batch que ingesta archivos CSV.
* **Database:** PostgreSQL (Persistencia).

---

## 🛠️ Requisitos Previos

* **Docker Desktop** instalado y corriendo.
* **Git** (opcional, para clonar).

-------

## 🚀 Inicialización (Quick Start)

Sigue estos pasos para levantar el entorno completo para la demostración:

### 1. Levantar el Sistema
Ejecuta el siguiente comando en la raíz del proyecto (donde está el `docker-compose.yml`):

```bash
docker compose up -d --build

