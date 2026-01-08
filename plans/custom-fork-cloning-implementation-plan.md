# Custom Fork Cloning Feature - Implementation Plan

## 📋 Executive Summary

This document outlines the implementation plan for adding **Custom Fork Cloning** capability to the Open WebUI Customizer, along with a comprehensive **Credential Management System**. This feature enables developers to customize their own forks of Open WebUI while maintaining the existing branding and pipeline capabilities.

> ⚠️ **EXPERIMENTAL FEATURE**: Custom fork cloning is an experimental feature. Compatibility with all forks cannot be guaranteed, and users should expect potential issues when using non-standard forks.

---

## 🎯 User Story

> As a developer who has forked the Open WebUI repository and implemented custom features, I want to:
> 1. Provide my repository URL (HTTPS or SSH)
> 2. Configure credentials for private repositories
> 3. Apply branding customizations to my fork
> 4. Receive either a compressed ZIP archive or a built Docker image
> 5. Optionally push the image to my configured registry

---

## 🏗️ Architecture Overview

### High-Level System Architecture

```mermaid
graph TB
    subgraph "User Interface"
        UI[Web UI]
        API[REST API]
    end
    
    subgraph "Credential Management"
        CM[Credential Manager]
        ENC[Encryption Service]
        KV[Key Vault]
    end
    
    subgraph "Source Control"
        GS[Git Service]
        SSH[SSH Handler]
        HTTPS[HTTPS Handler]
    end
    
    subgraph "Build Pipeline"
        PS[Pipeline Service]
        BS[Build Service]
        PKG[Packaging Service]
    end
    
    subgraph "Output"
        REG[Registry Push]
        ZIP[ZIP Export]
    end
    
    UI --> API
    API --> CM
    API --> GS
    API --> PS
    
    CM --> ENC
    CM --> KV
    
    GS --> SSH
    GS --> HTTPS
    
    PS --> BS
    BS --> PKG
    
    PKG --> REG
    PKG --> ZIP
```

### Data Flow for Custom Fork Cloning

```mermaid
sequenceDiagram
    participant U as User
    participant API as API Layer
    participant CM as Credential Manager
    participant GS as Git Service
    participant PS as Pipeline Service
    participant OUT as Output Service
    
    U->>API: Submit fork URL + credentials
    API->>CM: Store credentials securely
    CM-->>API: Credential ID
    
    U->>API: Start pipeline
    API->>CM: Retrieve credentials
    CM-->>API: Decrypted credentials
    
    API->>GS: Clone fork with credentials
    GS-->>API: Clone status
    
    API->>PS: Apply branding + build
    PS-->>API: Build artifacts
    
    API->>OUT: Package output
    OUT-->>U: ZIP download or Image URL
```

---

## 📊 Database Schema Changes

### New Tables

#### 1. `credentials` Table
Stores encrypted credentials for various services.

```sql
CREATE TABLE credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL UNIQUE,
    credential_type VARCHAR(50) NOT NULL,  -- 'git_ssh', 'git_https', 'registry_token', 'aws_keys'
    encrypted_data TEXT NOT NULL,          -- AES-256-GCM encrypted JSON
    encryption_key_id VARCHAR(255),        -- Reference to key version
    metadata JSON,                          -- Non-sensitive metadata
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NULL,               -- Optional expiration
    last_used_at DATETIME NULL
);
```

#### 2. `git_repositories` Table
Stores custom fork configurations.

```sql
CREATE TABLE git_repositories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL UNIQUE,
    repository_url VARCHAR(1024) NOT NULL,  -- HTTPS or SSH URL
    repository_type VARCHAR(20) NOT NULL,   -- 'https', 'ssh'
    default_branch VARCHAR(255) DEFAULT 'main',
    credential_id INTEGER NULL,             -- FK to credentials table
    is_verified BOOLEAN DEFAULT FALSE,      -- Has the repo been successfully cloned?
    verification_status VARCHAR(50),        -- 'pending', 'success', 'failed'
    verification_message TEXT,
    is_experimental BOOLEAN DEFAULT TRUE,   -- Custom forks are always experimental
    metadata JSON,                          -- Additional repo metadata
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (credential_id) REFERENCES credentials(id) ON DELETE SET NULL
);
```

#### 3. `build_outputs` Table
Tracks generated build artifacts.

```sql
CREATE TABLE build_outputs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_run_id INTEGER NOT NULL,
    output_type VARCHAR(50) NOT NULL,       -- 'zip', 'docker_image'
    file_path VARCHAR(1024),                -- For ZIP files
    image_url VARCHAR(1024),                -- For Docker images
    file_size_bytes BIGINT,
    checksum_sha256 VARCHAR(64),
    download_count INTEGER DEFAULT 0,
    expires_at DATETIME,                    -- Auto-cleanup for SaaS
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pipeline_run_id) REFERENCES pipeline_runs(id) ON DELETE CASCADE
);
```

### Modified Tables

#### Update `pipeline_runs` Table

```sql
ALTER TABLE pipeline_runs ADD COLUMN git_repository_id INTEGER NULL;
ALTER TABLE pipeline_runs ADD COLUMN output_type VARCHAR(50) DEFAULT 'docker_image';
ALTER TABLE pipeline_runs ADD COLUMN registry_id INTEGER NULL;

-- Add foreign keys
ALTER TABLE pipeline_runs ADD CONSTRAINT fk_git_repo 
    FOREIGN KEY (git_repository_id) REFERENCES git_repositories(id);
ALTER TABLE pipeline_runs ADD CONSTRAINT fk_registry 
    FOREIGN KEY (registry_id) REFERENCES container_registries(id);
```

---

## 🔐 Credential Management System

### Security Architecture

```mermaid
graph LR
    subgraph "Application Layer"
        APP[Application]
    end
    
    subgraph "Credential Service"
        CS[Credential Service]
        ENC[Encryption Module]
    end
    
    subgraph "Key Management"
        MEK[Master Encryption Key]
        DEK[Data Encryption Keys]
    end
    
    subgraph "Storage"
        DB[(Database)]
        ENV[Environment]
    end
    
    APP --> CS
    CS --> ENC
    ENC --> DEK
    DEK --> MEK
    MEK --> ENV
    CS --> DB
```

