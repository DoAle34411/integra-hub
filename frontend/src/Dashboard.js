import React, { useEffect, useState } from "react";
import api from "./api";
import BrandBar from "./BrandBar";

function Dashboard({ onLogout }) {
  const [orders, setOrders] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [status, setStatus] = useState({ api: "Unknown", worker: "Unknown" });

  // Formulario nuevo pedido
  const [newOrderCustomer, setNewOrderCustomer] = useState("");

  const refreshData = async () => {
    try {
      // 1. Obtener Analítica (reutilizamos esto para la lista porque no hicimos endpoint de lista específico en la API para ahorrar tiempo,
      // pero para la demo mostraremos las métricas y simular la lista en base a eventos si fuera complejo,
      // OJO: En el paso 2 no creamos un endpoint GET /orders (lista).
      // CORRECCIÓN RÁPIDA: Para la demo, usaremos la respuesta de analytics para mostrar números y
      // agregaremos un array local temporal para los pedidos creados en esta sesión,
      // ya que listar todos los pedidos de la DB requiere otro endpoint en FastAPI.)

      const analyticsRes = await api.get("/analytics/dashboard");
      setMetrics(analyticsRes.data);

      // Chequeo de salud simple
      const healthRes = await api.get("/health");
      setStatus({
        api: healthRes.data.status === "healthy" ? "ONLINE" : "DOWN",
      });
    } catch (error) {
      console.error("Error refrescando datos", error);
    }
  };

  // Efecto para polling (refrescar cada 5 segs automáticamente)
  useEffect(() => {
    refreshData();
    const interval = setInterval(refreshData, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleCreateOrder = async () => {
    try {
      const payload = {
        customer_name: newOrderCustomer,
        items: [{ product_id: "demo-prod", quantity: 1, price: 100 }],
      };
      const res = await api.post("/orders", payload);

      // Agregamos a una lista local para mostrar en la UI inmediatamente
      const newOrder = {
        ...res.data,
        status: "PENDING (Processing...)", // Estado inicial visual
      };
      setOrders([newOrder, ...orders]);
      setNewOrderCustomer("");

      // Disparar refresh para actualizar contadores
      setTimeout(refreshData, 1000);
    } catch (error) {
      alert("Error creando pedido: " + error.message);
    }
  };

  return (
    <>
      <BrandBar
        right={
          <button className="btn-udla-outline" onClick={onLogout}>
            Salir
          </button>
        }
      />
      <div className="container mt-4">
        {/* SECCIÓN 1: STATUS & ANALÍTICA */}
        <div className="row mb-4">
          <div className="col-md-3">
            <div className="card card-udla soft-shadow mb-3">
              <div className="card-header">System Status</div>
              <div className="card-body">
                <h5 className="card-title">API: {status.api}</h5>
                <p className="card-text">Database: CONNECTED</p>
              </div>
            </div>
          </div>
          <div className="col-md-3">
            <div className="card card-udla soft-shadow mb-3">
              <div className="card-header">Total Ventas</div>
              <div className="card-body">
                <h5 className="card-title">${metrics?.total_sales || 0}</h5>
              </div>
            </div>
          </div>
          <div className="col-md-3">
            <div className="card card-udla soft-shadow mb-3">
              <div className="card-header">Pedidos Totales</div>
              <div className="card-body">
                <h5 className="card-title">{metrics?.total_orders || 0}</h5>
              </div>
            </div>
          </div>
        </div>

        {/* SECCIÓN 2: OPERACIONES */}
        <div className="row">
          {/* Formulario de Creación */}
          <div className="col-md-4">
            <div className="card card-udla soft-shadow">
              <div className="card-header">Nuevo Pedido</div>
              <div className="card-body">
                <div className="mb-3">
                  <label>Cliente</label>
                  <input
                    className="form-control"
                    placeholder="Nombre Cliente"
                    value={newOrderCustomer}
                    onChange={(e) => setNewOrderCustomer(e.target.value)}
                  />
                  <small className="text-muted">
                    Usa "ERROR" para probar fallos.
                  </small>
                </div>
                <button
                  className="btn btn-udla w-100"
                  onClick={handleCreateOrder}
                >
                  Crear Pedido (E2E)
                </button>
              </div>
            </div>
          </div>

          {/* Lista de Pedidos (Tracking) */}
          <div className="col-md-8">
            <h3 className="text-udla">Últimos Pedidos (Sesión Actual)</h3>
            <table className="table table-striped">
              <thead>
                <tr>
                  <th>Order UUID (Correlation ID)</th>
                  <th>Cliente</th>
                  <th>Total</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((o) => (
                  <tr key={o.order_uuid}>
                    <td>
                      <small>{o.order_uuid}</small>
                    </td>
                    <td>{o.customer_name}</td>
                    <td>${o.total_amount}</td>
                    <td>
                      <span
                        className={
                          o.customer_name.includes("ERROR")
                            ? "badge bg-danger"
                            : "badge badge-udla"
                        }
                      >
                        {o.customer_name.includes("ERROR")
                          ? "FAILED (DLQ)"
                          : "SENT TO QUEUE"}
                      </span>
                    </td>
                  </tr>
                ))}
                {orders.length === 0 && (
                  <tr>
                    <td colSpan="4">No hay pedidos nuevos en esta sesión.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  );
}

export default Dashboard;
