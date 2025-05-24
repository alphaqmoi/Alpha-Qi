import { useState, useCallback, useEffect } from 'react';
import { useToast } from '@/components/ui/use-toast';

interface User {
  id: string;
  email: string;
  name: string;
  token: string;
  role: 'user' | 'admin';
  created_at: string;
  updated_at: string;
}

interface UseAuthReturn {
  user: User | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  updateProfile: (data: Partial<User>) => Promise<void>;
}

export function useAuth(): UseAuthReturn {
  const { toast } = useToast();
  
  // State
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Check auth status on mount
  useEffect(() => {
    checkAuth();
  }, []);
  
  // Check authentication status
  const checkAuth = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        setUser(null);
        return;
      }
      
      const response = await fetch('/api/auth/me', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      const data = await response.json();
      if (data.status === 'success') {
        setUser({
          ...data.user,
          token
        });
      } else {
        throw new Error(data.message);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to check authentication';
      setError(message);
      setUser(null);
      localStorage.removeItem('token');
    } finally {
      setLoading(false);
    }
  }, []);
  
  // Login
  const login = useCallback(async (email: string, password: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email, password })
      });
      
      const data = await response.json();
      if (data.status === 'success') {
        const { token, user } = data;
        localStorage.setItem('token', token);
        setUser({
          ...user,
          token
        });
      } else {
        throw new Error(data.message);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to login';
      setError(message);
      toast({
        title: 'Error',
        description: message,
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);
  
  // Logout
  const logout = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      if (user?.token) {
        await fetch('/api/auth/logout', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${user.token}`
          }
        });
      }
    } catch (err) {
      console.error('Error during logout:', err);
    } finally {
      localStorage.removeItem('token');
      setUser(null);
      setLoading(false);
    }
  }, [user]);
  
  // Register
  const register = useCallback(async (email: string, password: string, name: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email, password, name })
      });
      
      const data = await response.json();
      if (data.status === 'success') {
        const { token, user } = data;
        localStorage.setItem('token', token);
        setUser({
          ...user,
          token
        });
      } else {
        throw new Error(data.message);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to register';
      setError(message);
      toast({
        title: 'Error',
        description: message,
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);
  
  // Update profile
  const updateProfile = useCallback(async (data: Partial<User>) => {
    if (!user) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/auth/profile', {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user.token}`
        },
        body: JSON.stringify(data)
      });
      
      const responseData = await response.json();
      if (responseData.status === 'success') {
        setUser(prev => prev ? {
          ...prev,
          ...responseData.user
        } : null);
      } else {
        throw new Error(responseData.message);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update profile';
      setError(message);
      toast({
        title: 'Error',
        description: message,
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  }, [user, toast]);
  
  return {
    user,
    loading,
    error,
    login,
    logout,
    register,
    updateProfile
  };
} 