### Encryption Strategy

#### Key Hierarchy
1. **Master Key**: Stored in environment variable or secret manager
2. **Data Encryption Keys (DEK)**: Generated per credential, encrypted with Master Key
3. **Credential Data**: Encrypted with DEK using AES-256-GCM

#### Implementation Details

```python
# Credential types and their required fields
CREDENTIAL_SCHEMAS = {
    'git_ssh': {
        'required': ['private_key'],
        'optional': ['passphrase', 'known_hosts']
    },
    'git_https': {
        'required': ['username', 'password_or_token'],
        'optional': []
    },
    'registry_docker_hub': {
        'required': ['username', 'access_token'],
        'optional': []
    },
    'registry_aws_ecr': {
        'required': ['aws_access_key_id', 'aws_secret_access_key'],
        'optional': ['aws_session_token', 'region']
    },
    'registry_quay_io': {
        'required': ['username', 'password'],
        'optional': []
    }
}
```

---

## 📁 New File Structure

```
app/
├── api/
│   ├── credentials.py          # NEW: Credential management API
│   ├── git_repositories.py     # NEW: Git repository API
│   └── build_outputs.py        # NEW: Build output API
├── models/
│   └── models.py               # MODIFIED: Add new models
├── schemas/
│   ├── credentials.py          # NEW: Credential schemas
│   ├── git_repository.py       # NEW: Git repository schemas
│   └── build_output.py         # NEW: Build output schemas
├── services/
│   ├── credential_service.py   # NEW: Credential management
│   ├── encryption_service.py   # NEW: Encryption utilities
│   ├── git_service.py          # NEW: Git operations
│   ├── build_output_service.py # NEW: Build packaging
│   └── pipeline_service.py     # MODIFIED: Support custom forks
├── templates/
│   ├── credentials.html        # NEW: Credential management UI
│   ├── git_repositories.html   # NEW: Repository management UI
│   └── pipeline.html           # MODIFIED: Custom fork options
└── utils/
    └── git_utils.py            # NEW: Git helper functions
```

---

## 🔧 Implementation Phases

### Phase 1: Credential Management Foundation

#### 1.1 Create Encryption Service

**File**: `app/services/encryption_service.py`

```python
"""
Encryption service for secure credential storage.
Uses AES-256-GCM for data encryption with key derivation.
"""

import os
import base64
import secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

class EncryptionService:
    """Handles encryption and decryption of sensitive data."""
    
    def __init__(self, master_key: str = None):
        """Initialize with master key from environment."""
        self.master_key = master_key or os.environ.get('CREDENTIAL_MASTER_KEY')
        if not self.master_key:
            raise ConfigurationError("CREDENTIAL_MASTER_KEY not configured")
    
    def encrypt(self, plaintext: str) -> dict:
        """Encrypt data and return encrypted payload with metadata."""
        # Implementation details...
        pass
    
    def decrypt(self, encrypted_data: dict) -> str:
        """Decrypt data from encrypted payload."""
        # Implementation details...
        pass
```

#### 1.2 Create Credential Models

**File**: `app/models/models.py` (additions)

```python
class Credential(Base):
    __tablename__ = "credentials"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    credential_type = Column(String(50), nullable=False)
    encrypted_data = Column(Text, nullable=False)
    encryption_key_id = Column(String(255))
    metadata = Column(JSON, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    
    # Relationships
    git_repositories = relationship("GitRepository", back_populates="credential")
```

#### 1.3 Create Credential Schemas

**File**: `app/schemas/credentials.py`

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class CredentialType(str, Enum):
    GIT_SSH = "git_ssh"
    GIT_HTTPS = "git_https"
    REGISTRY_DOCKER_HUB = "registry_docker_hub"
    REGISTRY_AWS_ECR = "registry_aws_ecr"
    REGISTRY_QUAY_IO = "registry_quay_io"

class CredentialCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    credential_type: CredentialType
    credential_data: Dict[str, Any]  # Will be encrypted
    expires_at: Optional[datetime] = None
    
    @validator('credential_data')
    def validate_credential_data(cls, v, values):
        """Validate that required fields are present for credential type."""
        # Validation logic based on credential type
        pass

class CredentialResponse(BaseModel):
    id: int
    name: str
    credential_type: CredentialType
    is_active: bool
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    # Note: credential_data is NEVER exposed in responses
    
    class Config:
        from_attributes = True
```

#### 1.4 Create Credential Service

**File**: `app/services/credential_service.py`

```python
"""
Service for managing credentials securely.
"""

from sqlalchemy.orm import Session
from app.models.models import Credential
from app.services.encryption_service import EncryptionService
from app.schemas.credentials import CredentialCreate, CredentialType
from app.exceptions import ValidationError, NotFoundError

class CredentialService:
    """Manages credential lifecycle with encryption."""
    
    def __init__(self, db: Session):
        self.db = db
        self.encryption = EncryptionService()
    
    def create_credential(self, credential: CredentialCreate) -> Credential:
        """Create a new encrypted credential."""
        # Validate credential data
        self._validate_credential_data(credential.credential_type, credential.credential_data)
        
        # Encrypt sensitive data
        encrypted = self.encryption.encrypt(json.dumps(credential.credential_data))
        
        db_credential = Credential(
            name=credential.name,
            credential_type=credential.credential_type.value,
            encrypted_data=json.dumps(encrypted),
            encryption_key_id=encrypted.get('key_id'),
            expires_at=credential.expires_at
        )
        
        self.db.add(db_credential)
        self.db.commit()
        self.db.refresh(db_credential)
        return db_credential
    
    def get_decrypted_credential(self, credential_id: int) -> dict:
        """Retrieve and decrypt credential data."""
        credential = self.db.query(Credential).filter(
            Credential.id == credential_id,
            Credential.is_active == True
        ).first()
        
        if not credential:
            raise NotFoundError(f"Credential {credential_id} not found")
        
        # Check expiration
        if credential.expires_at and credential.expires_at < datetime.utcnow():
            raise ValidationError("Credential has expired")
        
        # Decrypt and return
        encrypted_data = json.loads(credential.encrypted_data)
        decrypted = self.encryption.decrypt(encrypted_data)
        
        # Update last used timestamp
        credential.last_used_at = datetime.utcnow()
        self.db.commit()
        
        return json.loads(decrypted)
