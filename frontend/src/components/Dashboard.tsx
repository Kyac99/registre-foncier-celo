import React, { useState, useEffect } from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, Area, AreaChart
} from 'recharts';
import { 
  Home, Users, FileText, CheckCircle, AlertCircle, TrendingUp, 
  MapPin, Calendar, DollarSign, Activity, Eye, Download, Share2
} from 'lucide-react';

// Types
interface DashboardStats {
  total_properties: number;
  verified_properties: number;
  total_users: number;
  total_documents: number;
  pending_verifications: number;
  monthly_registrations: Array<{month: string, count: number}>;
  properties_by_type: Array<{type: string, count: number}>;
  properties_by_region: Array<{region: string, count: number}>;
  recent_activities: Array<{
    id: string;
    type: string;
    description: string;
    timestamp: string;
    user: string;
  }>;
}

interface DashboardProps {
  userRole?: 'admin' | 'verifier' | 'user';
  userId?: string;
}

const Dashboard: React.FC<DashboardProps> = ({ userRole = 'user', userId }) => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState('6months');

  // Couleurs pour les graphiques
  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D'];

  useEffect(() => {
    loadDashboardData();
  }, [timeRange, userId]);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      
      // Chargement des statistiques principales
      const statsResponse = await fetch('/api/v1/search/statistics', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      });
      
      if (!statsResponse.ok) throw new Error('Erreur de chargement des statistiques');
      
      const statsData = await statsResponse.json();
      
      // Simulation de données additionnelles pour le MVP
      const mockStats: DashboardStats = {
        total_properties: statsData.total_properties || 1250,
        verified_properties: statsData.verified_properties || 892,
        total_users: 456,
        total_documents: 2340,
        pending_verifications: 78,
        monthly_registrations: statsData.registration_trends || [
          { month: '2024-08', count: 45 },
          { month: '2024-09', count: 67 },
          { month: '2024-10', count: 89 },
          { month: '2024-11', count: 123 },
          { month: '2024-12', count: 156 },
          { month: '2025-01', count: 178 }
        ],
        properties_by_type: Object.entries(statsData.by_type || {
          'residential': 650,
          'commercial': 320,
          'agricultural': 180,
          'industrial': 70,
          'vacant_land': 30
        }).map(([type, count]) => ({ type, count: count as number })),
        properties_by_region: Object.entries(statsData.by_region || {
          'Centre': 450,
          'Hauts-Bassins': 280,
          'Centre-Ouest': 195,
          'Nord': 165,
          'Est': 110,
          'Centre-Sud': 50
        }).map(([region, count]) => ({ region, count: count as number })),
        recent_activities: [
          {
            id: '1',
            type: 'property_registered',
            description: 'Nouvelle propriété enregistrée à Ouagadougou',
            timestamp: '2025-01-30T10:30:00Z',
            user: 'Jean Ouédraogo'
          },
          {
            id: '2',
            type: 'property_verified',
            description: 'Propriété vérifiée dans la région Centre',
            timestamp: '2025-01-30T09:15:00Z',
            user: 'Marie Kaboré'
          },
          {
            id: '3',
            type: 'document_uploaded',
            description: 'Document ajouté pour une propriété à Bobo-Dioulasso',
            timestamp: '2025-01-30T08:45:00Z',
            user: 'Paul Sawadogo'
          }
        ]
      };
      
      setStats(mockStats);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur de chargement');
    } finally {
      setLoading(false);
    }
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('fr-FR').format(num);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'property_registered':
        return <Home className="h-4 w-4" />;
      case 'property_verified':
        return <CheckCircle className="h-4 w-4" />;
      case 'document_uploaded':
        return <FileText className="h-4 w-4" />;
      default:
        return <Activity className="h-4 w-4" />;
    }
  };

  const getActivityColor = (type: string) => {
    switch (type) {
      case 'property_registered':
        return 'text-blue-600 bg-blue-100';
      case 'property_verified':
        return 'text-green-600 bg-green-100';
      case 'document_uploaded':
        return 'text-purple-600 bg-purple-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Chargement du tableau de bord...</span>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="h-16 w-16 text-red-400 mx-auto mb-4" />
        <h3 className="text-xl font-medium text-gray-900 mb-2">
          Erreur de chargement
        </h3>
        <p className="text-gray-600">{error}</p>
        <button 
          onClick={loadDashboardData}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Réessayer
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Tableau de bord
          </h1>
          <p className="text-gray-600 mt-1">
            Vue d'ensemble du registre foncier décentralisé
          </p>
        </div>
        
        <div className="flex items-center space-x-3">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="1month">1 mois</option>
            <option value="3months">3 mois</option>
            <option value="6months">6 mois</option>
            <option value="1year">1 an</option>
          </select>
          
          <button className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            <Download className="h-4 w-4 mr-2" />
            Exporter
          </button>
        </div>
      </div>

      {/* Métriques principales */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">
                Propriétés totales
              </p>
              <p className="text-3xl font-bold text-gray-900">
                {formatNumber(stats.total_properties)}
              </p>
            </div>
            <div className="p-3 bg-blue-100 rounded-lg">
              <Home className="h-6 w-6 text-blue-600" />
            </div>
          </div>
          <div className="mt-4 flex items-center">
            <TrendingUp className="h-4 w-4 text-green-500 mr-1" />
            <span className="text-sm text-green-600 font-medium">+12%</span>
            <span className="text-sm text-gray-500 ml-1">ce mois</span>
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">
                Propriétés vérifiées
              </p>
              <p className="text-3xl font-bold text-gray-900">
                {formatNumber(stats.verified_properties)}
              </p>
            </div>
            <div className="p-3 bg-green-100 rounded-lg">
              <CheckCircle className="h-6 w-6 text-green-600" />
            </div>
          </div>
          <div className="mt-4 flex items-center">
            <span className="text-sm text-gray-500">
              {Math.round((stats.verified_properties / stats.total_properties) * 100)}% du total
            </span>
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">
                Utilisateurs actifs
              </p>
              <p className="text-3xl font-bold text-gray-900">
                {formatNumber(stats.total_users)}
              </p>
            </div>
            <div className="p-3 bg-purple-100 rounded-lg">
              <Users className="h-6 w-6 text-purple-600" />
            </div>
          </div>
          <div className="mt-4 flex items-center">
            <TrendingUp className="h-4 w-4 text-green-500 mr-1" />
            <span className="text-sm text-green-600 font-medium">+8%</span>
            <span className="text-sm text-gray-500 ml-1">ce mois</span>
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">
                Documents stockés
              </p>
              <p className="text-3xl font-bold text-gray-900">
                {formatNumber(stats.total_documents)}
              </p>
            </div>
            <div className="p-3 bg-yellow-100 rounded-lg">
              <FileText className="h-6 w-6 text-yellow-600" />
            </div>
          </div>
          <div className="mt-4 flex items-center">
            <span className="text-sm text-gray-500">
              Sur IPFS décentralisé
            </span>
          </div>
        </div>
      </div>

      {/* Graphiques */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Évolution des enregistrements */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Évolution des enregistrements
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={stats.monthly_registrations}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip />
              <Area 
                type="monotone" 
                dataKey="count" 
                stroke="#3B82F6" 
                fill="#3B82F6" 
                fillOpacity={0.2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Répartition par type */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Répartition par type
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={stats.properties_by_type}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ type, percent }) => `${type} (${(percent * 100).toFixed(0)}%)`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="count"
              >
                {stats.properties_by_type.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Répartition géographique et activités récentes */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top régions */}
        <div className="lg:col-span-2 bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Répartition par région
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={stats.properties_by_region}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="region" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#10B981" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Activités récentes */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">
              Activités récentes
            </h3>
            <button className="text-blue-600 hover:text-blue-800 text-sm font-medium">
              Voir tout
            </button>
          </div>
          
          <div className="space-y-4">
            {stats.recent_activities.map((activity) => (
              <div key={activity.id} className="flex items-start space-x-3">
                <div className={`p-2 rounded-lg ${getActivityColor(activity.type)}`}>
                  {getActivityIcon(activity.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900">
                    {activity.description}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Par {activity.user} • {formatDate(activity.timestamp)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Alertes et actions rapides */}
      {userRole === 'admin' || userRole === 'verifier' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Alertes */}
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
              <AlertCircle className="h-5 w-5 text-yellow-500 mr-2" />
              Alertes et notifications
            </h3>
            
            <div className="space-y-3">
              <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                <div className="flex items-center">
                  <AlertCircle className="h-4 w-4 text-yellow-600 mr-2" />
                  <p className="text-sm font-medium text-yellow-800">
                    {stats.pending_verifications} propriétés en attente de vérification
                  </p>
                </div>
              </div>
              
              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center">
                  <FileText className="h-4 w-4 text-blue-600 mr-2" />
                  <p className="text-sm font-medium text-blue-800">
                    15 nouveaux documents à examiner
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Actions rapides */}
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Actions rapides
            </h3>
            
            <div className="grid grid-cols-2 gap-3">
              <button className="flex flex-col items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                <CheckCircle className="h-6 w-6 text-green-600 mb-2" />
                <span className="text-sm font-medium text-gray-900">Vérifier</span>
              </button>
              
              <button className="flex flex-col items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                <FileText className="h-6 w-6 text-blue-600 mb-2" />
                <span className="text-sm font-medium text-gray-900">Documents</span>
              </button>
              
              <button className="flex flex-col items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                <Users className="h-6 w-6 text-purple-600 mb-2" />
                <span className="text-sm font-medium text-gray-900">Utilisateurs</span>
              </button>
              
              <button className="flex flex-col items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                <Activity className="h-6 w-6 text-orange-600 mb-2" />
                <span className="text-sm font-medium text-gray-900">Rapports</span>
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {/* Footer avec informations blockchain */}
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 p-6 rounded-xl border border-blue-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-blue-100 rounded-lg">
              <Activity className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <h4 className="font-semibold text-gray-900">
                Réseau CELO - {stats.verified_properties} propriétés sécurisées
              </h4>
              <p className="text-sm text-gray-600">
                Blockchain décentralisée • IPFS pour les documents • Vérifications cryptographiques
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <div className="h-3 w-3 bg-green-400 rounded-full animate-pulse"></div>
            <span className="text-sm font-medium text-green-600">Réseau opérationnel</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;