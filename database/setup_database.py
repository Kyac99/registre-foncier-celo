#!/usr/bin/env python3
"""
Script de configuration initiale de la base de données PostgreSQL avec PostGIS
pour le Registre Foncier Décentralisé
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

# Configuration de la base de données
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'user': os.getenv('DB_USER', 'rfd_user'),
    'password': os.getenv('DB_PASSWORD', 'rfd_password'),
    'database': os.getenv('DB_NAME', 'registre_foncier')
}

def create_database():
    """Crée la base de données si elle n'existe pas"""
    try:
        # Connexion à PostgreSQL (base postgres par défaut)
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database='postgres'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Vérification si la base existe
        cursor.execute(
            "SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s",
            (DB_CONFIG['database'],)
        )
        exists = cursor.fetchone()

        if not exists:
            print(f"📦 Création de la base de données '{DB_CONFIG['database']}'...")
            cursor.execute(f"CREATE DATABASE {DB_CONFIG['database']}")
            print("✅ Base de données créée avec succès")
        else:
            print(f"ℹ️ La base de données '{DB_CONFIG['database']}' existe déjà")

        cursor.close()
        conn.close()

    except psycopg2.Error as e:
        print(f"❌ Erreur lors de la création de la base : {e}")
        sys.exit(1)

def setup_extensions():
    """Configure les extensions nécessaires (PostGIS, etc.)"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        print("🗂️ Configuration des extensions...")

        # Extension PostGIS pour les données géospatiales
        cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis_topology;")
        
        # Extension pour les UUID
        cursor.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
        
        # Extension pour le chiffrement
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

        conn.commit()
        print("✅ Extensions configurées avec succès")

        cursor.close()
        conn.close()

    except psycopg2.Error as e:
        print(f"❌ Erreur lors de la configuration des extensions : {e}")
        sys.exit(1)

def create_tables():
    """Crée les tables principales"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        print("🏗️ Création des tables...")

        # Table des utilisateurs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                wallet_address VARCHAR(42) UNIQUE NOT NULL,
                email VARCHAR(255),
                first_name VARCHAR(100),
                last_name VARCHAR(100),
                phone VARCHAR(20),
                role VARCHAR(50) DEFAULT 'citizen',
                is_verified BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)

        # Table des propriétés (cache de la blockchain)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS properties (
                id BIGSERIAL PRIMARY KEY,
                blockchain_id BIGINT UNIQUE NOT NULL,
                owner_address VARCHAR(42) NOT NULL,
                location TEXT NOT NULL,
                coordinates GEOMETRY(POLYGON, 4326),
                area DECIMAL(15, 2) NOT NULL,
                value DECIMAL(20, 2),
                property_type VARCHAR(50) NOT NULL,
                status VARCHAR(50) DEFAULT 'ACTIVE',
                registration_date TIMESTAMP WITH TIME ZONE,
                last_transfer_date TIMESTAMP WITH TIME ZONE,
                document_hash VARCHAR(100),
                ipfs_hash VARCHAR(100),
                registrar_address VARCHAR(42),
                is_verified BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)

        # Table de l'historique des transactions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS property_transactions (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                property_id BIGINT REFERENCES properties(id),
                transaction_hash VARCHAR(66) UNIQUE NOT NULL,
                from_address VARCHAR(42),
                to_address VARCHAR(42) NOT NULL,
                transaction_type VARCHAR(50) NOT NULL,
                value DECIMAL(20, 2),
                gas_used BIGINT,
                gas_price DECIMAL(20, 2),
                block_number BIGINT,
                transaction_date TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)

        # Table des documents IPFS
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                property_id BIGINT REFERENCES properties(id),
                document_type VARCHAR(50) NOT NULL,
                file_name VARCHAR(255) NOT NULL,
                file_size BIGINT,
                mime_type VARCHAR(100),
                ipfs_hash VARCHAR(100) UNIQUE NOT NULL,
                encryption_key VARCHAR(100),
                uploaded_by VARCHAR(42),
                is_public BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)

        # Table des recherches et indexation
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS property_search (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                property_id BIGINT REFERENCES properties(id),
                search_vector TSVECTOR,
                keywords TEXT[],
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)

        # Table des événements blockchain
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blockchain_events (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                event_type VARCHAR(50) NOT NULL,
                contract_address VARCHAR(42) NOT NULL,
                transaction_hash VARCHAR(66) NOT NULL,
                block_number BIGINT NOT NULL,
                event_data JSONB,
                processed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)

        conn.commit()
        print("✅ Tables créées avec succès")

        cursor.close()
        conn.close()

    except psycopg2.Error as e:
        print(f"❌ Erreur lors de la création des tables : {e}")
        sys.exit(1)

