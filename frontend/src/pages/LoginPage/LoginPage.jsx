import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import './LoginPage.css';

function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const { login } = useAuth();

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');

    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    try {
      const response = await fetch('/token', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        login(data.access_token);
        // Redirect to the main page or dashboard
        navigate('/');
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to login. Please check your credentials.');
      }
    } catch (err) {
      setError('An error occurred. Please try again later.');
    }
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <h2>SMC Login</h2>
        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <label htmlFor="username">Username or Email</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>
          <div className="input-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          {error && <p className="error-message">{error}</p>}
          <button type="submit" className="login-button">Login</button>
          <div className="register-link-container">
            계정이 없으신가요? <Link to="/register" className="register-link">회원가입</Link>
          </div>
        </form>
      </div>
    </div>
  );
}

export default LoginPage;
