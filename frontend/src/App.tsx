import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from 'react-query';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import 'leaflet/dist/leaflet.css';

// Components
import Layout from './components/Layout';
import HomePage from './pages/HomePage';
import PropertiesPage from './pages/PropertiesPage';
import { 
  PropertyDetailsPage, 
  RegisterPropertyPage, 
  SearchPage, 
  MapPage, 
  ProfilePage, 
  DashboardPage 
} from './pages';

// Providers
import { Web3Provider } from './contexts/Web3Context';
import { AuthProvider } from './contexts/AuthContext';

// CSS
import './index.css';

// Configuration React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Web3Provider>
        <AuthProvider>
          <Router>
            <div className="App min-h-screen bg-gray-50">
              <Layout>
                <Routes>
                  {/* Route principale */}
                  <Route path="/" element={<HomePage />} />
                  
                  {/* Routes des propriétés */}
                  <Route path="/properties" element={<PropertiesPage />} />
                  <Route path="/properties/:id" element={<PropertyDetailsPage />} />
                  <Route path="/register" element={<RegisterPropertyPage />} />
                  
                  {/* Recherche et carte */}
                  <Route path="/search" element={<SearchPage />} />
                  <Route path="/map" element={<MapPage />} />
                  
                  {/* Pages utilisateur */}
                  <Route path="/profile" element={<ProfilePage />} />
                  <Route path="/dashboard" element={<DashboardPage />} />
                  
                  {/* Route 404 */}
                  <Route path="*" element={
                    <div className="flex items-center justify-center min-h-screen">
                      <div className="text-center">
                        <h1 className="text-4xl font-bold text-gray-900 mb-4">404</h1>
                        <p className="text-gray-600 mb-8">Page non trouvée</p>
                        <a 
                          href="/" 
                          className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg transition-colors"
                        >
                          Retour à l'accueil
                        </a>
                      </div>
                    </div>
                  } />
                </Routes>
              </Layout>
              
              {/* Notifications Toast */}
              <ToastContainer
                position="top-right"
                autoClose={5000}
                hideProgressBar={false}
                newestOnTop={false}
                closeOnClick
                rtl={false}
                pauseOnFocusLoss
                draggable
                pauseOnHover
                theme="light"
              />
            </div>
          </Router>
        </AuthProvider>
      </Web3Provider>
    </QueryClientProvider>
  );
}

export default App;
