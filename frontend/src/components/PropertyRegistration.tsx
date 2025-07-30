import React, { useState, useCallback } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { MapPin, Upload, FileText, Check, AlertCircle, Loader2 } from 'lucide-react';

// Types
interface PropertyFormData {
  title: string;
  description: string;
  propertyType: string;
  area: number;
  price?: number;
  address: string;
  city: string;
  region: string;
  latitude?: number;
  longitude?: number;
  documents: FileList | null;
}

interface PropertyRegistrationProps {
  onSuccess?: (propertyId: string) => void;
  onError?: (error: string) => void;
}

// Schema de validation avec Zod
const propertySchema = z.object({
  title: z.string().min(3, 'Le titre doit contenir au moins 3 caractères'),
  description: z.string().min(10, 'La description doit contenir au moins 10 caractères'),
  propertyType: z.string().min(1, 'Veuillez sélectionner un type de propriété'),
  area: z.number().min(1, 'La superficie doit être supérieure à 0'),
  price: z.number().optional(),
  address: z.string().min(5, 'L\'adresse doit contenir au moins 5 caractères'),
  city: z.string().min(2, 'La ville doit contenir au moins 2 caractères'),
  region: z.string().min(2, 'La région doit contenir au moins 2 caractères'),
  latitude: z.number().optional(),
  longitude: z.number().optional(),
});

