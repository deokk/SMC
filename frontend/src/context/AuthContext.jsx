import React, { createContext, useState, useContext, useEffect } from 'react';
import { jwtDecode } from 'jwt-decode'; // Import jwtDecode

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('accessToken'));
  const [username, setUsername] = useState(null);

  // Function to decode token and extract username
  const decodeToken = (jwtToken) => {
    try {
      const decoded = jwtDecode(jwtToken);
      return decoded.sub; // Assuming 'sub' claim holds the username
    } catch (error) {
      console.error("Failed to decode token:", error);
      return null;
    }
  };

  useEffect(() => {
    // Initialize username from token if available
    if (token) {
      setUsername(decodeToken(token));
    } else {
      setUsername(null);
    }
    
    // This effect ensures that the state is updated if localStorage changes from another tab.
    const handleStorageChange = () => {
      const newToken = localStorage.getItem('accessToken');
      setToken(newToken);
      setUsername(newToken ? decodeToken(newToken) : null);
    };
    window.addEventListener('storage', handleStorageChange);
    return () => {
      window.removeEventListener('storage', handleStorageChange);
    };
  }, [token]);

  const login = (newToken) => {
    localStorage.setItem('accessToken', newToken);
    setToken(newToken);
    setUsername(decodeToken(newToken)); // Update username after login
  };

  const logout = () => {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('username'); // Also remove username
    setToken(null);
    setUsername(null);
  };

  const isAuthenticated = !!token;

  return (
    <AuthContext.Provider value={{ isAuthenticated, token, username, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  return useContext(AuthContext);
};