```

#### 1.5 Create Credential API

**File**: `app/api/credentials.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.schemas.credentials import (
    CredentialCreate, CredentialResponse, CredentialUpdate
)
from app.services.credential_service import CredentialService
from typing import List

router = APIRouter(prefix="/api/v1/credentials", tags=["credentials"])

@router.post("/", response_model=CredentialResponse)
def create_credential(
    credential: CredentialCreate,
    db: Session = Depends(get_db)
):
    """Create a new credential (data will be encrypted)."""
    service = CredentialService(db)
    return service.create_credential(credential)

@router.get("/", response_model=List[CredentialResponse])
def list_credentials(db: Session = Depends(get_db)):
    """List all credentials (without sensitive data)."""
    service = CredentialService(db)
    return service.list_credentials()

@router.delete("/{credential_id}")
def delete_credential(credential_id: int, db: Session = Depends(get_db)):
    """Delete a credential."""
    service = CredentialService(db)
    if not service.delete_credential(credential_id):
        raise HTTPException(status_code=404, detail="Credential not found")
    return {"message": "Credential deleted successfully"}

@router.post("/{credential_id}/verify")
def verify_credential(credential_id: int, db: Session = Depends(get_db)):
    """Verify that a credential is valid and working."""
    service = CredentialService(db)
    result = service.verify_credential(credential_id)
    return {"valid": result.valid, "message": result.message}
```

---

### Phase 2: Git Repository Management

#### 2.1 Create Git Repository Models

**File**: `app/models/models.py` (additions)

```python
class GitRepository(Base):
    __tablename__ = "git_repositories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    repository_url = Column(String(1024), nullable=False)
    repository_type = Column(String(20), nullable=False)  # 'https' or 'ssh'
    default_branch = Column(String(255), default='main')
    credential_id = Column(Integer, ForeignKey('credentials.id'), nullable=True)
    is_verified = Column(Boolean, default=False)
    verification_status = Column(String(50), default='pending')
    verification_message = Column(Text, nullable=True)
    is_experimental = Column(Boolean, default=True)
    metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    credential = relationship("Credential", back_populates="git_repositories")
    pipeline_runs = relationship("PipelineRun", back_populates="git_repository")
```

#### 2.2 Create Git Service

**File**: `app/services/git_service.py`

```python
"""
Service for Git operations including clone, fetch, and verification.
Supports both HTTPS and SSH protocols with credential handling.
"""

import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.models.models import GitRepository
from app.services.credential_service import CredentialService
from app.exceptions import PipelineError, ValidationError

class GitService:
    """Handles Git operations for custom fork cloning."""
    
    OFFICIAL_REPO_URL = "https://github.com/open-webui/open-webui.git"
    
    def __init__(self, db: Session):
        self.db = db
        self.credential_service = CredentialService(db)
    
    def validate_repository_url(self, url: str) -> Tuple[bool, str, str]:
        """
        Validate and parse a repository URL.
        Returns: (is_valid, repo_type, normalized_url)
        """
        url = url.strip()
        
        # SSH URL pattern: git@host:user/repo.git
        if url.startswith('git@') or url.startswith('ssh://'):
            return True, 'ssh', url
        
        # HTTPS URL pattern
        if url.startswith('https://') or url.startswith('http://'):
            return True, 'https', url
        
        return False, None, "Invalid repository URL format"
    
    def clone_repository(
        self,
        repository: GitRepository,
        target_dir: str,
        branch: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Clone a repository to the target directory.
        Returns: (success, message)
        """
        branch = branch or repository.default_branch
        
        try:
            # Prepare environment for credentials
            env = os.environ.copy()
            
            if repository.credential_id:
                cred_data = self.credential_service.get_decrypted_credential(
                    repository.credential_id
                )
                env = self._setup_credential_environment(
                    repository.repository_type,
                    cred_data,
                    env
                )
            
            # Clone command
            cmd = [
                'git', 'clone',
                '--depth', '1',  # Shallow clone for efficiency
                '--branch', branch,
                repository.repository_url,
                target_dir
            ]
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                return False, f"Clone failed: {result.stderr}"
            
            return True, "Repository cloned successfully"
            
        except subprocess.TimeoutExpired:
            return False, "Clone operation timed out"
        except Exception as e:
            return False, f"Clone error: {str(e)}"
        finally:
            # Clean up SSH key files if created
            self._cleanup_temp_credentials()
    
    def _setup_credential_environment(
        self,
        repo_type: str,
        cred_data: dict,
        env: dict
    ) -> dict:
        """Set up environment variables for Git authentication."""
        
        if repo_type == 'ssh':
            # Create temporary SSH key file
            ssh_key_path = self._write_temp_ssh_key(cred_data['private_key'])
            
            # Configure SSH command
            ssh_cmd = f'ssh -i {ssh_key_path} -o StrictHostKeyChecking=no'
            if 'known_hosts' in cred_data:
                known_hosts_path = self._write_temp_known_hosts(cred_data['known_hosts'])
                ssh_cmd += f' -o UserKnownHostsFile={known_hosts_path}'
            
            env['GIT_SSH_COMMAND'] = ssh_cmd
            
        elif repo_type == 'https':
            # Use credential helper or embed in URL
            username = cred_data['username']
            token = cred_data['password_or_token']
            
            # Configure credential helper
            env['GIT_ASKPASS'] = self._create_askpass_script(username, token)
        
        return env
    
    def verify_repository(self, repository_id: int) -> Tuple[bool, str]:
        """
        Verify that a repository can be accessed with current credentials.
        Uses 'git ls-remote' to check without full clone.
        """
        repository = self.db.query(GitRepository).filter(
            GitRepository.id == repository_id
        ).first()
        
        if not repository:
            return False, "Repository not found"
        
        try:
            env = os.environ.copy()
            
            if repository.credential_id:
                cred_data = self.credential_service.get_decrypted_credential(
                    repository.credential_id
                )
                env = self._setup_credential_environment(
                    repository.repository_type,
                    cred_data,
                    env
                )
            
            cmd = ['git', 'ls-remote', '--heads', repository.repository_url]
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                repository.is_verified = True
                repository.verification_status = 'success'
                repository.verification_message = 'Repository accessible'
            else:
                repository.is_verified = False
                repository.verification_status = 'failed'
                repository.verification_message = result.stderr
            
            self.db.commit()
            return repository.is_verified, repository.verification_message
            
        except Exception as e:
            repository.verification_status = 'failed'
            repository.verification_message = str(e)
            self.db.commit()
            return False, str(e)
```

#### 2.3 Create Git Repository API

**File**: `app/api/git_repositories.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.schemas.git_repository import (
    GitRepositoryCreate, GitRepositoryResponse, GitRepositoryUpdate
)
from app.services.git_service import GitService
from typing import List

router = APIRouter(prefix="/api/v1/git-repositories", tags=["git-repositories"])

@router.post("/", response_model=GitRepositoryResponse)
def create_repository(
    repository: GitRepositoryCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new Git repository configuration.
    
    ⚠️ EXPERIMENTAL: Custom fork support is experimental and may not work
    with all forks or modifications.
    """
    service = GitService(db)
    
    # Validate URL
    is_valid, repo_type, message = service.validate_repository_url(repository.repository_url)
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)
    
    return service.create_repository(repository, repo_type)

