import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as WebBrowser from 'expo-web-browser';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;
const GOOGLE_AUTH_URL = 'https://demobackend.emergentagent.com/auth/v1/google?domain=wisdom-companion-4.preview.emergentagent.com&secure_token=true';

interface User {
  user_id: string;
  email: string;
  name: string;
  picture?: string;
}

interface Child {
  child_id: string;
  parent_id: string;
  name: string;
  age_tier: string;
  avatar?: string;
  preferred_translation: string;
  parental_consent_given: boolean;
}

interface AuthContextType {
  user: User | null;
  children: Child[];
  currentChild: Child | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  refreshChildren: () => Promise<void>;
  addChild: (name: string, ageTier: string) => Promise<Child | null>;
  setCurrentChild: (child: Child) => void;
  updateChild: (childId: string, updates: Partial<Child>) => Promise<void>;
  giveConsent: (childId: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [childrenList, setChildrenList] = useState<Child[]>([]);
  const [currentChild, setCurrentChild] = useState<Child | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/auth/me`, {
        credentials: 'include',
      });
      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        await refreshChildren();
      }
    } catch (error) {
      console.log('Not authenticated');
    } finally {
      setIsLoading(false);
    }
  };

  const login = async () => {
    try {
      const result = await WebBrowser.openAuthSessionAsync(
        GOOGLE_AUTH_URL,
        'wisdom-companion-4.preview.emergentagent.com'
      );
      
      if (result.type === 'success' && result.url) {
        const url = new URL(result.url);
        const sessionId = url.searchParams.get('session_id');
        
        if (sessionId) {
          const response = await fetch(`${BACKEND_URL}/api/auth/session?session_id=${sessionId}`, {
            credentials: 'include',
          });
          
          if (response.ok) {
            const userData = await response.json();
            setUser(userData);
            await refreshChildren();
          }
        }
      }
    } catch (error) {
      console.error('Login error:', error);
    }
  };

  const logout = async () => {
    try {
      await fetch(`${BACKEND_URL}/api/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      });
      setUser(null);
      setChildrenList([]);
      setCurrentChild(null);
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  const refreshChildren = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/children`, {
        credentials: 'include',
      });
      if (response.ok) {
        const data = await response.json();
        setChildrenList(data.children || []);
        if (data.children?.length > 0 && !currentChild) {
          setCurrentChild(data.children[0]);
        }
      }
    } catch (error) {
      console.error('Refresh children error:', error);
    }
  };

  const addChild = async (name: string, ageTier: string): Promise<Child | null> => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/children`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ name, age_tier: ageTier }),
      });
      if (response.ok) {
        const newChild = await response.json();
        await refreshChildren();
        return newChild;
      }
    } catch (error) {
      console.error('Add child error:', error);
    }
    return null;
  };

  const updateChild = async (childId: string, updates: Partial<Child>) => {
    try {
      await fetch(`${BACKEND_URL}/api/children/${childId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(updates),
      });
      await refreshChildren();
    } catch (error) {
      console.error('Update child error:', error);
    }
  };

  const giveConsent = async (childId: string) => {
    try {
      await fetch(`${BACKEND_URL}/api/children/${childId}/consent`, {
        method: 'POST',
        credentials: 'include',
      });
      await refreshChildren();
    } catch (error) {
      console.error('Consent error:', error);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        children: childrenList,
        currentChild,
        isLoading,
        isAuthenticated: !!user,
        login,
        logout,
        refreshChildren,
        addChild,
        setCurrentChild,
        updateChild,
        giveConsent,
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
