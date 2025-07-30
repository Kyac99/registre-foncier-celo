import React from 'react';

// Pages de base pour compléter le routing
// Ces pages pourront être développées plus tard

export const PropertyDetailsPage: React.FC = () => {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Détails de la propriété</h1>
      <div className="bg-white rounded-lg shadow p-6">
        <p className="text-gray-600">
          Page en cours de développement. Cette page affichera les détails complets d'une propriété 
          incluant la carte, les documents, l'historique des transactions, etc.
        </p>
      </div>
    </div>
  );
};

export const RegisterPropertyPage: React.FC = () => {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Enregistrer une propriété</h1>
      <div className="bg-white rounded-lg shadow p-6">
        <p className="text-gray-600 mb-4">
          Page en cours de développement. Cette page permettra aux notaires d'enregistrer 
          de nouvelles propriétés sur la blockchain.
        </p>
        <p className="text-sm text-gray-500">
          Fonctionnalités prévues : formulaire d'enregistrement, upload de documents, 
          géolocalisation, validation, signature blockchain.
        </p>
      </div>
    </div>
  );
};

export const SearchPage: React.FC = () => {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Recherche avancée</h1>
      <div className="bg-white rounded-lg shadow p-6">
        <p className="text-gray-600 mb-4">
          Page en cours de développement. Cette page offrira une recherche avancée 
          avec filtres géographiques et critères multiples.
        </p>
        <p className="text-sm text-gray-500">
          Fonctionnalités prévues : recherche textuelle, filtres par type/statut/prix, 
          recherche géospatiale, sauvegarde de recherches.
        </p>
      </div>
    </div>
  );
};

export const MapPage: React.FC = () => {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Carte interactive</h1>
      <div className="bg-white rounded-lg shadow p-6 h-96">
        <p className="text-gray-600 mb-4">
          Page en cours de développement. Cette page affichera une carte interactive 
          avec toutes les propriétés géolocalisées.
        </p>
        <p className="text-sm text-gray-500">
          Fonctionnalités prévues : carte Leaflet, marqueurs cliquables, couches par type, 
          recherche sur carte, popup détails.
        </p>
      </div>
    </div>
  );
};

export const ProfilePage: React.FC = () => {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Mon profil</h1>
      <div className="bg-white rounded-lg shadow p-6">
        <p className="text-gray-600 mb-4">
          Page en cours de développement. Cette page permettra aux utilisateurs 
          de gérer leur profil et leurs paramètres.
        </p>
        <p className="text-sm text-gray-500">
          Fonctionnalités prévues : informations personnelles, historique d'activité, 
          préférences, sécurité.
        </p>
      </div>
    </div>
  );
};

export const DashboardPage: React.FC = () => {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Tableau de bord</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-2">Mes propriétés</h2>
          <p className="text-gray-600">
            Gérez vos propriétés enregistrées
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-2">Activité récente</h2>
          <p className="text-gray-600">
            Consultez votre activité récente
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-2">Statistiques</h2>
          <p className="text-gray-600">
            Analysez vos données
          </p>
        </div>
      </div>
    </div>
  );
};