def create_indexes():
    """Crée les index pour optimiser les performances"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        print("📊 Création des index...")

        # Index pour les recherches fréquentes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_properties_owner ON properties(owner_address);",
            "CREATE INDEX IF NOT EXISTS idx_properties_location ON properties USING GIN(to_tsvector('french', location));",
            "CREATE INDEX IF NOT EXISTS idx_properties_coordinates ON properties USING GIST(coordinates);",
            "CREATE INDEX IF NOT EXISTS idx_properties_blockchain_id ON properties(blockchain_id);",
            "CREATE INDEX IF NOT EXISTS idx_transactions_property ON property_transactions(property_id);",
            "CREATE INDEX IF NOT EXISTS idx_transactions_hash ON property_transactions(transaction_hash);",
            "CREATE INDEX IF NOT EXISTS idx_documents_property ON documents(property_id);",
            "CREATE INDEX IF NOT EXISTS idx_documents_ipfs ON documents(ipfs_hash);",
            "CREATE INDEX IF NOT EXISTS idx_events_processed ON blockchain_events(processed);",
            "CREATE INDEX IF NOT EXISTS idx_events_block ON blockchain_events(block_number);",
            "CREATE INDEX IF NOT EXISTS idx_search_vector ON property_search USING GIN(search_vector);",
            "CREATE INDEX IF NOT EXISTS idx_users_wallet ON users(wallet_address);"
        ]

        for index_query in indexes:
            cursor.execute(index_query)

        conn.commit()
        print("✅ Index créés avec succès")

        cursor.close()
        conn.close()

    except psycopg2.Error as e:
        print(f"❌ Erreur lors de la création des index : {e}")
        sys.exit(1)

def create_triggers():
    """Crée les triggers pour la mise à jour automatique"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        print("⚡ Création des triggers...")

        # Fonction pour mettre à jour updated_at
        cursor.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """)

        # Triggers pour updated_at
        tables_with_updated_at = ['users', 'properties']
        for table in tables_with_updated_at:
            cursor.execute(f"""
                DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};
                CREATE TRIGGER update_{table}_updated_at
                    BEFORE UPDATE ON {table}
                    FOR EACH ROW
                    EXECUTE FUNCTION update_updated_at_column();
            """)

        # Trigger pour la recherche full-text
        cursor.execute("""
            CREATE OR REPLACE FUNCTION update_property_search()
            RETURNS TRIGGER AS $$
            BEGIN
                INSERT INTO property_search (property_id, search_vector, keywords)
                VALUES (
                    NEW.id,
                    to_tsvector('french', COALESCE(NEW.location, '') || ' ' || COALESCE(NEW.property_type, '')),
                    string_to_array(LOWER(COALESCE(NEW.location, '') || ' ' || COALESCE(NEW.property_type, '')), ' ')
                )
                ON CONFLICT (property_id) DO UPDATE SET
                    search_vector = to_tsvector('french', COALESCE(NEW.location, '') || ' ' || COALESCE(NEW.property_type, '')),
                    keywords = string_to_array(LOWER(COALESCE(NEW.location, '') || ' ' || COALESCE(NEW.property_type, '')), ' ');
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """)

        cursor.execute("""
            DROP TRIGGER IF EXISTS update_property_search_trigger ON properties;
            CREATE TRIGGER update_property_search_trigger
                AFTER INSERT OR UPDATE ON properties
                FOR EACH ROW
                EXECUTE FUNCTION update_property_search();
        """)

        conn.commit()
        print("✅ Triggers créés avec succès")

        cursor.close()
        conn.close()

    except psycopg2.Error as e:
        print(f"❌ Erreur lors de la création des triggers : {e}")
        sys.exit(1)

def insert_sample_data():
    """Insère des données d'exemple pour les tests"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        print("📝 Insertion des données d'exemple...")

        # Utilisateur admin de test
        cursor.execute("""
            INSERT INTO users (wallet_address, email, first_name, last_name, role, is_verified)
            VALUES ('0x1234567890123456789012345678901234567890', 'admin@rfd.local', 'Admin', 'Test', 'admin', TRUE)
            ON CONFLICT (wallet_address) DO NOTHING;
        """)

        # Notaire de test
        cursor.execute("""
            INSERT INTO users (wallet_address, email, first_name, last_name, role, is_verified)
            VALUES ('0xABCDEF1234567890123456789012345678901234', 'notaire@rfd.local', 'Jean', 'Notaire', 'notary', TRUE)
            ON CONFLICT (wallet_address) DO NOTHING;
        """)

        conn.commit()
        print("✅ Données d'exemple insérées")

        cursor.close()
        conn.close()

    except psycopg2.Error as e:
        print(f"❌ Erreur lors de l'insertion des données : {e}")
        sys.exit(1)

def main():
    """Fonction principale"""
    print("🚀 Configuration de la base de données pour le Registre Foncier Décentralisé")
    print(f"📍 Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"🗄️ Base: {DB_CONFIG['database']}")
    print(f"👤 Utilisateur: {DB_CONFIG['user']}")

    try:
        create_database()
        setup_extensions()
        create_tables()
        create_indexes()
        create_triggers()
        insert_sample_data()

        print("\\n🎉 Configuration de la base de données terminée avec succès!")
        print("\\n📋 Prochaines étapes:")
        print("1. Vérifiez la connexion depuis votre application")
        print("2. Configurez les variables d'environnement si nécessaire")
        print("3. Lancez les tests pour valider la configuration")

    except Exception as e:
        print(f"\\n❌ Erreur fatale : {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
