import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  HomeIcon, 
  BuildingOfficeIcon, 
  MagnifyingGlassIcon, 
  MapIcon,
  UserIcon,
  ChartBarIcon,
  PlusIcon
} from '@heroicons/react/24/outline';
import { useWeb3 } from '../contexts/Web3Context';
import { useAuth } from '../contexts/AuthContext';
import WalletConnectButton from './WalletConnectButton';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const { isConnected, account, networkInfo } = useWeb3();
  const { user } = useAuth();

  const navigation = [
    { name: 'Accueil', href: '/', icon: HomeIcon },
    { name: 'Propriétés', href: '/properties', icon: BuildingOfficeIcon },
    { name: 'Recherche', href: '/search', icon: MagnifyingGlassIcon },
    { name: 'Carte', href: '/map', icon: MapIcon },
  ];

  const userNavigation = [
    { name: 'Tableau de bord', href: '/dashboard', icon: ChartBarIcon },
    { name: 'Profil', href: '/profile', icon: UserIcon },
  ];

  const isActivePath = (path: string) => {
    return location.pathname === path;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo */}
            <div className="flex items-center">
              <Link to="/" className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                  <BuildingOfficeIcon className="w-5 h-5 text-white" />
                </div>
                <span className="text-xl font-bold text-gray-900">
                  RFD
                </span>
                <span className="text-sm text-gray-500 hidden sm:block">
                  Registre Foncier Décentralisé
                </span>
              </Link>
            </div>

            {/* Navigation */}
            <nav className="hidden md:flex space-x-8">
              {navigation.map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={`flex items-center space-x-1 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      isActivePath(item.href)
                        ? 'text-blue-600 bg-blue-50'
                        : 'text-gray-700 hover:text-blue-600 hover:bg-gray-50'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{item.name}</span>
                  </Link>
                );
              })}
            </nav>

            {/* Actions utilisateur */}
            <div className="flex items-center space-x-4">
              {/* Bouton enregistrer (si connecté et autorisé) */}
              {isConnected && user?.permissions?.can_register_property && (
                <Link
                  to="/register"
                  className="flex items-center space-x-1 bg-green-600 hover:bg-green-700 text-white px-3 py-2 rounded-md text-sm font-medium transition-colors"
                >
                  <PlusIcon className="w-4 h-4" />
                  <span className="hidden sm:block">Enregistrer</span>
                </Link>
              )}

              {/* Informations réseau */}
              {isConnected && (
                <div className="hidden lg:flex items-center space-x-2 text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span>{networkInfo.name}</span>
                </div>
              )}

              {/* Connexion wallet */}
              <WalletConnectButton />

              {/* Menu utilisateur connecté */}
              {isConnected && (
                <div className="relative">
                  <div className="flex items-center space-x-2">
                    {userNavigation.map((item) => {
                      const Icon = item.icon;
                      return (
                        <Link
                          key={item.name}
                          to={item.href}
                          className={`p-2 rounded-md transition-colors ${
                            isActivePath(item.href)
                              ? 'text-blue-600 bg-blue-50'
                              : 'text-gray-700 hover:text-blue-600 hover:bg-gray-50'
                          }`}
                          title={item.name}
                        >
                          <Icon className="w-5 h-5" />
                        </Link>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Navigation mobile */}
        <div className="md:hidden border-t border-gray-200">
          <div className="px-4 py-2">
            <div className="flex space-x-4 overflow-x-auto">
              {navigation.map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={`flex items-center space-x-1 px-3 py-2 rounded-md text-sm font-medium whitespace-nowrap transition-colors ${
                      isActivePath(item.href)
                        ? 'text-blue-600 bg-blue-50'
                        : 'text-gray-700 hover:text-blue-600 hover:bg-gray-50'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{item.name}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        </div>
      </header>

      {/* Contenu principal */}
      <main className="flex-1">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            {/* Informations du projet */}
            <div className="md:col-span-2">
              <div className="flex items-center space-x-2 mb-4">
                <div className="w-6 h-6 bg-blue-600 rounded-lg flex items-center justify-center">
                  <BuildingOfficeIcon className="w-4 h-4 text-white" />
                </div>
                <span className="text-lg font-bold text-gray-900">
                  Registre Foncier Décentralisé
                </span>
              </div>
              <p className="text-gray-600 text-sm mb-4">
                Plateforme décentralisée pour l'enregistrement et la gestion 
                transparente des propriétés foncières sur la blockchain CELO.
              </p>
              <div className="flex items-center space-x-4 text-sm text-gray-500">
                <span>Propulsé par CELO</span>
                <span>•</span>
                <span>Sécurisé par IPFS</span>
                <span>•</span>
                <span>Open Source</span>
              </div>
            </div>

            {/* Liens rapides */}
            <div>
              <h3 className="text-sm font-semibold text-gray-900 mb-4">
                Liens rapides
              </h3>
              <ul className="space-y-2 text-sm text-gray-600">
                <li>
                  <Link to="/properties" className="hover:text-blue-600 transition-colors">
                    Consulter les propriétés
                  </Link>
                </li>
                <li>
                  <Link to="/search" className="hover:text-blue-600 transition-colors">
                    Rechercher
                  </Link>
                </li>
                <li>
                  <Link to="/map" className="hover:text-blue-600 transition-colors">
                    Carte interactive
                  </Link>
                </li>
                {isConnected && (
                  <li>
                    <Link to="/dashboard" className="hover:text-blue-600 transition-colors">
                      Tableau de bord
                    </Link>
                  </li>
                )}
              </ul>
            </div>

            {/* Statistiques réseau */}
            <div>
              <h3 className="text-sm font-semibold text-gray-900 mb-4">
                Réseau
              </h3>
              <div className="space-y-2 text-sm text-gray-600">
                <div className="flex justify-between">
                  <span>Statut:</span>
                  <span className={`font-medium ${isConnected ? 'text-green-600' : 'text-red-600'}`}>
                    {isConnected ? 'Connecté' : 'Déconnecté'}
                  </span>
                </div>
                {isConnected && (
                  <>
                    <div className="flex justify-between">
                      <span>Réseau:</span>
                      <span className="font-medium text-blue-600">
                        {networkInfo.name}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Compte:</span>
                      <span className="font-mono text-xs">
                        {account ? `${account.slice(0, 6)}...${account.slice(-4)}` : ''}
                      </span>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Copyright */}
          <div className="border-t border-gray-200 mt-8 pt-4">
            <div className="flex flex-col sm:flex-row justify-between items-center text-sm text-gray-500">
              <p>
                © 2024 Registre Foncier Décentralisé. Tous droits réservés.
              </p>
              <p className="mt-2 sm:mt-0">
                Développé avec ❤️ pour un foncier transparent
              </p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Layout;
