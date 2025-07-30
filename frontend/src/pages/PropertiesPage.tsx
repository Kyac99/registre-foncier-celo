import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  MagnifyingGlassIcon,
  AdjustmentsHorizontalIcon,
  MapPinIcon,
  CheckCircleIcon,
  XCircleIcon,
  EyeIcon
} from '@heroicons/react/24/outline';
import { useQuery } from 'react-query';
import { apiService } from '../services/apiService';
import { toast } from 'react-toastify';

interface Property {
  id: number;
  blockchain_id: number;
  owner_address: string;
  location: string;
  area: number;
  value?: number;
  property_type: string;
  status: string;
  is_verified: boolean;
  created_at: string;
}

const PropertiesPage: React.FC = () => {
  const [filters, setFilters] = useState({
    skip: 0,
    limit: 20,
    search: '',
    property_type: '',
    status: '',
    verified_only: false
  });
  const [showFilters, setShowFilters] = useState(false);

  // Query pour récupérer les propriétés
  const { data: propertiesData, isLoading, error, refetch } = useQuery(
    ['properties', filters],
    () => apiService.getProperties(filters),
    {
      keepPreviousData: true,
      onError: (error: any) => {
        toast.error('Erreur lors du chargement des propriétés');
        console.error('Error loading properties:', error);
      }
    }
  );

  const properties = propertiesData?.properties || [];
  const total = propertiesData?.total || 0;

  const propertyTypes = [
    { value: '', label: 'Tous types' },
    { value: 'RESIDENTIAL', label: 'Résidentiel' },
    { value: 'COMMERCIAL', label: 'Commercial' },
    { value: 'INDUSTRIAL', label: 'Industriel' },
    { value: 'AGRICULTURAL', label: 'Agricole' },
    { value: 'FOREST', label: 'Forestier' },
    { value: 'OTHER', label: 'Autre' }
  ];

  const statusOptions = [
    { value: '', label: 'Tous statuts' },
    { value: 'ACTIVE', label: 'Actif' },
    { value: 'DISPUTED', label: 'En litige' },
    { value: 'FROZEN', label: 'Gelé' },
    { value: 'TRANSFERRED', label: 'Transféré' }
  ];

  const handleFilterChange = (key: string, value: any) => {
    setFilters(prev => ({
      ...prev,
      [key]: value,
      skip: 0 // Reset pagination
    }));
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    refetch();
  };

  const formatCurrency = (value?: number) => {
    if (!value) return 'Non spécifié';
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const formatArea = (area: number) => {
    return new Intl.NumberFormat('fr-FR').format(area) + ' m²';
  };

  const getPropertyTypeLabel = (type: string) => {
    const typeObj = propertyTypes.find(t => t.value === type);
    return typeObj?.label || type;
  };

  const getStatusBadge = (status: string, isVerified: boolean) => {
    const statusConfig = {
      ACTIVE: { color: 'bg-green-100 text-green-800', label: 'Actif' },
      DISPUTED: { color: 'bg-red-100 text-red-800', label: 'En litige' },
      FROZEN: { color: 'bg-yellow-100 text-yellow-800', label: 'Gelé' },
      TRANSFERRED: { color: 'bg-blue-100 text-blue-800', label: 'Transféré' }
    };

    const config = statusConfig[status as keyof typeof statusConfig] || {
      color: 'bg-gray-100 text-gray-800',
      label: status
    };

    return (
      <div className="flex items-center space-x-2">
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.color}`}>
          {config.label}
        </span>
        {isVerified ? (
          <CheckCircleIcon className="w-4 h-4 text-green-600" title="Vérifié" />
        ) : (
          <XCircleIcon className="w-4 h-4 text-gray-400" title="Non vérifié" />
        )}
      </div>
    );
  };

  const nextPage = () => {
    if (filters.skip + filters.limit < total) {
      setFilters(prev => ({ ...prev, skip: prev.skip + prev.limit }));
    }
  };

  const prevPage = () => {
    if (filters.skip > 0) {
      setFilters(prev => ({ ...prev, skip: Math.max(0, prev.skip - prev.limit) }));
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Propriétés enregistrées
        </h1>
        <p className="text-gray-600">
          Explorez toutes les propriétés foncières enregistrées sur la blockchain
        </p>
      </div>

      {/* Barre de recherche et filtres */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <form onSubmit={handleSearch} className="space-y-4">
          {/* Recherche principale */}
          <div className="flex space-x-4">
            <div className="flex-1 relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Rechercher par localisation, adresse..."
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                value={filters.search}
                onChange={(e) => handleFilterChange('search', e.target.value)}
              />
            </div>
            <button
              type="button"
              onClick={() => setShowFilters(!showFilters)}
              className="flex items-center space-x-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <AdjustmentsHorizontalIcon className="w-5 h-5" />
              <span>Filtres</span>
            </button>
            <button
              type="submit"
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg transition-colors"
            >
              Rechercher
            </button>
          </div>

          {/* Filtres avancés */}
          {showFilters && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Type de propriété
                </label>
                <select
                  className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  value={filters.property_type}
                  onChange={(e) => handleFilterChange('property_type', e.target.value)}
                >
                  {propertyTypes.map(type => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Statut
                </label>
                <select
                  className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  value={filters.status}
                  onChange={(e) => handleFilterChange('status', e.target.value)}
                >
                  {statusOptions.map(status => (
                    <option key={status.value} value={status.value}>
                      {status.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-end">
                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    checked={filters.verified_only}
                    onChange={(e) => handleFilterChange('verified_only', e.target.checked)}
                  />
                  <span className="text-sm font-medium text-gray-700">
                    Seulement les vérifiées
                  </span>
                </label>
              </div>
            </div>
          )}
        </form>
      </div>

      {/* Statistiques */}
      <div className="bg-blue-50 rounded-lg p-4 mb-6">
        <div className="flex items-center justify-between">
          <div className="text-sm text-blue-800">
            <span className="font-semibold">{total}</span> propriétés trouvées
          </div>
          <Link
            to="/map"
            className="flex items-center space-x-1 text-blue-600 hover:text-blue-800 text-sm font-medium"
          >
            <MapPinIcon className="w-4 h-4" />
            <span>Voir sur la carte</span>
          </Link>
        </div>
      </div>

      {/* Liste des propriétés */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      ) : error ? (
        <div className="text-center py-12">
          <p className="text-red-600">Erreur lors du chargement des propriétés</p>
          <button
            onClick={() => refetch()}
            className="mt-4 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg"
          >
            Réessayer
          </button>
        </div>
      ) : properties.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500 text-lg">Aucune propriété trouvée</p>
        </div>
      ) : (
        <div className="space-y-4">
          {properties.map((property: Property) => (
            <div
              key={property.id}
              className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 mb-1">
                        {property.location}
                      </h3>
                      <p className="text-sm text-gray-500">
                        ID Blockchain: {property.blockchain_id}
                      </p>
                    </div>
                    {getStatusBadge(property.status, property.is_verified)}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                    <div>
                      <span className="text-sm text-gray-500">Type:</span>
                      <p className="font-medium">
                        {getPropertyTypeLabel(property.property_type)}
                      </p>
                    </div>
                    <div>
                      <span className="text-sm text-gray-500">Surface:</span>
                      <p className="font-medium">{formatArea(property.area)}</p>
                    </div>
                    <div>
                      <span className="text-sm text-gray-500">Valeur:</span>
                      <p className="font-medium">{formatCurrency(property.value)}</p>
                    </div>
                  </div>

                  <div className="flex items-center space-x-4 text-sm text-gray-500">
                    <span>
                      Propriétaire: {property.owner_address.slice(0, 6)}...{property.owner_address.slice(-4)}
                    </span>
                    <span>•</span>
                    <span>
                      Enregistré le {new Date(property.created_at).toLocaleDateString('fr-FR')}
                    </span>
                  </div>
                </div>

                <div className="ml-6">
                  <Link
                    to={`/properties/${property.id}`}
                    className="flex items-center space-x-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm transition-colors"
                  >
                    <EyeIcon className="w-4 h-4" />
                    <span>Voir détails</span>
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {total > filters.limit && (
        <div className="flex items-center justify-between mt-8">
          <div className="text-sm text-gray-700">
            Affichage de {filters.skip + 1} à {Math.min(filters.skip + filters.limit, total)} sur {total} propriétés
          </div>
          <div className="flex space-x-2">
            <button
              onClick={prevPage}
              disabled={filters.skip === 0}
              className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Précédent
            </button>
            <button
              onClick={nextPage}
              disabled={filters.skip + filters.limit >= total}
              className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Suivant
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default PropertiesPage;
