import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';

export type Role = 'sonologist' | 'expert_reviewer' | 'admin';

export type User = {
  id: number;
  full_name: string;
  email: string;
  username: string;
  role: Role;
};

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  login: (identifier: string, password: string, role: Role) => Promise<User>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = sessionStorage.getItem('supernova_token');
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .get<User>('/auth/me')
      .then((response) => setUser(response.data))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      async login(identifier, password, role) {
        const response = await api.post<{ access_token: string; user: User }>('/auth/login', { identifier, password, role });
        sessionStorage.setItem('supernova_token', response.data.access_token);
        setUser(response.data.user);
        return response.data.user;
      },
      async logout() {
        try {
          await api.post('/auth/logout');
        } finally {
          sessionStorage.removeItem('supernova_token');
          setUser(null);
        }
      },
    }),
    [user, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return context;
}