const PropertyRegistration: React.FC<PropertyRegistrationProps> = ({ onSuccess, onError }) => {
  const [currentStep, setCurrentStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [isGeolocating, setIsGeolocating] = useState(false);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors, isValid }
  } = useForm<PropertyFormData>({
    resolver: zodResolver(propertySchema),
    mode: 'onChange'
  });

  const propertyTypes = [
    { value: 'residential', label: 'Résidentiel' },
    { value: 'commercial', label: 'Commercial' },
    { value: 'industrial', label: 'Industriel' },
    { value: 'agricultural', label: 'Agricole' },
    { value: 'vacant_land', label: 'Terrain nu' },
    { value: 'other', label: 'Autre' }
  ];

  const regions = [
    'Centre',
    'Centre-Est',
    'Centre-Nord',
    'Centre-Ouest',
    'Centre-Sud',
    'Est',
    'Hauts-Bassins',
    'Nord',
    'Plateau-Central',
    'Sahel',
    'Sud-Ouest',
    'Boucle du Mouhoun',
    'Cascades'
  ];

  // Géolocalisation automatique
  const handleGeolocate = useCallback(async () => {
    if (!navigator.geolocation) {
      alert('La géolocalisation n\'est pas supportée par votre navigateur');
      return;
    }

    setIsGeolocating(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setValue('latitude', position.coords.latitude);
        setValue('longitude', position.coords.longitude);
        setIsGeolocating(false);
      },
      (error) => {
        console.error('Erreur de géolocalisation:', error);
        setIsGeolocating(false);
        alert('Impossible d\'obtenir votre position');
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }, [setValue]);

  // Gestion des fichiers
  const handleFileUpload = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files) {
      const fileArray = Array.from(files);
      setUploadedFiles(prev => [...prev, ...fileArray]);
    }
  }, []);

  const removeFile = useCallback((index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  }, []);

  // Soumission du formulaire
  const onSubmit = async (data: PropertyFormData) => {
    setIsSubmitting(true);
    
    try {
      // Préparation des données
      const formData = new FormData();
      
      // Données de la propriété
      Object.entries(data).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          formData.append(key, value.toString());
        }
      });

      // Ajout des fichiers
      uploadedFiles.forEach((file, index) => {
        formData.append(`document_${index}`, file);
      });

      // Envoi à l'API
      const response = await fetch('/api/v1/properties', {
        method: 'POST',
        body: formData,
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      });

      if (!response.ok) {
        throw new Error('Erreur lors de l\'enregistrement');
      }

      const result = await response.json();
      onSuccess?.(result.property_id);
      
    } catch (error) {
      console.error('Erreur:', error);
      onError?.(error instanceof Error ? error.message : 'Erreur inconnue');
    } finally {
      setIsSubmitting(false);
    }
  };

  const nextStep = () => {
    if (currentStep < 3) setCurrentStep(currentStep + 1);
  };

  const prevStep = () => {
    if (currentStep > 1) setCurrentStep(currentStep - 1);
  };

  const renderStep1 = () => (
    <div className="space-y-6">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Informations générales
        </h2>
        <p className="text-gray-600">
          Renseignez les informations de base de votre propriété
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Titre de la propriété *
          </label>
          <input
            {...register('title')}
            type="text"
            className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              errors.title ? 'border-red-300' : 'border-gray-300'
            }`}
            placeholder="Ex: Maison familiale à Ouagadougou"
          />
          {errors.title && (
            <p className="mt-1 text-sm text-red-600">{errors.title.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Type de propriété *
          </label>
          <select
            {...register('propertyType')}
            className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              errors.propertyType ? 'border-red-300' : 'border-gray-300'
            }`}
          >
            <option value="">Sélectionner un type</option>
            {propertyTypes.map(type => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
          {errors.propertyType && (
            <p className="mt-1 text-sm text-red-600">{errors.propertyType.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Superficie (m²) *
          </label>
          <input
            {...register('area', { valueAsNumber: true })}
            type="number"
            step="0.01"
            className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              errors.area ? 'border-red-300' : 'border-gray-300'
            }`}
            placeholder="Ex: 500"
          />
          {errors.area && (
            <p className="mt-1 text-sm text-red-600">{errors.area.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Prix (FCFA)
          </label>
          <input
            {...register('price', { valueAsNumber: true })}
            type="number"
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Ex: 25000000"
          />
        </div>

        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Description *
          </label>
          <textarea
            {...register('description')}
            rows={4}
            className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              errors.description ? 'border-red-300' : 'border-gray-300'
            }`}
            placeholder="Décrivez votre propriété..."
          />
          {errors.description && (
            <p className="mt-1 text-sm text-red-600">{errors.description.message}</p>
          )}
        </div>
      </div>
    </div>
  );

  const renderStep2 = () => (
    <div className="space-y-6">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Localisation
        </h2>
        <p className="text-gray-600">
          Précisez l'emplacement de votre propriété
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Adresse *
          </label>
          <input
            {...register('address')}
            type="text"
            className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              errors.address ? 'border-red-300' : 'border-gray-300'
            }`}
            placeholder="Ex: Secteur 15, Rue 15.15"
          />
          {errors.address && (
            <p className="mt-1 text-sm text-red-600">{errors.address.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Ville *
          </label>
          <input
            {...register('city')}
            type="text"
            className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              errors.city ? 'border-red-300' : 'border-gray-300'
            }`}
            placeholder="Ex: Ouagadougou"
          />
          {errors.city && (
            <p className="mt-1 text-sm text-red-600">{errors.city.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Région *
          </label>
          <select
            {...register('region')}
            className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              errors.region ? 'border-red-300' : 'border-gray-300'
            }`}
          >
            <option value="">Sélectionner une région</option>
            {regions.map(region => (
              <option key={region} value={region}>
                {region}
              </option>
            ))}
          </select>
          {errors.region && (
            <p className="mt-1 text-sm text-red-600">{errors.region.message}</p>
          )}
        </div>

        <div className="md:col-span-2">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center">
                <MapPin className="h-5 w-5 text-blue-600 mr-2" />
                <span className="text-sm font-medium text-blue-900">
                  Coordonnées GPS (Optionnel)
                </span>
              </div>
              <button
                type="button"
                onClick={handleGeolocate}
                disabled={isGeolocating}
                className="flex items-center px-3 py-1 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                {isGeolocating ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-1" />
                ) : (
                  <MapPin className="h-4 w-4 mr-1" />
                )}
                Géolocaliser
              </button>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-blue-700 mb-1">Latitude</label>
                <input
                  {...register('latitude', { valueAsNumber: true })}
                  type="number"
                  step="any"
                  className="w-full px-3 py-2 text-sm border border-blue-200 rounded focus:ring-1 focus:ring-blue-500"
                  placeholder="Ex: 12.3714"
                />
              </div>
              <div>
                <label className="block text-xs text-blue-700 mb-1">Longitude</label>
                <input
                  {...register('longitude', { valueAsNumber: true })}
                  type="number"
                  step="any"
                  className="w-full px-3 py-2 text-sm border border-blue-200 rounded focus:ring-1 focus:ring-blue-500"
                  placeholder="Ex: -1.5197"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const renderStep3 = () => (
    <div className="space-y-6">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Documents justificatifs
        </h2>
        <p className="text-gray-600">
          Ajoutez les documents relatifs à votre propriété
        </p>
      </div>

      <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
        <Upload className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <p className="text-gray-600 mb-4">
          Glissez-déposez vos fichiers ici ou cliquez pour sélectionner
        </p>
        <input
          type="file"
          multiple
          accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
          onChange={handleFileUpload}
          className="hidden"
          id="file-upload"
        />
        <label
          htmlFor="file-upload"
          className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 cursor-pointer"
        >
          <FileText className="h-4 w-4 mr-2" />
          Sélectionner des fichiers
        </label>
        <p className="text-xs text-gray-500 mt-2">
          PDF, JPG, PNG, DOC, DOCX - Max 10MB par fichier
        </p>
      </div>

      {uploadedFiles.length > 0 && (
        <div className="space-y-2">
          <h4 className="font-medium text-gray-900">Fichiers sélectionnés:</h4>
          {uploadedFiles.map((file, index) => (
            <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center">
                <FileText className="h-4 w-4 text-blue-600 mr-2" />
                <span className="text-sm text-gray-700">{file.name}</span>
                <span className="text-xs text-gray-500 ml-2">
                  ({(file.size / 1024 / 1024).toFixed(2)} MB)
                </span>
              </div>
              <button
                type="button"
                onClick={() => removeFile(index)}
                className="text-red-600 hover:text-red-800"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <div className="max-w-4xl mx-auto bg-white rounded-xl shadow-lg overflow-hidden">
      {/* Progress bar */}
      <div className="bg-gray-50 px-6 py-4">
        <div className="flex items-center justify-between mb-2">
          {[1, 2, 3].map((step) => (
            <div
              key={step}
              className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium ${
                step <= currentStep
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-600'
              }`}
            >
              {step < currentStep ? <Check className="h-4 w-4" /> : step}
            </div>
          ))}
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${(currentStep / 3) * 100}%` }}
          />
        </div>
      </div>

      {/* Form content */}
      <form onSubmit={handleSubmit(onSubmit)} className="p-6">
        {currentStep === 1 && renderStep1()}
        {currentStep === 2 && renderStep2()}
        {currentStep === 3 && renderStep3()}

        {/* Navigation buttons */}
        <div className="flex justify-between mt-8 pt-6 border-t border-gray-200">
          <button
            type="button"
            onClick={prevStep}
            disabled={currentStep === 1}
            className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Précédent
          </button>

          {currentStep < 3 ? (
            <button
              type="button"
              onClick={nextStep}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Suivant
            </button>
          ) : (
            <button
              type="submit"
              disabled={isSubmitting || !isValid}
              className="flex items-center px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Enregistrement...
                </>
              ) : (
                <>
                  <Check className="h-4 w-4 mr-2" />
                  Enregistrer la propriété
                </>
              )}
            </button>
          )}
        </div>
      </form>
    </div>
  );
};

export default PropertyRegistration;