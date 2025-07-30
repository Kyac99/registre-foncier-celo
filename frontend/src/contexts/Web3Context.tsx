import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { ethers } from 'ethers';
import { toast } from 'react-toastify';

// Types
interface Web3ContextType {
  // État de la connexion
  account: string | null;
  provider: ethers.BrowserProvider | null;
  signer: ethers.JsonRpcSigner | null;
  chainId: number | null;
  isConnecting: boolean;
  isConnected: boolean;
  
  // Fonctions
  connectWallet: () => Promise<void>;
  disconnectWallet: () => void;
  switchToCorrectNetwork: () => Promise<boolean>;
  
  // Contrat
  contract: ethers.Contract | null;
  
  // Informations réseau
  networkInfo: {
    name: string;
    chainId: number;
    rpcUrl: string;
    blockExplorer: string;
    nativeCurrency: {
      name: string;
      symbol: string;
      decimals: number;
    };
  };
}

interface Web3ProviderProps {
  children: ReactNode;
}

// Configuration réseau CELO
const CELO_NETWORKS = {
  alfajores: {
    name: 'Celo Alfajores Testnet',
    chainId: 44787,
    rpcUrl: 'https://alfajores-forno.celo-testnet.org',
    blockExplorer: 'https://alfajores.celoscan.io',
    nativeCurrency: {
      name: 'Celo',
      symbol: 'CELO',
      decimals: 18,
    },
  },
  mainnet: {
    name: 'Celo Mainnet',
    chainId: 42220,
    rpcUrl: 'https://forno.celo.org',
    blockExplorer: 'https://celoscan.io',
    nativeCurrency: {
      name: 'Celo',
      symbol: 'CELO',
      decimals: 18,
    },
  },
};

// Configuration actuelle (basée sur l'environnement)
const CURRENT_NETWORK = process.env.REACT_APP_CELO_NETWORK === 'mainnet' 
  ? CELO_NETWORKS.mainnet 
  : CELO_NETWORKS.alfajores;

// ABI du contrat LandRegistry (version simplifiée)
const LAND_REGISTRY_ABI = [
  "function registerProperty(address owner, string location, string coordinates, uint256 area, uint256 value, uint8 propertyType, string documentHash, string tokenURI) external returns (uint256)",
  "function getProperty(uint256 propertyId) external view returns (tuple(uint256 id, string location, string coordinates, uint256 area, uint256 value, uint8 propertyType, uint8 status, uint256 registrationDate, uint256 lastTransferDate, string documentHash, address registrar, bool verified))",
  "function getTotalProperties() external view returns (uint256)",
  "function getPropertiesByOwner(address owner) external view returns (uint256[])",
  "function transferProperty(uint256 propertyId, address newOwner, uint256 newValue) external",
  "function verifyProperty(uint256 propertyId, bool isVerified) external",
  "event PropertyRegistered(uint256 indexed propertyId, address indexed owner, string location, uint256 value, address registrar)",
  "event PropertyTransferred(uint256 indexed propertyId, address indexed from, address indexed to, uint256 value)"
];

const CONTRACT_ADDRESS = process.env.REACT_APP_CONTRACT_ADDRESS;

// Contexte
const Web3Context = createContext<Web3ContextType | undefined>(undefined);

export const useWeb3 = () => {
  const context = useContext(Web3Context);
  if (context === undefined) {
    throw new Error('useWeb3 must be used within a Web3Provider');
  }
  return context;
};

