import React from 'react';
import { WalletIcon } from '@heroicons/react/24/outline';
import { useWeb3 } from '../contexts/Web3Context';

const WalletConnectButton: React.FC = () => {
  const { 
    account, 
    isConnected, 
    isConnecting, 
    connectWallet, 
    disconnectWallet,
    chainId,
    networkInfo
  } = useWeb3();

  const isCorrectNetwork = chainId === networkInfo.chainId;

  if (isConnected && account) {
    return (
      <div className="flex items-center space-x-2">
        {/* Indicateur de réseau */}
        <div className={`w-2 h-2 rounded-full ${
          isCorrectNetwork ? 'bg-green-500' : 'bg-red-500'
        }`} />
        
        {/* Bouton compte */}
        <button
          onClick={disconnectWallet}
          className="flex items-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 rounded-md text-sm font-medium transition-colors"
          title={`${account}\nCliquer pour déconnecter`}
        >
          <WalletIcon className="w-4 h-4" />
          <span className="hidden sm:block">
            {`${account.slice(0, 6)}...${account.slice(-4)}`}
          </span>
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={connectWallet}
      disabled={isConnecting}
      className="flex items-center space-x-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
    >
      <WalletIcon className="w-4 h-4" />
      <span>
        {isConnecting ? 'Connexion...' : 'Connecter Wallet'}
      </span>
    </button>
  );
};

export default WalletConnectButton;
