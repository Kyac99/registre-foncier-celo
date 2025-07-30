import axios, { AxiosInstance, AxiosResponse } from 'axios';

// Configuration de base
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Types
interface Property {
  id: number;
  blockchain_id: number;
  owner_address: string;
  location: string;
  coordinates?: any;
  area: number;
  value?: number;
  property_type: string;
  status: string;
  registration_date?: string;
  last_transfer_date?: string;
  document_hash?: string;
  ipfs_hash?: string;
  registrar_address?: string;
  is_verified: boolean;
  verified_by?: string;
  verification_date?: string;
  created_at: string;
  updated_at: string;
}

interface User {
  id: string;
  wallet_address: string;
  first_name?: string;
  last_name?: string;
  full_name: string;
  email?: string;
  role: string;
  is_verified: boolean;
  is_active: boolean;
  permissions: {
    can_register_property: boolean;
    can_verify_property: boolean;
    can_manage_users: boolean;
  };
  created_at: string;
}

interface PropertyFilters {
  skip?: number;
  limit?: number;
  property_type?: string;
  status?: string;
  owner_address?: string;
  verified_only?: boolean;
}

interface PropertyListResponse {
  properties: Property[];
  total: number;
  skip: number;
  limit: number;
}

interface PropertyStats {
  total_properties: number;
  verified_properties: number;
  unique_owners: number;
  total_area: number;
  average_area: number;
  by_type: Record<string, number>;
}

interface GeospatialSearch {
  latitude: number;
  longitude: number;
  radius_km: number;
}

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Intercepteur pour ajouter le token d'authentification
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('auth_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Intercepteur pour gérer les erreurs de réponse
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Token expiré ou invalide
          localStorage.removeItem('auth_token');
          window.location.href = '/';
        }
        return Promise.reject(error);
      }
    );
  }

  // === Méthodes génériques ===
  private async handleResponse<T>(promise: Promise<AxiosResponse<T>>): Promise<T> {
    try {
      const response = await promise;
      return response.data;
    } catch (error: any) {
      console.error('API Error:', error);
      throw new Error(error.response?.data?.detail || error.message || 'Erreur API');
    }
  }

  // === Authentification ===
  async authenticateUser(data: {
    wallet_address: string;
    message: string;
    signature: string;
  }): Promise<{ success: boolean; token?: string }> {
    return this.handleResponse(
      this.client.post('/api/v1/auth/authenticate', data)
    );
  }

  // === Utilisateurs ===
  async getUserByWallet(walletAddress: string): Promise<User | null> {
    try {
      return await this.handleResponse(
        this.client.get(`/api/v1/users/wallet/${walletAddress}`)
      );
    } catch (error) {
      if (error.message.includes('404')) {
        return null;
      }
      throw error;
    }
  }

  async createUser(data: {
    wallet_address: string;
    role: string;
    first_name?: string;
    last_name?: string;
    email?: string;
  }): Promise<User> {
    return this.handleResponse(
      this.client.post('/api/v1/users/', data)
    );
  }

  async updateUser(userId: string, data: Partial<User>): Promise<User> {
    return this.handleResponse(
      this.client.put(`/api/v1/users/${userId}`, data)
    );
  }

  async getCurrentUser(): Promise<User> {
    return this.handleResponse(
      this.client.get('/api/v1/users/me')
    );
  }

  // === Propriétés ===
  async getProperties(filters: PropertyFilters = {}): Promise<PropertyListResponse> {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined) {
        params.append(key, value.toString());
      }
    });

    return this.handleResponse(
      this.client.get(`/api/v1/properties/?${params.toString()}`)
    );
  }

  async getProperty(propertyId: number): Promise<Property> {
    return this.handleResponse(
      this.client.get(`/api/v1/properties/${propertyId}`)
    );
  }

  async createProperty(formData: FormData): Promise<Property> {
    return this.handleResponse(
      this.client.post('/api/v1/properties/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
    );
  }

  async verifyProperty(propertyId: number, verified: boolean): Promise<Property> {
    const formData = new FormData();
    formData.append('verified', verified.toString());

    return this.handleResponse(
      this.client.put(`/api/v1/properties/${propertyId}/verify`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
    );
  }

  async downloadPropertyDocument(propertyId: number): Promise<Blob> {
    const response = await this.client.get(
      `/api/v1/properties/${propertyId}/document`,
      {
        responseType: 'blob',
      }
    );
    return response.data;
  }

  async getPropertiesByOwner(
    ownerAddress: string,
    filters: PropertyFilters = {}
  ): Promise<PropertyListResponse> {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined) {
        params.append(key, value.toString());
      }
    });

    return this.handleResponse(
      this.client.get(`/api/v1/properties/owner/${ownerAddress}?${params.toString()}`)
    );
  }

  async searchPropertiesGeospatial(search: GeospatialSearch): Promise<{
    properties: Property[];
    search_center: { latitude: number; longitude: number };
    radius_km: number;
    total_found: number;
  }> {
    const params = new URLSearchParams({
      latitude: search.latitude.toString(),
      longitude: search.longitude.toString(),
      radius_km: search.radius_km.toString(),
    });

    return this.handleResponse(
      this.client.get(`/api/v1/properties/search/geospatial?${params.toString()}`)
    );
  }

  async getPropertyStats(): Promise<PropertyStats> {
    return this.handleResponse(
      this.client.get('/api/v1/properties/stats/summary')
    );
  }

  // === Recherche ===
  async searchProperties(query: string, filters: PropertyFilters = {}): Promise<PropertyListResponse> {
    const params = new URLSearchParams({
      q: query,
      ...Object.fromEntries(
        Object.entries(filters).map(([key, value]) => [key, value?.toString() || ''])
      ),
    });

    return this.handleResponse(
      this.client.get(`/api/v1/search/properties?${params.toString()}`)
    );
  }

  // === Blockchain ===
  async getNetworkInfo(): Promise<{
    network: string;
    connected: boolean;
    block_number: number;
    gas_price: number;
    account?: string;
    contract_address?: string;
  }> {
    return this.handleResponse(
      this.client.get('/api/v1/blockchain/network-info')
    );
  }

  async getBlockchainStats(): Promise<{
    total_transactions: number;
    total_properties: number;
    last_block: number;
    average_gas_price: number;
  }> {
    return this.handleResponse(
      this.client.get('/api/v1/blockchain/stats')
    );
  }

  // === Configuration ===
  async getPublicConfig(): Promise<{
    blockchain: {
      network: string;
      rpc_url: string;
      contract_address?: string;
    };
    ipfs: {
      gateway: string;
    };
    features: {
      registration: boolean;
      search: boolean;
      verification: boolean;
      documents: boolean;
    };
  }> {
    return this.handleResponse(
      this.client.get('/api/v1/config')
    );
  }

  // === Santé de l'API ===
  async healthCheck(): Promise<{
    status: string;
    database: string;
    blockchain_network: string;
    environment: string;
  }> {
    return this.handleResponse(
      this.client.get('/health')
    );
  }

  // === Utilitaires ===
  getApiUrl(): string {
    return API_BASE_URL;
  }

  setAuthToken(token: string): void {
    localStorage.setItem('auth_token', token);
  }

  clearAuthToken(): void {
    localStorage.removeItem('auth_token');
  }
}

// Instance globale
export const apiService = new ApiService();
export default apiService;
