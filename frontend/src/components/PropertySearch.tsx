import React, { useState, useEffect, useCallback } from 'react';
import { Search, Filter, MapPin, Home, Calendar, CheckCircle, Eye, Star } from 'lucide-react';
import { debounce } from 'lodash';

// Types
interface Property {
  property_id: string;
  title: string;
  description: string;
  property_type: string;
  status: string;
  verified: boolean;
  city: string;
  region: string;
  area?: number;
  price?: number;
  registration_date: string;
  owner_name?: string;
  distance_km?: number;
  images?: string[];
}

interface SearchFilters {
  propertyType?: string;
  city?: string;
  region?: string;
  verifiedOnly: boolean;
  minArea?: number;
  maxArea?: number;
  minPrice?: number;
  maxPrice?: number;
}

interface PropertySearchProps {
  onPropertySelect?: (property: Property) => void;
  initialQuery?: string;
}

const PropertySearch: React.FC<PropertySearchProps> = ({ 
  onPropertySelect, 
  initialQuery = '' 
}) => {
  const [query, setQuery] = useState(initialQuery);
  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(false);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(0);
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<SearchFilters>({
    verifiedOnly: false
  });
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);

  const limit = 12;

  // Options pour les filtres
  const propertyTypes = [
    { value: '', label: 'Tous les types' },
    { value: 'residential', label: 'Résidentiel' },
    { value: 'commercial', label: 'Commercial' },
    { value: 'industrial', label: 'Industriel' },
    { value: 'agricultural', label: 'Agricole' },
    { value: 'vacant_land', label: 'Terrain nu' },
    { value: 'other', label: 'Autre' }
  ];

  const regions = [
    'Centre', 'Centre-Est', 'Centre-Nord', 'Centre-Ouest',
    'Centre-Sud', 'Est', 'Hauts-Bassins', 'Nord',
    'Plateau-Central', 'Sahel', 'Sud-Ouest', 'Boucle du Mouhoun', 'Cascades'
  ];

  // Recherche avec debounce
  const debouncedSearch = useCallback(
    debounce(async (searchQuery: string, searchFilters: SearchFilters, pageNum: number = 0) => {
      setLoading(true);
      try {
        const params = new URLSearchParams({
          skip: (pageNum * limit).toString(),
          limit: limit.toString(),
          ...(searchQuery && { q: searchQuery }),
          ...(searchFilters.propertyType && { property_type: searchFilters.propertyType }),
          ...(searchFilters.city && { city: searchFilters.city }),
          ...(searchFilters.region && { region: searchFilters.region }),
          ...(searchFilters.verifiedOnly && { verified_only: 'true' }),
          ...(searchFilters.minArea && { min_area: searchFilters.minArea.toString() }),
          ...(searchFilters.maxArea && { max_area: searchFilters.maxArea.toString() }),
          ...(searchFilters.minPrice && { min_price: searchFilters.minPrice.toString() }),
          ...(searchFilters.maxPrice && { max_price: searchFilters.maxPrice.toString() })
        });

        const response = await fetch(`/api/v1/search/properties?${params}`);
        if (!response.ok) throw new Error('Erreur de recherche');

        const data = await response.json();
        
        if (pageNum === 0) {
          setProperties(data.properties);
        } else {
          setProperties(prev => [...prev, ...data.properties]);
        }
        
        setTotalCount(data.total_count);
      } catch (error) {
        console.error('Erreur de recherche:', error);
      } finally {
        setLoading(false);
      }
    }, 300),
    [limit]
  );

  // Suggestions auto-complétées
  const debouncedSuggestions = useCallback(
    debounce(async (searchQuery: string) => {
      if (searchQuery.length < 2) {
        setSuggestions([]);
        return;
      }

      try {
        const response = await fetch(`/api/v1/search/suggestions?q=${encodeURIComponent(searchQuery)}&limit=5`);
        if (response.ok) {
          const data = await response.json();
          setSuggestions(data.suggestions || []);
        }
      } catch (error) {
        console.error('Erreur suggestions:', error);
      }
    }, 200),
    []
  );

  // Effets
  useEffect(() => {
    debouncedSearch(query, filters, 0);
    setPage(0);
  }, [query, filters, debouncedSearch]);

  useEffect(() => {
    if (query.length >= 2) {
      debouncedSuggestions(query);
    } else {
      setSuggestions([]);
    }
  }, [query, debouncedSuggestions]);

  // Handlers
  const handleQueryChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value);
    setShowSuggestions(true);
  };

  const handleSuggestionClick = (suggestion: string) => {
    setQuery(suggestion);
    setShowSuggestions(false);
    setSuggestions([]);
  };

  const handleFilterChange = (key: keyof SearchFilters, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const loadMore = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    debouncedSearch(query, filters, nextPage);
  };

  const clearFilters = () => {
    setFilters({ verifiedOnly: false });
    setQuery('');
  };

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: 'XOF',
      minimumFractionDigits: 0
    }).format(price);
  };

  const formatArea = (area: number) => {
    return `${area.toLocaleString()} m²`;
  };

  return (
    <div className="w-full max-w-6xl mx-auto">
      {/* Barre de recherche */}
      <div className="relative mb-6">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
          <input
            type="text"
            value={query}
            onChange={handleQueryChange}
            onFocus={() => setShowSuggestions(suggestions.length > 0)}
            placeholder="Rechercher une propriété (ville, type, description...)"
            className="w-full pl-12 pr-16 py-4 text-lg border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all duration-200"
          />
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`absolute right-4 top-1/2 transform -translate-y-1/2 p-2 rounded-lg transition-colors ${
              showFilters ? 'bg-blue-100 text-blue-600' : 'text-gray-400 hover:text-gray-600'
            }`}
          >
            <Filter className="h-5 w-5" />
          </button>
        </div>

        {/* Suggestions */}
        {showSuggestions && suggestions.length > 0 && (
          <div className="absolute top-full left-0 right-0 mt-2 bg-white border border-gray-200 rounded-lg shadow-lg z-10">
            {suggestions.map((suggestion, index) => (
              <button
                key={index}
                onClick={() => handleSuggestionClick(suggestion)}
                className="w-full px-4 py-3 text-left hover:bg-gray-50 border-b border-gray-100 last:border-b-0"
              >
                <div className="flex items-center">
                  <Search className="h-4 w-4 text-gray-400 mr-3" />
                  <span>{suggestion}</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Filtres avancés */}
      {showFilters && (
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Type de propriété
              </label>
              <select
                value={filters.propertyType || ''}
                onChange={(e) => handleFilterChange('propertyType', e.target.value || undefined)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                {propertyTypes.map(type => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Ville
              </label>
              <input
                type="text"
                value={filters.city || ''}
                onChange={(e) => handleFilterChange('city', e.target.value || undefined)}
                placeholder="Ex: Ouagadougou"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Région
              </label>
              <select
                value={filters.region || ''}
                onChange={(e) => handleFilterChange('region', e.target.value || undefined)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Toutes les régions</option>
                {regions.map(region => (
                  <option key={region} value={region}>
                    {region}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center">
              <label className="flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.verifiedOnly}
                  onChange={(e) => handleFilterChange('verifiedOnly', e.target.checked)}
                  className="sr-only"
                />
                <div className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  filters.verifiedOnly ? 'bg-blue-600' : 'bg-gray-200'
                }`}>
                  <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    filters.verifiedOnly ? 'translate-x-6' : 'translate-x-1'
                  }`} />
                </div>
                <span className="ml-3 text-sm font-medium text-gray-700">
                  Vérifiées uniquement
                </span>
              </label>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Superficie min (m²)
              </label>
              <input
                type="number"
                value={filters.minArea || ''}
                onChange={(e) => handleFilterChange('minArea', e.target.value ? parseFloat(e.target.value) : undefined)}
                placeholder="0"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Superficie max (m²)
              </label>
              <input
                type="number"
                value={filters.maxArea || ''}
                onChange={(e) => handleFilterChange('maxArea', e.target.value ? parseFloat(e.target.value) : undefined)}
                placeholder="∞"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Prix min (FCFA)
              </label>
              <input
                type="number"
                value={filters.minPrice || ''}
                onChange={(e) => handleFilterChange('minPrice', e.target.value ? parseFloat(e.target.value) : undefined)}
                placeholder="0"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Prix max (FCFA)
              </label>
              <input
                type="number"
                value={filters.maxPrice || ''}
                onChange={(e) => handleFilterChange('maxPrice', e.target.value ? parseFloat(e.target.value) : undefined)}
                placeholder="∞"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="flex justify-end mt-4 space-x-3">
            <button
              onClick={clearFilters}
              className="px-4 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Effacer les filtres
            </button>
          </div>
        </div>
      )}

      {/* Résultats */}
      <div className="mb-4 flex items-center justify-between">
        <div className="text-gray-600">
          {totalCount > 0 ? (
            <span>{totalCount} propriété{totalCount > 1 ? 's' : ''} trouvée{totalCount > 1 ? 's' : ''}</span>
          ) : loading ? (
            <span>Recherche en cours...</span>
          ) : (
            <span>Aucune propriété trouvée</span>
          )}
        </div>
      </div>

      {/* Liste des propriétés */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {properties.map((property) => (
          <div
            key={property.property_id}
            className="bg-white border border-gray-200 rounded-xl overflow-hidden hover:shadow-lg transition-shadow duration-200 cursor-pointer"
            onClick={() => onPropertySelect?.(property)}
          >
            {/* Image placeholder */}
            <div className="h-48 bg-gradient-to-r from-blue-400 to-purple-500 relative">
              <div className="absolute inset-0 bg-black bg-opacity-20 flex items-center justify-center">
                <Home className="h-12 w-12 text-white opacity-60" />
              </div>
              {property.verified && (
                <div className="absolute top-3 right-3 bg-green-500 text-white px-2 py-1 rounded-full text-xs font-medium flex items-center">
                  <CheckCircle className="h-3 w-3 mr-1" />
                  Vérifiée
                </div>
              )}
              {property.distance_km && (
                <div className="absolute top-3 left-3 bg-blue-500 text-white px-2 py-1 rounded-full text-xs font-medium flex items-center">
                  <MapPin className="h-3 w-3 mr-1" />
                  {property.distance_km.toFixed(1)} km
                </div>
              )}
            </div>

            <div className="p-4">
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-semibold text-gray-900 text-lg line-clamp-1">
                  {property.title}
                </h3>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  property.status === 'active' ? 'bg-green-100 text-green-800' :
                  property.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {property.status}
                </span>
              </div>

              <p className="text-gray-600 text-sm mb-3 line-clamp-2">
                {property.description}
              </p>

              <div className="space-y-2 mb-4">
                <div className="flex items-center text-sm text-gray-500">
                  <MapPin className="h-4 w-4 mr-2" />
                  <span>{property.city}, {property.region}</span>
                </div>
                
                {property.area && (
                  <div className="flex items-center text-sm text-gray-500">
                    <div className="h-4 w-4 mr-2 flex items-center justify-center">
                      <div className="h-3 w-3 border border-gray-400 rounded-sm"></div>
                    </div>
                    <span>{formatArea(property.area)}</span>
                  </div>
                )}

                <div className="flex items-center text-sm text-gray-500">
                  <Calendar className="h-4 w-4 mr-2" />
                  <span>
                    Enregistrée le {new Date(property.registration_date).toLocaleDateString('fr-FR')}
                  </span>
                </div>
              </div>

              {property.price && (
                <div className="text-2xl font-bold text-green-600 mb-2">
                  {formatPrice(property.price)}
                </div>
              )}

              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-500">
                  {property.owner_name && `Par ${property.owner_name}`}
                </div>
                <button className="flex items-center text-blue-600 hover:text-blue-800 text-sm font-medium">
                  <Eye className="h-4 w-4 mr-1" />
                  Voir détails
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Bouton "Charger plus" */}
      {properties.length < totalCount && (
        <div className="text-center mt-8">
          <button
            onClick={loadMore}
            disabled={loading}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Chargement...' : 'Charger plus de propriétés'}
          </button>
        </div>
      )}

      {/* État vide */}
      {!loading && properties.length === 0 && (
        <div className="text-center py-12">
          <Home className="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-xl font-medium text-gray-900 mb-2">
            Aucune propriété trouvée
          </h3>
          <p className="text-gray-600 mb-4">
            Essayez d'ajuster vos critères de recherche ou supprimez quelques filtres.
          </p>
          <button
            onClick={clearFilters}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Effacer tous les filtres
          </button>
        </div>
      )}
    </div>
  );
};

export default PropertySearch;