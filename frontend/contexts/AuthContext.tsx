import React, { createContext, useContext } from 'react';
import { useAuth, User, Child } from '../hooks/useAuth';

interface AuthContextType {
  user: User | null;
  token: string | null;
  children: Child[];
  activeChild: Child | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  register: (name: string, email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
  addChild: (name: string, ageTier: string, voiceId?: string) => Promise<{ success: boolean; child?: Child; error?: string }>;
  setActiveChild: (child: Child) => Promise<void>;
  refreshChildren: () => Promise<void>;
  updateChildVoice: (childId: string, voiceId: string) => Promise<{ success: boolean; error?: string }>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const auth = useAuth();
  return <AuthContext.Provider value={auth}>{children}</AuthContext.Provider>;
}

export function useAuthContext() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuthContext must be inside AuthProvider');
  return ctx;
}