@router.get("/", response_model=List[GitRepositoryResponse])
def list_repositories(db: Session = Depends(get_db)):
    """List all configured Git repositories."""
    service = GitService(db)
    return service.list_repositories()

@router.post("/{repository_id}/verify")
def verify_repository(repository_id: int, db: Session = Depends(get_db)):
    """
    Verify that the repository is accessible with configured credentials.
    """
    service = GitService(db)
    success, message = service.verify_repository(repository_id)
    return {
        "verified": success,
        "message": message
    }

@router.delete("/{repository_id}")
def delete_repository(repository_id: int, db: Session = Depends(get_db)):
    """Delete a Git repository configuration."""
    service = GitService(db)
    if not service.delete_repository(repository_id):
        raise HTTPException(status_code=404, detail="Repository not found")
    return {"message": "Repository deleted successfully"}
```

---

### Phase 3: Enhanced Pipeline with Custom Fork Support

#### 3.1 Update Pipeline Service

**File**: `app/services/pipeline_service.py` (modifications)

```python
class PipelineService:
    """Enhanced pipeline service with custom fork support."""
    
    def __init__(self, db: Session):
        self.db = db
        self.git_service = GitService(db)
        self.credential_service = CredentialService(db)
    
    def get_pipeline_steps(self):
        """Get all available pipeline steps including new options."""
        return [
            {
                "name": "clone",
                "description": "Clone/fetch the source repository",
                "supports_custom_fork": True
            },
            {
                "name": "branding",
                "description": "Apply branding customizations (text replacements)",
                "supports_custom_fork": True
            },
            {
                "name": "build",
                "description": "Build the Svelte frontend and Docker image",
                "supports_custom_fork": True,
                "experimental_warning": "May fail with heavily modified forks"
            },
            {
                "name": "package",
                "description": "Package output as ZIP or Docker image",
                "supports_custom_fork": True
            },
            {
                "name": "publish",
                "description": "Publish Docker image to registry",
                "supports_custom_fork": True
            },
            {
                "name": "clean",
                "description": "Clean up temporary files",
                "supports_custom_fork": True
            }
        ]
    
    def execute_pipeline(
        self,
        steps: list,
        template_id: int,
        output_type: str = 'docker_image',  # 'docker_image' or 'zip'
        git_repository_id: int = None,      # None = official repo
        registry_id: int = None
    ):
        """
        Execute the pipeline with optional custom fork support.
        """
        # Create pipeline run record
        db_pipeline_run = PipelineRun(
            status="running",
            selected_steps=json.dumps(steps),
            template_id=template_id,
            git_repository_id=git_repository_id,
            output_type=output_type,
            registry_id=registry_id
        )
        self.db.add(db_pipeline_run)
        self.db.commit()
        
        log_output = ""
        
        # Add experimental warning for custom forks
        if git_repository_id:
            log_output += "\n⚠️ EXPERIMENTAL: Using custom fork. Compatibility not guaranteed.\n"
        
        try:
            for step in steps:
                if step == "clone":
                    log_output += self._execute_clone_step(git_repository_id)
                elif step == "branding":
                    log_output += self._execute_branding_step(template_id)
                elif step == "build":
                    log_output += self._execute_build_step()
                elif step == "package":
                    log_output += self._execute_package_step(
                        db_pipeline_run.id,
                        output_type
                    )
                elif step == "publish":
                    if output_type == 'docker_image' and registry_id:
                        log_output += self._execute_publish_step(registry_id)
                    else:
                        log_output += "Skipping publish: Not applicable for ZIP output\n"
                elif step == "clean":
                    log_output += self._execute_clean_step()
            
            db_pipeline_run.status = "completed"
            
        except Exception as e:
            db_pipeline_run.status = "failed"
            log_output += f"\n❌ Error: {str(e)}"
        
        db_pipeline_run.log_output = log_output
        db_pipeline_run.end_time = datetime.utcnow()
        self.db.commit()
        
        return db_pipeline_run
    
    def _execute_clone_step(self, git_repository_id: int = None) -> str:
        """Execute clone step with custom fork support."""
        log_output = "\n=== Clone Step ===\n"
        
        if git_repository_id:
            # Clone custom fork
            repository = self.db.query(GitRepository).filter(
                GitRepository.id == git_repository_id
            ).first()
            
            if not repository:
                raise PipelineError("Git repository not found", step="clone")
            
            log_output += f"Cloning custom fork: {repository.name}\n"
            log_output += f"URL: {repository.repository_url}\n"
            
            success, message = self.git_service.clone_repository(
                repository,
                "open-webui"
            )
            
            if not success:
                raise PipelineError(f"Clone failed: {message}", step="clone")
            
            log_output += f"✅ {message}\n"
            
        else:
            # Use official submodule
            log_output += "Using official Open WebUI repository\n"
            log_output += self._clone_official_repo()
        
        return log_output
