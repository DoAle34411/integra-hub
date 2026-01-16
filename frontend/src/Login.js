import React, { useState } from 'react';
import api from './api';

function Login({ onLogin }) {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            // FormData es necesario porque OAuth2 espera form-data, no JSON
            const formData = new FormData();
            formData.append('username', username);
            formData.append('password', password);

            const response = await api.post('/token', formData);
            localStorage.setItem('token', response.data.access_token);
            onLogin(); // Notificar al padre que ya entramos
        } catch (err) {
            setError('Credenciales inválidas (Prueba: admin / admin123)');
        }
    };

    return (
        <div className="container mt-5" style={{ maxWidth: '400px' }}>
            <div className="card shadow">
                <div className="card-body">
                    <h3 className="card-title text-center">IntegraHub Login</h3>
                    {error && <div className="alert alert-danger">{error}</div>}
                    <form onSubmit={handleSubmit}>
                        <div className="mb-3">
                            <label>Usuario</label>
                            <input className="form-control" value={username} onChange={e => setUsername(e.target.value)} />
                        </div>
                        <div className="mb-3">
                            <label>Password</label>
                            <input type="password" className="form-control" value={password} onChange={e => setPassword(e.target.value)} />
                        </div>
                        <button type="submit" className="btn btn-primary w-100">Ingresar</button>
                    </form>
                    <div className="mt-3 text-muted text-center small">
                        Hint: admin / admin123
                    </div>
                </div>
            </div>
        </div>
    );
}

export default Login;