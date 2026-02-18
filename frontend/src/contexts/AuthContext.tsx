import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { login as apiLogin, getMe } from '../services/api';

interface User {
  user_id: string;
  username: string;
  display_name: string;
  email?: string | null;
  role: string;
  subsidiary_id: string | null;
  permissions: string[];
  scope: 'global' | 'subsidiary';
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  /** Check if the current user has a specific permission */
  can: (permission: string) => boolean;
  /** Check if the current user has ANY of the listed permissions */
  canAny: (...permissions: string[]) => boolean;
  /** Check if the current user has ALL of the listed permissions */
  canAll: (...permissions: string[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      getMe()
        .then((res) => {
          const data = res.data;
          setUser({
            user_id: data.user_id,
            username: data.username,
            display_name: data.display_name || data.username,
            email: data.email,
            role: data.role,
            subsidiary_id: data.subsidiary_id,
            permissions: data.permissions || [],
            scope: data.scope || 'subsidiary',
          });
          localStorage.setItem('user', JSON.stringify(data));
        })
        .catch(() => {
          setToken(null);
          setUser(null);
          localStorage.removeItem('token');
          localStorage.removeItem('user');
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [token]);

  const login = async (username: string, password: string) => {
    const res = await apiLogin(username, password);
    const { access_token, user: userData } = res.data;
    localStorage.setItem('token', access_token);
    localStorage.setItem('user', JSON.stringify(userData));
    setToken(access_token);
    setUser({
      user_id: userData.id || userData.user_id,
      username: userData.username,
      display_name: userData.display_name || userData.username,
      email: userData.email,
      role: userData.role,
      subsidiary_id: userData.subsidiary_id,
      permissions: userData.permissions || [],
      scope: userData.scope || 'subsidiary',
    });
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
  };

  const can = useCallback(
    (permission: string): boolean => {
      return user?.permissions?.includes(permission) ?? false;
    },
    [user],
  );

  const canAny = useCallback(
    (...permissions: string[]): boolean => {
      return permissions.some((p) => user?.permissions?.includes(p) ?? false);
    },
    [user],
  );

  const canAll = useCallback(
    (...permissions: string[]): boolean => {
      return permissions.every((p) => user?.permissions?.includes(p) ?? false);
    },
    [user],
  );

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        login,
        logout,
        can,
        canAny,
        canAll,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
