import axios from 'axios';

// La API corre en el puerto 8000 en tu máquina local
const API_URL = 'http://localhost:8000';

const api = axios.create({
    baseURL: API_URL,
});

// Interceptor: Antes de cada petición, inyecta el Token si existe
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

export default api;