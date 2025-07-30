import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { useWeb3 } from './Web3Context';
import { apiService } from '../services/apiService';

// Types
interface User {
  id: string;
  wallet_address: string;
  first_name?: string;
  last_name?: string;
  full_name: string;
  email?: string;
  role: 'citizen' | 'notary' | 'surveyor' | 'tax_authority' | 'admin';
  is_verified: boolean;
  is_active: boolean;
  permissions: {
    can_register_property: boolean;
    can_verify_property: boolean;
    can_manage_users: boolean;
  };
  created_at: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: () => Promise<void>;
  logout: () => void;
  updateProfile: (data: Partial<User>) => Promise<void>;
  refreshUser: () => Promise<void>;
}

interface AuthProviderProps {
  children: ReactNode;
}

// Contexte
const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const { account, isConnected, signer } = useWeb3();

  const isAuthenticated = !!user && isConnected;

  // Connexion utilisateur
  const login = async () => {
    if (!account || !signer) {
      throw new Error('Wallet non connecté');
    }

    setIsLoading(true);

    try {
      // Vérification si l'utilisateur existe
      let userData = await apiService.getUserByWallet(account);

      if (!userData) {
        // Création d'un nouvel utilisateur
        userData = await apiService.createUser({
          wallet_address: account,
          role: 'citizen'
        });
      }

      // Authentification avec signature
      const message = `Connexion au Registre Foncier Décentralisé\nAdresse: ${account}\nTimestamp: ${Date.now()}`;
      const signature = await signer.signMessage(message);

      // Vérification de la signature côté serveur
      const authResult = await apiService.authenticateUser({
        wallet_address: account,
        message,
        signature
      });

      if (authResult.success) {
        setUser(userData);
        // Stockage du token si fourni
        if (authResult.token) {
          localStorage.setItem('auth_token', authResult.token);
        }
      } else {
        throw new Error('Authentification échouée');
      }
    } catch (error) {
      console.error('Erreur lors de la connexion:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  // Déconnexion
  const logout = () => {
    setUser(null);
    localStorage.removeItem('auth_token');
  };

  // Mise à jour du profil
  const updateProfile = async (data: Partial<User>) => {
    if (!user) {
      throw new Error('Utilisateur non connecté');
    }

    try {
      const updatedUser = await apiService.updateUser(user.id, data);
      setUser(updatedUser);
    } catch (error) {
      console.error('Erreur mise à jour profil:', error);
      throw error;
    }
  };

  // Actualisation des données utilisateur
  const refreshUser = async () => {
    if (!account) return;

    try {
      const userData = await apiService.getUserByWallet(account);
      if (userData) {
        setUser(userData);
      }
    } catch (error) {
      console.error('Erreur actualisation utilisateur:', error);
    }
  };

  // Effet pour gérer les changements de compte
  useEffect(() => {
    if (!isConnected || !account) {
      logout();
      return;
    }

    // Tentative de connexion automatique si token présent
    const token = localStorage.getItem('auth_token');
    if (token && !user) {
      refreshUser();
    }
  }, [isConnected, account]);

  // Effet pour actualiser les données utilisateur périodiquement
  useEffect(() => {
    if (!isAuthenticated) return;

    const interval = setInterval(() => {
      refreshUser();
    }, 5 * 60 * 1000); // Toutes les 5 minutes

    return () => clearInterval(interval);
  }, [isAuthenticated]);

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated,
    login,
    logout,
    updateProfile,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export default AuthContext;