export const Web3Provider: React.FC<Web3ProviderProps> = ({ children }) => {
  const [account, setAccount] = useState<string | null>(null);
  const [provider, setProvider] = useState<ethers.BrowserProvider | null>(null);
  const [signer, setSigner] = useState<ethers.JsonRpcSigner | null>(null);
  const [chainId, setChainId] = useState<number | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [contract, setContract] = useState<ethers.Contract | null>(null);

  const isConnected = !!account;

  // Initialisation du contrat
  const initializeContract = (signerOrProvider: ethers.Signer | ethers.Provider) => {
    if (!CONTRACT_ADDRESS) {
      console.warn('Contract address not configured');
      return null;
    }

    try {
      const contractInstance = new ethers.Contract(
        CONTRACT_ADDRESS,
        LAND_REGISTRY_ABI,
        signerOrProvider
      );
      setContract(contractInstance);
      return contractInstance;
    } catch (error) {
      console.error('Error initializing contract:', error);
      return null;
    }
  };

  // Connexion au wallet
  const connectWallet = async () => {
    if (!window.ethereum) {
      toast.error('MetaMask ou un wallet compatible n\'est pas installé');
      return;
    }

    setIsConnecting(true);

    try {
      // Demande de connexion
      const accounts = await window.ethereum.request({
        method: 'eth_requestAccounts',
      });

      if (accounts.length === 0) {
        throw new Error('Aucun compte sélectionné');
      }

      // Création du provider
      const web3Provider = new ethers.BrowserProvider(window.ethereum);
      const web3Signer = await web3Provider.getSigner();
      const network = await web3Provider.getNetwork();

      setProvider(web3Provider);
      setSigner(web3Signer);
      setAccount(accounts[0]);
      setChainId(Number(network.chainId));

      // Vérification du réseau
      if (Number(network.chainId) !== CURRENT_NETWORK.chainId) {
        const switched = await switchToCorrectNetwork();
        if (!switched) {
          toast.warning('Veuillez changer de réseau pour utiliser l\'application');
          return;
        }
      }

      // Initialisation du contrat
      initializeContract(web3Signer);

      toast.success('Wallet connecté avec succès');
    } catch (error: any) {
      console.error('Error connecting wallet:', error);
      toast.error(`Erreur de connexion: ${error.message}`);
    } finally {
      setIsConnecting(false);
    }
  };

  // Déconnexion
  const disconnectWallet = () => {
    setAccount(null);
    setProvider(null);
    setSigner(null);
    setChainId(null);
    setContract(null);
    toast.info('Wallet déconnecté');
  };

  // Changement de réseau
  const switchToCorrectNetwork = async (): Promise<boolean> => {
    if (!window.ethereum) return false;

    try {
      // Tentative de changement de réseau
      await window.ethereum.request({
        method: 'wallet_switchEthereumChain',
        params: [{ chainId: `0x${CURRENT_NETWORK.chainId.toString(16)}` }],
      });
      return true;
    } catch (switchError: any) {
      // Si le réseau n'est pas ajouté, on l'ajoute
      if (switchError.code === 4902) {
        try {
          await window.ethereum.request({
            method: 'wallet_addEthereumChain',
            params: [
              {
                chainId: `0x${CURRENT_NETWORK.chainId.toString(16)}`,
                chainName: CURRENT_NETWORK.name,
                nativeCurrency: CURRENT_NETWORK.nativeCurrency,
                rpcUrls: [CURRENT_NETWORK.rpcUrl],
                blockExplorerUrls: [CURRENT_NETWORK.blockExplorer],
              },
            ],
          });
          return true;
        } catch (addError) {
          console.error('Error adding network:', addError);
          return false;
        }
      }
      console.error('Error switching network:', switchError);
      return false;
    }
  };

  // Gestion des événements du wallet
  useEffect(() => {
    if (!window.ethereum) return;

    const handleAccountsChanged = (accounts: string[]) => {
      if (accounts.length === 0) {
        disconnectWallet();
      } else if (accounts[0] !== account) {
        setAccount(accounts[0]);
        // Reconnexion automatique si le compte a changé
        if (provider && signer) {
          connectWallet();
        }
      }
    };

    const handleChainChanged = (chainId: string) => {
      const newChainId = parseInt(chainId, 16);
      setChainId(newChainId);
      
      if (newChainId !== CURRENT_NETWORK.chainId) {
        toast.warning('Réseau incorrect. Veuillez changer vers ' + CURRENT_NETWORK.name);
      } else {
        toast.success('Réseau correct configuré');
      }
    };

    const handleDisconnect = () => {
      disconnectWallet();
    };

    // Ajout des listeners
    window.ethereum.on('accountsChanged', handleAccountsChanged);
    window.ethereum.on('chainChanged', handleChainChanged);
    window.ethereum.on('disconnect', handleDisconnect);

    // Tentative de reconnexion automatique
    const tryAutoConnect = async () => {
      try {
        const accounts = await window.ethereum.request({
          method: 'eth_accounts',
        });
        if (accounts.length > 0) {
          await connectWallet();
        }
      } catch (error) {
        console.log('No previous connection found');
      }
    };

    tryAutoConnect();

    // Nettoyage
    return () => {
      if (window.ethereum) {
        window.ethereum.removeListener('accountsChanged', handleAccountsChanged);
        window.ethereum.removeListener('chainChanged', handleChainChanged);
        window.ethereum.removeListener('disconnect', handleDisconnect);
      }
    };
  }, []);

  const value: Web3ContextType = {
    account,
    provider,
    signer,
    chainId,
    isConnecting,
    isConnected,
    connectWallet,
    disconnectWallet,
    switchToCorrectNetwork,
    contract,
    networkInfo: CURRENT_NETWORK,
  };

  return <Web3Context.Provider value={value}>{children}</Web3Context.Provider>;
};

// Utilitaires pour les types globaux
declare global {
  interface Window {
    ethereum?: any;
  }
}

export default Web3Context;