```

#### 3.2 Create Build Output Service

**File**: `app/services/build_output_service.py`

```python
"""
Service for managing build outputs (ZIP archives and Docker images).
"""

import os
import shutil
import hashlib
import zipfile
from pathlib import Path
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.models import BuildOutput, PipelineRun
from app.config import get_settings

class BuildOutputService:
    """Manages build output packaging and storage."""
    
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
    
    def create_zip_archive(
        self,
        pipeline_run_id: int,
        source_dir: str = "open-webui",
        include_build: bool = True
    ) -> BuildOutput:
        """
        Create a compressed ZIP archive of the customized source.
        
        Args:
            pipeline_run_id: Associated pipeline run
            source_dir: Directory to archive
            include_build: Include built artifacts (node_modules excluded)
        """
        output_dir = Path(self.settings.file_storage.base_dir) / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"open-webui-custom_{pipeline_run_id}_{timestamp}.zip"
        zip_path = output_dir / zip_filename
        
        # Exclusion patterns
        exclude_patterns = [
            'node_modules',
            '.git',
            '__pycache__',
            '*.pyc',
            '.env',
            '.env.local',
            'venv',
            '.venv'
        ]
        
        # Create ZIP with maximum compression
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            source_path = Path(source_dir)
            
            for file_path in source_path.rglob('*'):
                # Check exclusions
                if any(pattern in str(file_path) for pattern in exclude_patterns):
                    continue
                
                if file_path.is_file():
                    arcname = file_path.relative_to(source_path)
                    zf.write(file_path, arcname)
        
        # Calculate checksum
        sha256_hash = hashlib.sha256()
        with open(zip_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        # Get file size
        file_size = os.path.getsize(zip_path)
        
        # Create database record
        build_output = BuildOutput(
            pipeline_run_id=pipeline_run_id,
            output_type='zip',
            file_path=str(zip_path),
            file_size_bytes=file_size,
            checksum_sha256=sha256_hash.hexdigest(),
            expires_at=datetime.utcnow() + timedelta(days=7)  # 7-day retention
        )
        
        self.db.add(build_output)
        self.db.commit()
        self.db.refresh(build_output)
        
        return build_output
    
    def get_download_url(self, output_id: int) -> str:
        """Generate download URL for a build output."""
        output = self.db.query(BuildOutput).filter(
            BuildOutput.id == output_id
        ).first()
        
        if not output:
            return None
        
        # Increment download count
        output.download_count += 1
        self.db.commit()
        
        return f"/api/v1/build-outputs/{output_id}/download"
    
    def cleanup_expired_outputs(self):
        """Remove expired build outputs."""
        expired = self.db.query(BuildOutput).filter(
            BuildOutput.expires_at < datetime.utcnow()
        ).all()
        
        for output in expired:
            # Delete file
            if output.file_path and os.path.exists(output.file_path):
                os.remove(output.file_path)
            
            # Delete record
            self.db.delete(output)
        
        self.db.commit()
        return len(expired)
```

---

### Phase 4: User Interface Updates

#### 4.1 Credential Management UI

**File**: `app/templates/credentials.html`

```html
{% extends "base.html" %}

{% block content %}
<div class="container mx-auto px-4 py-8">
    <div class="flex justify-between items-center mb-6">
        <h1 class="text-2xl font-bold">Credential Management</h1>
        <button 
            onclick="openCreateModal()"
            class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg"
        >
            Add Credential
        </button>
    </div>
    
    <!-- Security Notice -->
    <div class="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-6">
        <div class="flex">
            <div class="flex-shrink-0">
                <svg class="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                </svg>
            </div>
            <div class="ml-3">
                <p class="text-sm text-yellow-700">
                    <strong>Security Notice:</strong> All credentials are encrypted using AES-256-GCM. 
                    Credential values are never displayed after creation.
                </p>
            </div>
        </div>
    </div>
    
    <!-- Credentials List -->
    <div id="credentials-list" hx-get="/api/v1/credentials/" hx-trigger="load">
        <!-- Populated via HTMX -->
    </div>
</div>

<!-- Create Credential Modal -->
<div id="create-modal" class="hidden fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full">
    <div class="relative top-20 mx-auto p-5 border w-full max-w-xl shadow-lg rounded-md bg-white">
        <h3 class="text-lg font-bold mb-4">Add New Credential</h3>
        
        <form hx-post="/api/v1/credentials/" hx-swap="none" onsubmit="closeModal()">
            <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700">Name</label>
                <input type="text" name="name" required
                    class="mt-1 block w-full rounded-md border-gray-300 shadow-sm">
            </div>
            
            <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700">Credential Type</label>
                <select name="credential_type" id="credential-type" onchange="updateCredentialFields()"
                    class="mt-1 block w-full rounded-md border-gray-300 shadow-sm">
                    <option value="git_ssh">Git SSH Key</option>
                    <option value="git_https">Git HTTPS Token</option>
                    <option value="registry_docker_hub">Docker Hub</option>
                    <option value="registry_aws_ecr">AWS ECR</option>
                    <option value="registry_quay_io">Quay.io</option>
                </select>
            </div>
            
            <!-- Dynamic fields based on type -->
            <div id="credential-fields">
                <!-- Populated by JavaScript -->
            </div>
            
            <div class="flex justify-end space-x-2 mt-6">
                <button type="button" onclick="closeModal()"
                    class="px-4 py-2 bg-gray-200 rounded-lg">Cancel</button>
                <button type="submit"
                    class="px-4 py-2 bg-blue-600 text-white rounded-lg">Create</button>
            </div>
        </form>
    </div>
</div>

<script>
const credentialFieldTemplates = {
    git_ssh: `
        <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700">SSH Private Key</label>
            <textarea name="credential_data[private_key]" rows="6" required
                class="mt-1 block w-full rounded-md border-gray-300 shadow-sm font-mono text-sm"
                placeholder="-----BEGIN OPENSSH PRIVATE KEY-----"></textarea>
        </div>
        <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700">Passphrase (optional)</label>
            <input type="password" name="credential_data[passphrase]"
                class="mt-1 block w-full rounded-md border-gray-300 shadow-sm">
        </div>
    `,
    git_https: `
        <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700">Username</label>
            <input type="text" name="credential_data[username]" required
                class="mt-1 block w-full rounded-md border-gray-300 shadow-sm">
        </div>
        <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700">Personal Access Token</label>
            <input type="password" name="credential_data[password_or_token]" required
                class="mt-1 block w-full rounded-md border-gray-300 shadow-sm">
        </div>
    `,
    // ... other credential type templates
};

function updateCredentialFields() {
    const type = document.getElementById('credential-type').value;
    document.getElementById('credential-fields').innerHTML = credentialFieldTemplates[type] || '';
}

// Initialize on load
updateCredentialFields();
</script>
{% endblock %}
```

#### 4.2 Git Repository Management UI

**File**: `app/templates/git_repositories.html`

```html
{% extends "base.html" %}

{% block content %}
<div class="container mx-auto px-4 py-8">
    <div class="flex justify-between items-center mb-6">
        <div>
            <h1 class="text-2xl font-bold">Git Repositories</h1>
            <p class="text-gray-600">Configure custom forks for branding</p>
        </div>
        <button 
            onclick="openCreateRepoModal()"
            class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg"
        >
            Add Repository
        </button>
    </div>
    
    <!-- Experimental Warning -->
    <div class="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
        <div class="flex">
            <div class="flex-shrink-0">
                <span class="text-2xl">⚠️</span>
            </div>
            <div class="ml-3">
                <h3 class="text-sm font-medium text-amber-800">Experimental Feature</h3>
                <p class="mt-1 text-sm text-amber-700">
                    Custom fork support is experimental. The build process may fail if your fork 
                    has significant structural changes from the official Open WebUI repository.
                    We recommend testing with a simple fork first.
                </p>
            </div>
        </div>
    </div>
    
    <!-- Official Repository Card -->
    <div class="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
        <div class="flex items-center justify-between">
            <div class="flex items-center">
                <span class="text-2xl mr-3">✅</span>
                <div>
                    <h3 class="font-medium text-green-800">Official Open WebUI Repository</h3>
                    <p class="text-sm text-green-600">https://github.com/open-webui/open-webui</p>
                </div>
            </div>
            <span class="bg-green-200 text-green-800 px-3 py-1 rounded-full text-sm">
                Recommended
            </span>
        </div>
    </div>
    
    <h2 class="text-lg font-semibold mb-4">Custom Forks</h2>
    
    <!-- Repository List -->
    <div id="repository-list" hx-get="/api/v1/git-repositories/" hx-trigger="load">
        <!-- Populated via HTMX -->
    </div>
</div>

<!-- Create Repository Modal -->
<div id="create-repo-modal" class="hidden fixed inset-0 bg-gray-600 bg-opacity-50">
    <div class="relative top-20 mx-auto p-5 border w-full max-w-xl shadow-lg rounded-md bg-white">
        <h3 class="text-lg font-bold mb-4">Add Custom Fork</h3>
        
        <form hx-post="/api/v1/git-repositories/" hx-swap="none">
            <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700">Repository Name</label>
                <input type="text" name="name" required
                    class="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
                    placeholder="My Custom Fork">
            </div>
            
            <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700">Repository URL</label>
                <input type="text" name="repository_url" required
                    class="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
                    placeholder="https://github.com/username/open-webui-fork.git">
                <p class="mt-1 text-sm text-gray-500">
                    HTTPS or SSH URL (e.g., git@github.com:user/repo.git)
                </p>
            </div>
            
            <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700">Default Branch</label>
                <input type="text" name="default_branch" value="main"
                    class="mt-1 block w-full rounded-md border-gray-300 shadow-sm">
            </div>
            
            <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700">
                    Credentials (for private repos)
                </label>
                <select name="credential_id"
                    class="mt-1 block w-full rounded-md border-gray-300 shadow-sm">
                    <option value="">None (Public Repository)</option>
                    {% for cred in credentials %}
                    <option value="{{ cred.id }}">{{ cred.name }} ({{ cred.credential_type }})</option>
                    {% endfor %}
                </select>
            </div>
            
            <div class="flex justify-end space-x-2 mt-6">
                <button type="button" onclick="closeRepoModal()"
                    class="px-4 py-2 bg-gray-200 rounded-lg">Cancel</button>
                <button type="submit"
                    class="px-4 py-2 bg-blue-600 text-white rounded-lg">Add Repository</button>
            </div>
        </form>
    </div>
</div>
{% endblock %}
```

#### 4.3 Updated Pipeline UI

**File**: `app/templates/pipeline.html` (modifications)

```html
{% extends "base.html" %}

{% block content %}
<div class="container mx-auto px-4 py-8">
    <h1 class="text-2xl font-bold mb-6">Pipeline Execution</h1>
    
    <form hx-post="/api/v1/pipeline/execute" hx-target="#pipeline-result">
        <!-- Source Selection -->
        <div class="bg-white rounded-lg shadow p-6 mb-6">
            <h2 class="text-lg font-semibold mb-4">Source Repository</h2>
            
            <div class="space-y-4">
                <label class="flex items-center">
                    <input type="radio" name="source_type" value="official" checked
                        class="h-4 w-4 text-blue-600" onchange="toggleSourceOptions()">
                    <span class="ml-2">Official Open WebUI Repository</span>
                    <span class="ml-2 bg-green-100 text-green-800 px-2 py-1 rounded text-sm">
                        Recommended
                    </span>
                </label>
                
                <label class="flex items-center">
                    <input type="radio" name="source_type" value="custom"
                        class="h-4 w-4 text-blue-600" onchange="toggleSourceOptions()">
                    <span class="ml-2">Custom Fork</span>
                    <span class="ml-2 bg-amber-100 text-amber-800 px-2 py-1 rounded text-sm">
                        Experimental
                    </span>
                </label>
            </div>
            
            <!-- Custom Fork Selection (hidden by default) -->
            <div id="custom-fork-options" class="hidden mt-4 pl-6 border-l-2 border-amber-300">
                <div class="bg-amber-50 border border-amber-200 rounded p-3 mb-4">
                    <p class="text-sm text-amber-800">
                        ⚠️ Custom forks may have compatibility issues. 
                        Build success is not guaranteed.
                    </p>
                </div>
                
                <label class="block text-sm font-medium text-gray-700">Select Repository</label>
                <select name="git_repository_id"
                    class="mt-1 block w-full rounded-md border-gray-300 shadow-sm">
                    {% for repo in git_repositories %}
                    <option value="{{ repo.id }}">
                        {{ repo.name }} 
                        {% if repo.is_verified %}✓{% else %}(unverified){% endif %}
                    </option>
                    {% endfor %}
                </select>
                <p class="mt-1 text-sm text-gray-500">
                    <a href="/git-repositories" class="text-blue-600 hover:underline">
                        Manage repositories →
                    </a>
                </p>
            </div>
        </div>
        
        <!-- Branding Template Selection -->
        <div class="bg-white rounded-lg shadow p-6 mb-6">
            <h2 class="text-lg font-semibold mb-4">Branding Template</h2>
            <select name="template_id" required
                class="block w-full rounded-md border-gray-300 shadow-sm">
                {% for template in templates %}
                <option value="{{ template.id }}">{{ template.name }}</option>
                {% endfor %}
            </select>
        </div>
        
        <!-- Output Type Selection -->
        <div class="bg-white rounded-lg shadow p-6 mb-6">
            <h2 class="text-lg font-semibold mb-4">Output Type</h2>
            
            <div class="space-y-4">
                <label class="flex items-start">
                    <input type="radio" name="output_type" value="docker_image" checked
                        class="h-4 w-4 text-blue-600 mt-1" onchange="toggleOutputOptions()">
                    <div class="ml-2">
                        <span class="font-medium">Docker Image</span>
                        <p class="text-sm text-gray-500">
                            Build and optionally push to a container registry
                        </p>
                    </div>
                </label>
                
                <label class="flex items-start">
                    <input type="radio" name="output_type" value="zip"
                        class="h-4 w-4 text-blue-600 mt-1" onchange="toggleOutputOptions()">
                    <div class="ml-2">
                        <span class="font-medium">ZIP Archive</span>
                        <p class="text-sm text-gray-500">
                            Download customized source code as compressed archive
                        </p>
                    </div>
                </label>
            </div>
            
            <!-- Registry Selection (for Docker output) -->
            <div id="registry-options" class="mt-4">
                <label class="block text-sm font-medium text-gray-700">Target Registry</label>
                <select name="registry_id"
                    class="mt-1 block w-full rounded-md border-gray-300 shadow-sm">
                    <option value="">Local only (don't push)</option>
                    {% for registry in registries %}
                    <option value="{{ registry.id }}">{{ registry.name }}</option>
                    {% endfor %}
                </select>
            </div>
        </div>
        
        <!-- Pipeline Steps -->
        <div class="bg-white rounded-lg shadow p-6 mb-6">
            <h2 class="text-lg font-semibold mb-4">Pipeline Steps</h2>
            
            <div class="space-y-2">
                {% for step in pipeline_steps %}
                <label class="flex items-center">
                    <input type="checkbox" name="steps" value="{{ step.name }}"
                        {% if step.name in default_steps %}checked{% endif %}
                        class="h-4 w-4 text-blue-600">
                    <span class="ml-2">{{ step.description }}</span>
                    {% if step.experimental_warning %}
                    <span class="ml-2 text-xs text-amber-600">
                        ({{ step.experimental_warning }})
                    </span>
                    {% endif %}
                </label>
                {% endfor %}
            </div>
        </div>
        
        <!-- Execute Button -->
        <div class="flex justify-end">
            <button type="submit"
                class="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium">
                🚀 Run Pipeline
            </button>
        </div>
    </form>
    
    <!-- Pipeline Result -->
    <div id="pipeline-result" class="mt-6">
        <!-- Results populated via HTMX -->
    </div>
</div>

<script>
function toggleSourceOptions() {
    const isCustom = document.querySelector('input[name="source_type"][value="custom"]').checked;
    document.getElementById('custom-fork-options').classList.toggle('hidden', !isCustom);
}

function toggleOutputOptions() {
    const isDocker = document.querySelector('input[name="output_type"][value="docker_image"]').checked;
    document.getElementById('registry-options').classList.toggle('hidden', !isDocker);
}
</script>
{% endblock %}
```

---

### Phase 5: Database Migrations

#### 5.1 Create Alembic Migration

**File**: `alembic/versions/xxxx_add_credential_and_git_repo_tables.py`

```python
"""Add credential management and git repository tables

Revision ID: xxxx
Revises: f036c06e4c08
Create Date: 2026-01-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

revision = 'xxxx_credentials_git_repos'
down_revision = 'f036c06e4c08'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create credentials table
    op.create_table(
        'credentials',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('credential_type', sa.String(50), nullable=False),
        sa.Column('encrypted_data', sa.Text(), nullable=False),
        sa.Column('encryption_key_id', sa.String(255), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_credentials_name', 'credentials', ['name'], unique=True)
    op.create_index('ix_credentials_type', 'credentials', ['credential_type'])
    
    # Create git_repositories table
    op.create_table(
        'git_repositories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('repository_url', sa.String(1024), nullable=False),
        sa.Column('repository_type', sa.String(20), nullable=False),
        sa.Column('default_branch', sa.String(255), default='main'),
        sa.Column('credential_id', sa.Integer(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), default=False),
        sa.Column('verification_status', sa.String(50), default='pending'),
        sa.Column('verification_message', sa.Text(), nullable=True),
        sa.Column('is_experimental', sa.Boolean(), default=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['credential_id'], ['credentials.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_git_repositories_name', 'git_repositories', ['name'], unique=True)
    
    # Create build_outputs table
    op.create_table(
        'build_outputs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pipeline_run_id', sa.Integer(), nullable=False),
        sa.Column('output_type', sa.String(50), nullable=False),
        sa.Column('file_path', sa.String(1024), nullable=True),
        sa.Column('image_url', sa.String(1024), nullable=True),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('checksum_sha256', sa.String(64), nullable=True),
        sa.Column('download_count', sa.Integer(), default=0),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['pipeline_run_id'], ['pipeline_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add new columns to pipeline_runs
    op.add_column('pipeline_runs', sa.Column('git_repository_id', sa.Integer(), nullable=True))
    op.add_column('pipeline_runs', sa.Column('output_type', sa.String(50), default='docker_image'))
    op.add_column('pipeline_runs', sa.Column('registry_id', sa.Integer(), nullable=True))
    
    op.create_foreign_key(
        'fk_pipeline_runs_git_repo',
        'pipeline_runs', 'git_repositories',
        ['git_repository_id'], ['id']
    )


def downgrade() -> None:
    op.drop_constraint('fk_pipeline_runs_git_repo', 'pipeline_runs', type_='foreignkey')
    op.drop_column('pipeline_runs', 'registry_id')
    op.drop_column('pipeline_runs', 'output_type')
    op.drop_column('pipeline_runs', 'git_repository_id')
    
    op.drop_table('build_outputs')
    op.drop_index('ix_git_repositories_name', 'git_repositories')
    op.drop_table('git_repositories')
    op.drop_index('ix_credentials_type', 'credentials')
    op.drop_index('ix_credentials_name', 'credentials')
    op.drop_table('credentials')
```

---

## 🔒 Security Considerations

### Credential Storage Security

1. **Encryption at Rest**: All credentials encrypted with AES-256-GCM
2. **Key Rotation**: Support for encryption key versioning
3. **Access Logging**: Track credential usage for audit
4. **Expiration**: Optional credential expiration dates
5. **Secure Deletion**: Overwrite credentials before deletion

### SSH Key Handling

1. **Temporary Files**: SSH keys written to temp files with restricted permissions (0600)
2. **Automatic Cleanup**: Keys deleted immediately after use
3. **Memory Safety**: Keys cleared from memory after operations
4. **No Logging**: Sensitive data never written to logs

### SaaS Preparation

1. **Tenant Isolation**: Prepare for multi-tenant credential storage
2. **Rate Limiting**: Add rate limits to prevent abuse
3. **Audit Trail**: Comprehensive logging of all operations
4. **Compliance**: Design with GDPR/SOC2 considerations

---

## 🧪 Testing Strategy

### Unit Tests

```python
# tests/test_credential_service.py

def test_credential_encryption():
    """Test that credentials are properly encrypted."""
    pass

def test_credential_decryption():
    """Test that credentials can be decrypted."""
    pass

def test_expired_credential_rejected():
    """Test that expired credentials raise an error."""
    pass

# tests/test_git_service.py

def test_validate_https_url():
    """Test HTTPS URL validation."""
    pass

def test_validate_ssh_url():
    """Test SSH URL validation."""
    pass

def test_clone_public_repo():
    """Test cloning a public repository."""
    pass
```

### Integration Tests

```python
# tests/test_pipeline_integration.py

def test_pipeline_with_official_repo():
    """Test full pipeline with official repository."""
    pass

def test_pipeline_with_custom_fork():
    """Test pipeline with custom fork (experimental)."""
    pass

def test_zip_output_generation():
    """Test ZIP archive generation."""
    pass
```

---

## 📅 Implementation Timeline

### Week 1-2: Foundation
- [ ] Implement encryption service
- [ ] Create credential models and schemas
- [ ] Build credential API endpoints
- [ ] Create credential management UI

### Week 3-4: Git Integration
- [ ] Implement Git service with SSH/HTTPS support
- [ ] Create git repository models and API
- [ ] Build repository management UI
- [ ] Add repository verification

### Week 5-6: Pipeline Enhancement
- [ ] Update pipeline service for custom forks
- [ ] Implement ZIP output packaging
- [ ] Enhance pipeline UI with new options
- [ ] Add build output tracking

### Week 7-8: Testing & Polish
- [ ] Comprehensive unit testing
- [ ] Integration testing
- [ ] Security audit
- [ ] Documentation
- [ ] Performance optimization

---

## 🚀 Future SaaS Considerations

### Multi-Tenancy Preparation

1. **User Model**: Add user/organization models
2. **Resource Isolation**: Ensure credentials are tenant-scoped
3. **Quotas**: Implement usage quotas per tenant
4. **Billing Integration**: Track resource usage for billing

### Scalability

1. **Queue System**: Move pipeline execution to async queue (Celery/RQ)
2. **Storage**: Move to cloud storage (S3) for build outputs
3. **Database**: Prepare for PostgreSQL migration
4. **Caching**: Add Redis for session/cache management

### Infrastructure

1. **Container Orchestration**: Kubernetes-ready deployment
2. **Secrets Management**: Integration with Vault/AWS Secrets Manager
3. **Monitoring**: Prometheus metrics, structured logging
4. **CI/CD**: Automated testing and deployment pipeline

---

## ✅ Acceptance Criteria

1. Users can create and manage encrypted credentials
2. Users can configure custom Git repositories (public and private)
3. Repository verification works for HTTPS and SSH URLs
4. Pipeline supports both official and custom repositories
5. Users can choose between ZIP and Docker image output
6. All credentials are encrypted at rest
7. Experimental features are clearly marked
8. Comprehensive error handling and user feedback
9. Full API documentation
10. Test coverage > 80%