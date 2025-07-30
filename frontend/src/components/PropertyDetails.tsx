import React, { useState, useEffect } from 'react';
import { 
  MapPin, Home, Calendar, User, FileText, CheckCircle, AlertCircle, 
  Download, Share2, Edit, Trash2, ExternalLink, Copy, Phone, Mail,
  Layers, DollarSign, TrendingUp, Clock, Shield, Eye, Upload
} from 'lucide-react';

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
  address: string;
  latitude?: number;
  longitude?: number;
  area?: number;
  price?: number;
  registration_date: string;
  last_updated: string;
  owner_name?: string;
  owner_contact?: string;
  blockchain_hash?: string;
  verification_date?: string;
  verifier_name?: string;
  documents?: Document[];
  images?: string[];
  metadata?: any;
}

interface Document {
  document_id: string;
  title: string;
  document_type: string;
  filename: string;
  size: number;
  mime_type: string;
  upload_timestamp: string;
  verification_status: string;
  is_public: boolean;
}

interface PropertyDetailsProps {
  propertyId: string;
  onEdit?: (property: Property) => void;
  onDelete?: (propertyId: string) => void;
  canEdit?: boolean;
  canDelete?: boolean;
}

const PropertyDetails: React.FC<PropertyDetailsProps> = ({
  propertyId,
  onEdit,
  onDelete,
  canEdit = false,
  canDelete = false
}) => {
  const [property, setProperty] = useState<Property | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showContactInfo, setShowContactInfo] = useState(false);
  const [activeTab, setActiveTab] = useState<'details' | 'documents' | 'blockchain'>('details');
  const [blockchainInfo, setBlockchainInfo] = useState<any>(null);

  // Chargement des données
  useEffect(() => {
    const fetchProperty = async () => {
      try {
        setLoading(true);
        const response = await fetch(`/api/v1/properties/${propertyId}`);
        if (!response.ok) throw new Error('Propriété non trouvée');
        
        const data = await response.json();
        setProperty(data);

        // Charger les informations blockchain si disponibles
        if (data.blockchain_hash) {
          const blockchainResponse = await fetch(`/api/v1/blockchain/property/${propertyId}`);
          if (blockchainResponse.ok) {
            const blockchainData = await blockchainResponse.json();
            setBlockchainInfo(blockchainData);
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erreur de chargement');
      } finally {
        setLoading(false);
      }
    };

    if (propertyId) {
      fetchProperty();
    }
  }, [propertyId]);

  // Handlers
  const handleShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: property?.title,
          text: property?.description,
          url: window.location.href,
        });
      } catch (err) {
        console.log('Partage annulé');
      }
    } else {
      // Fallback: copier l'URL
      navigator.clipboard.writeText(window.location.href);
      alert('Lien copié dans le presse-papiers');
    }
  };

  const handleDownloadDocument = async (documentId: string, filename: string) => {
    try {
      const response = await fetch(`/api/v1/documents/${documentId}/download`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      });
      
      if (!response.ok) throw new Error('Erreur de téléchargement');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Erreur de téléchargement:', error);
      alert('Erreur lors du téléchargement du document');
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    alert('Copié dans le presse-papiers');
  };

  // Formatage
  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: 'XOF',
      minimumFractionDigits: 0
    }).format(price);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('fr-FR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const formatFileSize = (bytes: number) => {
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 Bytes';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  const getPropertyTypeLabel = (type: string) => {
    const types: { [key: string]: string } = {
      'residential': 'Résidentiel',
      'commercial': 'Commercial',
      'industrial': 'Industriel',
      'agricultural': 'Agricole',
      'vacant_land': 'Terrain nu',
      'other': 'Autre'
    };
    return types[type] || type;
  };

  const getStatusColor = (status: string) => {
    const colors: { [key: string]: string } = {
      'active': 'bg-green-100 text-green-800',
      'pending': 'bg-yellow-100 text-yellow-800',
      'inactive': 'bg-gray-100 text-gray-800',
      'sold': 'bg-blue-100 text-blue-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Chargement des détails...</span>
      </div>
    );
  }

  if (error || !property) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="h-16 w-16 text-red-400 mx-auto mb-4" />
        <h3 className="text-xl font-medium text-gray-900 mb-2">
          Erreur de chargement
        </h3>
        <p className="text-gray-600">{error}</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto bg-white">
      {/* Header */}
      <div className="border-b border-gray-200 pb-6 mb-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center mb-2">
              <h1 className="text-3xl font-bold text-gray-900 mr-4">
                {property.title}
              </h1>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(property.status)}`}>
                {property.status}
              </span>
              {property.verified && (
                <div className="ml-3 flex items-center text-green-600">
                  <CheckCircle className="h-5 w-5 mr-1" />
                  <span className="text-sm font-medium">Vérifiée</span>
                </div>
              )}
            </div>

            <div className="flex items-center text-gray-600 mb-4">
              <MapPin className="h-5 w-5 mr-2" />
              <span>{property.address}, {property.city}, {property.region}</span>
            </div>

            <div className="flex items-center space-x-6 text-sm text-gray-500">
              <div className="flex items-center">
                <Home className="h-4 w-4 mr-1" />
                <span>{getPropertyTypeLabel(property.property_type)}</span>
              </div>
              {property.area && (
                <div className="flex items-center">
                  <Layers className="h-4 w-4 mr-1" />
                  <span>{property.area.toLocaleString()} m²</span>
                </div>
              )}
              <div className="flex items-center">
                <Calendar className="h-4 w-4 mr-1" />
                <span>Enregistrée le {formatDate(property.registration_date)}</span>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={handleShare}
              className="flex items-center px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              <Share2 className="h-4 w-4 mr-2" />
              Partager
            </button>
            {canEdit && (
              <button
                onClick={() => onEdit?.(property)}
                className="flex items-center px-4 py-2 text-blue-700 border border-blue-300 rounded-lg hover:bg-blue-50"
              >
                <Edit className="h-4 w-4 mr-2" />
                Modifier
              </button>
            )}
            {canDelete && (
              <button
                onClick={() => onDelete?.(property.property_id)}
                className="flex items-center px-4 py-2 text-red-700 border border-red-300 rounded-lg hover:bg-red-50"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Supprimer
              </button>
            )}
          </div>
        </div>

        {property.price && (
          <div className="mt-4">
            <div className="text-3xl font-bold text-green-600">
              {formatPrice(property.price)}
            </div>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          {['details', 'documents', 'blockchain'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab as any)}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab === 'details' && 'Détails'}
              {tab === 'documents' && `Documents (${property.documents?.length || 0})`}
              {tab === 'blockchain' && 'Blockchain'}
            </button>
          ))}
        </nav>
      </div>

      {/* Contenu des tabs */}
      {activeTab === 'details' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Colonne principale */}
          <div className="lg:col-span-2 space-y-6">
            {/* Description */}
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-3">Description</h3>
              <p className="text-gray-600 leading-relaxed">{property.description}</p>
            </div>

            {/* Caractéristiques */}
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-3">Caractéristiques</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 p-4 rounded-lg">
                  <div className="text-sm text-gray-500">Type</div>
                  <div className="font-medium">{getPropertyTypeLabel(property.property_type)}</div>
                </div>
                {property.area && (
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <div className="text-sm text-gray-500">Superficie</div>
                    <div className="font-medium">{property.area.toLocaleString()} m²</div>
                  </div>
                )}
                <div className="bg-gray-50 p-4 rounded-lg">
                  <div className="text-sm text-gray-500">Statut</div>
                  <div className="font-medium">{property.status}</div>
                </div>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <div className="text-sm text-gray-500">Vérification</div>
                  <div className={`font-medium ${property.verified ? 'text-green-600' : 'text-yellow-600'}`}>
                    {property.verified ? 'Vérifiée' : 'En attente'}
                  </div>
                </div>
              </div>
            </div>

            {/* Carte */}
            {property.latitude && property.longitude && (
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-3">Localisation</h3>
                <div className="bg-gray-100 h-64 rounded-lg flex items-center justify-center">
                  <div className="text-center text-gray-500">
                    <MapPin className="h-8 w-8 mx-auto mb-2" />
                    <p>Carte interactive</p>
                    <p className="text-sm">
                      {property.latitude.toFixed(6)}, {property.longitude.toFixed(6)}
                    </p>
                    <button
                      onClick={() => copyToClipboard(`${property.latitude},${property.longitude}`)}
                      className="mt-2 text-blue-600 hover:text-blue-800 text-sm"
                    >
                      Copier les coordonnées
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Informations du propriétaire */}
            <div className="bg-gray-50 p-6 rounded-lg">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Propriétaire</h3>
              <div className="space-y-3">
                {property.owner_name && (
                  <div className="flex items-center">
                    <User className="h-4 w-4 text-gray-400 mr-3" />
                    <span>{property.owner_name}</span>
                  </div>
                )}
                {property.owner_contact && showContactInfo && (
                  <>
                    <div className="flex items-center">
                      <Phone className="h-4 w-4 text-gray-400 mr-3" />
                      <span>{property.owner_contact}</span>
                    </div>
                    <button
                      onClick={() => copyToClipboard(property.owner_contact!)}
                      className="flex items-center text-blue-600 hover:text-blue-800 text-sm"
                    >
                      <Copy className="h-4 w-4 mr-1" />
                      Copier le contact
                    </button>
                  </>
                )}
                {property.owner_contact && !showContactInfo && (
                  <button
                    onClick={() => setShowContactInfo(true)}
                    className="text-blue-600 hover:text-blue-800 text-sm"
                  >
                    Voir les informations de contact
                  </button>
                )}
              </div>
            </div>

            {/* Dates importantes */}
            <div className="bg-gray-50 p-6 rounded-lg">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Dates importantes</h3>
              <div className="space-y-3">
                <div>
                  <div className="text-sm text-gray-500">Enregistrement</div>
                  <div className="font-medium">{formatDate(property.registration_date)}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Dernière mise à jour</div>
                  <div className="font-medium">{formatDate(property.last_updated)}</div>
                </div>
                {property.verification_date && (
                  <div>
                    <div className="text-sm text-gray-500">Vérification</div>
                    <div className="font-medium">{formatDate(property.verification_date)}</div>
                    {property.verifier_name && (
                      <div className="text-sm text-gray-500">Par {property.verifier_name}</div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'documents' && (
        <div>
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-gray-900">
              Documents ({property.documents?.length || 0})
            </h3>
            {canEdit && (
              <button className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                <Upload className="h-4 w-4 mr-2" />
                Ajouter un document
              </button>
            )}
          </div>

          {property.documents && property.documents.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {property.documents.map((doc) => (
                <div key={doc.document_id} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center">
                      <FileText className="h-8 w-8 text-blue-600 mr-3" />
                      <div>
                        <h4 className="font-medium text-gray-900">{doc.title}</h4>
                        <p className="text-sm text-gray-500">{doc.filename}</p>
                      </div>
                    </div>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      doc.verification_status === 'approved' ? 'bg-green-100 text-green-800' :
                      doc.verification_status === 'rejected' ? 'bg-red-100 text-red-800' :
                      'bg-yellow-100 text-yellow-800'
                    }`}>
                      {doc.verification_status}
                    </span>
                  </div>

                  <div className="text-sm text-gray-500 mb-3">
                    <div>Taille: {formatFileSize(doc.size)}</div>
                    <div>Ajouté le {formatDate(doc.upload_timestamp)}</div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => handleDownloadDocument(doc.document_id, doc.filename)}
                      className="flex items-center px-3 py-1 text-blue-600 border border-blue-300 rounded hover:bg-blue-50 text-sm"
                    >
                      <Download className="h-3 w-3 mr-1" />
                      Télécharger
                    </button>
                    <button className="flex items-center px-3 py-1 text-gray-600 border border-gray-300 rounded hover:bg-gray-50 text-sm">
                      <Eye className="h-3 w-3 mr-1" />
                      Aperçu
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <FileText className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">Aucun document disponible</p>
            </div>
          )}
        </div>
      )}

      {activeTab === 'blockchain' && (
        <div className="space-y-6">
          <div className="bg-gradient-to-r from-blue-50 to-purple-50 p-6 rounded-lg">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
              <Shield className="h-5 w-5 mr-2 text-blue-600" />
              Informations Blockchain
            </h3>
            
            {property.blockchain_hash ? (
              <div className="space-y-4">
                <div>
                  <div className="text-sm text-gray-500">Hash de transaction</div>
                  <div className="font-mono text-sm bg-white p-2 rounded border flex items-center justify-between">
                    <span className="truncate">{property.blockchain_hash}</span>
                    <button
                      onClick={() => copyToClipboard(property.blockchain_hash!)}
                      className="ml-2 text-blue-600 hover:text-blue-800"
                    >
                      <Copy className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                {blockchainInfo && (
                  <>
                    <div>
                      <div className="text-sm text-gray-500">Statut sur la blockchain</div>
                      <div className="font-medium text-green-600">Confirmé</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-500">Bloc</div>
                      <div className="font-medium">{blockchainInfo.block_number}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-500">Réseau</div>
                      <div className="font-medium">CELO {blockchainInfo.network}</div>
                    </div>
                  </>
                )}

                <button className="flex items-center text-blue-600 hover:text-blue-800">
                  <ExternalLink className="h-4 w-4 mr-2" />
                  Voir sur l'explorateur de blocs
                </button>
              </div>
            ) : (
              <div className="text-center py-8">
                <AlertCircle className="h-12 w-12 text-yellow-400 mx-auto mb-4" />
                <p className="text-gray-600 mb-2">Cette propriété n'est pas encore enregistrée sur la blockchain</p>
                <p className="text-sm text-gray-500">L'enregistrement blockchain est en cours de traitement</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default PropertyDetails;