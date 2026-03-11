import { useState, useEffect, useCallback } from 'react';
import { storage } from '../helpers/storage';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

export interface User {
  user_id: string;
  email: string;
  name: string;
  picture?: string;
}

export interface Child {
  child_id: string;
  parent_id: string;
  name: string;
  age_tier: string;
  avatar?: string;
  preferred_translation: string;
  parental_consent_given: boolean;
}

interface AuthState {
  user: User | null;
  token: string | null;
  children: Child[];
  activeChild: Child | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    user: null,
    token: null,
    children: [],
    activeChild: null,
    isLoading: true,
    isAuthenticated: false,
  });

  const getHeaders = useCallback((token: string) => ({
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  }), []);

  const fetchChildren = useCallback(async (token: string): Promise<Child[]> => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/children`, {
        headers: getHeaders(token),
      });
      if (res.ok) {
        const data = await res.json();
        return data.children || [];
      }
    } catch (e) {
      console.log('Fetch children error:', e);
    }
    return [];
  }, [getHeaders]);

  // Load saved auth on mount
  useEffect(() => {
    loadAuth();
  }, []);

  const loadAuth = async () => {
    try {
      const token = await storage.getItem('authToken');
      const userData = await storage.getItem('authUser');
      if (!token || !userData) {
        setState(s => ({ ...s, isLoading: false }));
        return;
      }

      const user: User = JSON.parse(userData);
      
      // Validate token is still valid
      const res = await fetch(`${BACKEND_URL}/api/auth/me`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      
      if (!res.ok) {
        // Token expired - clear auth
        await clearAuth();
        return;
      }

      const children = await fetchChildren(token);
      const savedActiveId = await storage.getItem('activeChildId');
      const activeChild = children.find(c => c.child_id === savedActiveId) || children[0] || null;

      setState({
        user,
        token,
        children,
        activeChild,
        isLoading: false,
        isAuthenticated: true,
      });
    } catch {
      setState(s => ({ ...s, isLoading: false }));
    }
  };

  const clearAuth = async () => {
    await storage.removeItem('authToken');
    await storage.removeItem('authUser');
    await storage.removeItem('activeChildId');
    setState({
      user: null,
      token: null,
      children: [],
      activeChild: null,
      isLoading: false,
      isAuthenticated: false,
    });
  };

  const login = async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        const err = await res.json();
        return { success: false, error: err.detail || 'Login failed' };
      }

      const data = await res.json();
      const user: User = { user_id: data.user_id, email: data.email, name: data.name };
      
      await storage.setItem('authToken', data.token);
      await storage.setItem('authUser', JSON.stringify(user));

      const children = await fetchChildren(data.token);
      const activeChild = children[0] || null;
      if (activeChild) {
        await storage.setItem('activeChildId', activeChild.child_id);
        await storage.setItem('childId', activeChild.child_id);
        await storage.setItem('ageTier', activeChild.age_tier);
      }

      setState({
        user,
        token: data.token,
        children,
        activeChild,
        isLoading: false,
        isAuthenticated: true,
      });

      return { success: true };
    } catch {
      return { success: false, error: 'Network error. Please try again.' };
    }
  };

  const register = async (name: string, email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, password }),
      });

      if (!res.ok) {
        const err = await res.json();
        return { success: false, error: err.detail || 'Registration failed' };
      }

      const data = await res.json();
      const user: User = { user_id: data.user_id, email: data.email, name: data.name };
      
      await storage.setItem('authToken', data.token);
      await storage.setItem('authUser', JSON.stringify(user));

      setState({
        user,
        token: data.token,
        children: [],
        activeChild: null,
        isLoading: false,
        isAuthenticated: true,
      });

      return { success: true };
    } catch {
      return { success: false, error: 'Network error. Please try again.' };
    }
  };

  const logout = async () => {
    if (state.token) {
      try {
        await fetch(`${BACKEND_URL}/api/auth/logout`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${state.token}` },
        });
      } catch {}
    }
    await clearAuth();
  };

  const addChild = async (name: string, ageTier: string): Promise<{ success: boolean; child?: Child; error?: string }> => {
    if (!state.token) return { success: false, error: 'Not authenticated' };
    try {
      const res = await fetch(`${BACKEND_URL}/api/children`, {
        method: 'POST',
        headers: getHeaders(state.token),
        body: JSON.stringify({ name, age_tier: ageTier }),
      });

      if (!res.ok) {
        const err = await res.json();
        return { success: false, error: err.detail || 'Failed to create profile' };
      }

      const child: Child = await res.json();
      const newChildren = [...state.children, child];
      
      await storage.setItem('activeChildId', child.child_id);
      await storage.setItem('childId', child.child_id);
      await storage.setItem('ageTier', child.age_tier);

      setState(s => ({
        ...s,
        children: newChildren,
        activeChild: child,
      }));

      return { success: true, child };
    } catch {
      return { success: false, error: 'Network error' };
    }
  };

  const setActiveChild = async (child: Child) => {
    await storage.setItem('activeChildId', child.child_id);
    await storage.setItem('childId', child.child_id);
    await storage.setItem('ageTier', child.age_tier);
    setState(s => ({ ...s, activeChild: child }));
  };

  const refreshChildren = async () => {
    if (!state.token) return;
    const children = await fetchChildren(state.token);
    const activeChild = children.find(c => c.child_id === state.activeChild?.child_id) || children[0] || null;
    setState(s => ({ ...s, children, activeChild }));
  };

  return {
    ...state,
    login,
    register,
    logout,
    addChild,
    setActiveChild,
    refreshChildren,
  };
}
