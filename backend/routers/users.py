"""
Routeur API pour la gestion des utilisateurs
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime

from config.database import get_database, cache_manager
from models import User
from middleware.auth import verify_token, get_current_user
from services.auth import AuthService

router = APIRouter()

# Schémas Pydantic
class UserCreate(BaseModel):
    """Schéma pour créer un utilisateur"""
    wallet_address: str = Field(..., regex=r"^0x[a-fA-F0-9]{40}$")
    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)

class UserUpdate(BaseModel):
    """Schéma pour mettre à jour un utilisateur"""
    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)

class UserResponse(BaseModel):
    """Schéma de réponse pour un utilisateur"""
    id: str
    wallet_address: str
    first_name: Optional[str]
    last_name: Optional[str]
    full_name: str
    role: str
    is_verified: bool
    is_active: bool
    created_at: datetime

# Services
async def get_auth_service() -> AuthService:
    return AuthService()

# Endpoints

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_database)
):
    """
    Enregistre un nouvel utilisateur
    """
    try:
        # Vérification si l'utilisateur existe déjà
        existing_query = select(User).where(User.wallet_address == user_data.wallet_address)
        existing_user = await db.execute(existing_query)
        if existing_user.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Un utilisateur avec cette adresse wallet existe déjà"
            )
        
        # Vérification de l'email si fourni
        if user_data.email:
            email_query = select(User).where(User.email == user_data.email)
            existing_email = await db.execute(email_query)
            if existing_email.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Un utilisateur avec cet email existe déjà"
                )
        
        # Création du nouvel utilisateur
        new_user = User(
            wallet_address=user_data.wallet_address,
            email=user_data.email,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone=user_data.phone,
            role="citizen",  # Rôle par défaut
            is_verified=False,
            is_active=True
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        return UserResponse(**new_user.to_dict())
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'enregistrement: {str(e)}"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Récupère les informations de l'utilisateur connecté
    """
    return UserResponse(**current_user.to_dict())

@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """
    Met à jour les informations de l'utilisateur connecté
    """
    try:
        # Vérification de l'email si modifié
        if user_update.email and user_update.email != current_user.email:
            email_query = select(User).where(
                User.email == user_update.email,
                User.id != current_user.id
            )
            existing_email = await db.execute(email_query)
            if existing_email.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Un utilisateur avec cet email existe déjà"
                )
        
        # Mise à jour des champs
        update_data = user_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(current_user, field, value)
        
        await db.commit()
        await db.refresh(current_user)
        
        return UserResponse(**current_user.to_dict())
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la mise à jour: {str(e)}"
        )

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_database)
):
    """
    Récupère un utilisateur par son ID
    """
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    return UserResponse(**user.to_dict())

@router.get("/wallet/{wallet_address}", response_model=UserResponse)
async def get_user_by_wallet(
    wallet_address: str,
    db: AsyncSession = Depends(get_database)
):
    """
    Récupère un utilisateur par son adresse wallet
    """
    query = select(User).where(User.wallet_address == wallet_address)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    return UserResponse(**user.to_dict())

@router.post("/auth/nonce")
async def get_auth_nonce(
    wallet_address: str,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Génère un nonce pour l'authentification Web3
    """
    nonce = await auth_service.generate_nonce(wallet_address)
    return {"nonce": nonce}

@router.post("/auth/verify")
async def verify_signature(
    wallet_address: str,
    signature: str,
    nonce: str,
    db: AsyncSession = Depends(get_database),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Vérifie la signature Web3 et retourne un token JWT
    """
    try:
        # Vérification de la signature
        is_valid = await auth_service.verify_signature(wallet_address, signature, nonce)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Signature invalide"
            )
        
        # Récupération ou création de l'utilisateur
        query = select(User).where(User.wallet_address == wallet_address)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            # Création automatique d'un utilisateur basique
            user = User(
                wallet_address=wallet_address,
                role="citizen",
                is_verified=False,
                is_active=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        
        # Mise à jour de la dernière connexion
        user.last_login = datetime.utcnow()
        await db.commit()
        
        # Génération du token JWT
        token = await auth_service.create_access_token(wallet_address)
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": UserResponse(**user.to_dict())
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur d'authentification: {str(e)}"
        )
