import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  ShieldCheckIcon, 
  GlobeAltIcon, 
  DocumentTextIcon,
  ChartBarIcon,
  MapPinIcon,
  UserGroupIcon,
  BuildingOfficeIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline';
import { useWeb3 } from '../contexts/Web3Context';
import { useAuth } from '../contexts/AuthContext';
import { apiService } from '../services/apiService';
import { toast } from 'react-toastify';

const HomePage: React.FC = () => {
  const { isConnected, networkInfo } = useWeb3();
  const { isAuthenticated, login } = useAuth();
  const [stats, setStats] = useState<any>(null);
  const [isLoadingStats, setIsLoadingStats] = useState(true);

  // Chargement des statistiques
  useEffect(() => {
    const loadStats = async () => {
      try {
        const [propertyStats, networkStats] = await Promise.all([
          apiService.getPropertyStats(),
          apiService.getBlockchainStats()
        ]);
        setStats({ ...propertyStats, ...networkStats });
      } catch (error) {
        console.error('Erreur chargement stats:', error);
      } finally {
        setIsLoadingStats(false);
      }
    };

    loadStats();
  }, []);

  // Fonction de connexion rapide
  const handleQuickLogin = async () => {
    if (!isConnected) {
      toast.warning('Veuillez d\'abord connecter votre wallet');
      return;
    }

    try {
      await login();
      toast.success('Connexion réussie !');
    } catch (error: any) {
      toast.error(`Erreur de connexion: ${error.message}`);
    }
  };

  const features = [
    {
      icon: ShieldCheckIcon,
      title: 'Sécurité Blockchain',
      description: 'Vos propriétés sont sécurisées par la blockchain CELO, garantissant immutabilité et transparence.'
    },
    {
      icon: DocumentTextIcon,
      title: 'Documents IPFS',
      description: 'Stockage décentralisé et chiffré de tous vos documents officiels sur le réseau IPFS.'
    },
    {
      icon: MapPinIcon,
      title: 'Géolocalisation',
      description: 'Coordonnées GPS précises et cartographie interactive pour toutes les propriétés.'
    },
    {
      icon: UserGroupIcon,
      title: 'Multi-acteurs',
      description: 'Notaires, géomètres, autorités fiscales et citoyens collaborent en toute transparence.'
    }
  ];

  const advantages = [
    'Prévention des fraudes et double-ventes',
    'Historique complet et traçable',
    'Réduction des délais administratifs',
    'Facilitation de l\'accès au crédit',
    'Transparence totale des transactions',
    'Coûts réduits par rapport aux méthodes traditionnelles'
  ];

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-800 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
          <div className="text-center">
            <h1 className="text-4xl md:text-6xl font-bold mb-6">
              Registre Foncier
              <br />
              <span className="text-blue-200">Décentralisé</span>
            </h1>
            <p className="text-xl md:text-2xl text-blue-100 mb-8 max-w-3xl mx-auto">
              Sécurisez, vérifiez et gérez vos propriétés foncières sur la blockchain CELO. 
              Une solution transparente, fiable et accessible pour un foncier moderne.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              {!isAuthenticated ? (
                <>
                  {isConnected ? (
                    <button
                      onClick={handleQuickLogin}
                      className="bg-white text-blue-600 hover:bg-blue-50 px-8 py-3 rounded-lg font-semibold text-lg transition-colors"
                    >
                      Se connecter
                    </button>
                  ) : (
                    <p className="text-blue-200">
                      Connectez votre wallet pour commencer
                    </p>
                  )}
                </>
              ) : (
                <Link
                  to="/properties"
                  className="bg-white text-blue-600 hover:bg-blue-50 px-8 py-3 rounded-lg font-semibold text-lg transition-colors"
                >
                  Explorer les propriétés
                </Link>
              )}
              
              <Link
                to="/map"
                className="border-2 border-white text-white hover:bg-white hover:text-blue-600 px-8 py-3 rounded-lg font-semibold text-lg transition-colors"
              >
                Voir la carte
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Statistiques */}
      <section className="py-16 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              La confiance par les chiffres
            </h2>
            <p className="text-gray-600 text-lg">
              Découvrez l'impact de notre plateforme décentralisée
            </p>
          </div>

          {isLoadingStats ? (
            <div className="flex justify-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="text-center p-6 bg-blue-50 rounded-lg">
                <ChartBarIcon className="w-12 h-12 text-blue-600 mx-auto mb-3" />
                <div className="text-3xl font-bold text-gray-900">
                  {stats?.total_properties || 0}
                </div>
                <div className="text-gray-600">Propriétés enregistrées</div>
              </div>
              
              <div className="text-center p-6 bg-green-50 rounded-lg">
                <CheckCircleIcon className="w-12 h-12 text-green-600 mx-auto mb-3" />
                <div className="text-3xl font-bold text-gray-900">
                  {stats?.verified_properties || 0}
                </div>
                <div className="text-gray-600">Propriétés vérifiées</div>
              </div>
              
              <div className="text-center p-6 bg-purple-50 rounded-lg">
                <UserGroupIcon className="w-12 h-12 text-purple-600 mx-auto mb-3" />
                <div className="text-3xl font-bold text-gray-900">
                  {stats?.unique_owners || 0}
                </div>
                <div className="text-gray-600">Propriétaires uniques</div>
              </div>
              
              <div className="text-center p-6 bg-orange-50 rounded-lg">
                <BuildingOfficeIcon className="w-12 h-12 text-orange-600 mx-auto mb-3" />
                <div className="text-3xl font-bold text-gray-900">
                  {stats?.total_area ? Math.round(stats.total_area / 10000) : 0}
                </div>
                <div className="text-gray-600">Hectares gérés</div>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Fonctionnalités */}
      <section className="py-16 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              Une technologie de pointe au service du foncier
            </h2>
            <p className="text-gray-600 text-lg max-w-3xl mx-auto">
              Notre plateforme combine blockchain, IPFS et géolocalisation pour révolutionner 
              la gestion des propriétés foncières
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <div key={index} className="flex items-start space-x-4 p-6 bg-white rounded-lg shadow-sm">
                  <div className="flex-shrink-0">
                    <Icon className="w-8 h-8 text-blue-600" />
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-2">
                      {feature.title}
                    </h3>
                    <p className="text-gray-600">
                      {feature.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Avantages */}
      <section className="py-16 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-3xl font-bold text-gray-900 mb-6">
                Pourquoi choisir notre solution ?
              </h2>
              <p className="text-gray-600 text-lg mb-8">
                Notre registre foncier décentralisé apporte des avantages concrets 
                pour tous les acteurs de l'écosystème immobilier.
              </p>
              
              <div className="space-y-4">
                {advantages.map((advantage, index) => (
                  <div key={index} className="flex items-start space-x-3">
                    <CheckCircleIcon className="w-6 h-6 text-green-600 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-700">{advantage}</span>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="relative">
              <div className="bg-gradient-to-br from-blue-500 to-indigo-600 rounded-2xl p-8 text-white">
                <GlobeAltIcon className="w-16 h-16 text-blue-200 mb-4" />
                <h3 className="text-2xl font-bold mb-4">
                  Réseau {networkInfo.name}
                </h3>
                <p className="text-blue-100 mb-6">
                  Propulsé par la blockchain CELO, notre plateforme offre des frais de transaction 
                  ultra-bas et une confirmation rapide.
                </p>
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 bg-green-400 rounded-full"></div>
                  <span className="text-sm text-blue-100">Réseau opérationnel</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Call to Action */}
      <section className="py-16 bg-blue-600">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Prêt à révolutionner votre gestion foncière ?
          </h2>
          <p className="text-blue-100 text-lg mb-8 max-w-2xl mx-auto">
            Rejoignez les pionniers qui font confiance à la blockchain pour sécuriser 
            leurs biens immobiliers
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              to="/properties"
              className="bg-white text-blue-600 hover:bg-blue-50 px-8 py-3 rounded-lg font-semibold text-lg transition-colors"
            >
              Explorer les propriétés
            </Link>
            <Link
              to="/search"
              className="border-2 border-white text-white hover:bg-white hover:text-blue-600 px-8 py-3 rounded-lg font-semibold text-lg transition-colors"
            >
              Rechercher une propriété
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
};

export default HomePage;
