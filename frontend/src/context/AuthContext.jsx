import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import api, { clearAuthStorage } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem('inventai_user');
    return raw ? JSON.parse(raw) : null;
  });
  const [token, setToken] = useState(() => localStorage.getItem('inventai_token'));
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const bootstrap = async () => {
      if (!token) {
        setIsLoading(false);
        return;
      }

      try {
        const me = await api.me();
        setUser(me);
        localStorage.setItem('inventai_user', JSON.stringify(me));
      } catch {
        clearAuthStorage();
        setToken(null);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    bootstrap();
  }, [token]);

  const login = async (googleCredentialResponse) => {
    const credential =
      googleCredentialResponse?.credential
      || googleCredentialResponse?.access_token
      || googleCredentialResponse

    if (!credential) {
      throw new Error('Google sign-in did not return a usable credential.')
    }

    const response = await api.googleAuth(credential);
    localStorage.setItem('inventai_token', response.access_token);
    localStorage.setItem('inventai_user', JSON.stringify(response.user));
    setToken(response.access_token);
    setUser(response.user);
    navigate('/dashboard', { replace: true });
    return response.user;
  };

  const logout = () => {
    clearAuthStorage();
    setToken(null);
    setUser(null);
    navigate('/', { replace: true });
  };

  const value = useMemo(() => ({
    user,
    token,
    isAuthenticated: Boolean(token && user),
    isLoading,
    login,
    logout,
  }), [user, token, isLoading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
