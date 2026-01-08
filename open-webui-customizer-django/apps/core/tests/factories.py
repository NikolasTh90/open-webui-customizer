"""
Factory Boy factories for creating test instances.
"""

import factory
from django.contrib.auth import get_user_model
from apps.branding.models import BrandingTemplate, BrandingAsset
from apps.credentials.models import Credential, CredentialType
from apps.pipelines.models import PipelineRun, BuildOutput, PipelineStatus, OutputType, BuildStatus
from apps.registries.models import ContainerRegistry, RegistryType
from apps.repositories.models import GitRepository, RepositoryType, VerificationStatus

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    """Factory for creating User instances."""
    
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    
    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override to create user with password."""
        password = kwargs.pop("password", "password123")
        user = super()._create(model_class, *args, **kwargs)
        user.set_password(password)
        user.save()
        return user


class BrandingTemplateFactory(factory.django.DjangoModelFactory):
    """Factory for creating BrandingTemplate instances."""
    
    class Meta:
        model = BrandingTemplate
    
    name = factory.Faker("company")
    description = factory.Faker("text", max_nb_chars=200)
    is_active = True
    is_default = False
    primary_color = factory.Faker("hex_color")
    secondary_color = factory.Faker("hex_color")
    accent_color = factory.Faker("hex_color")
    background_color = "#ffffff"
    text_color = "#000000"
    custom_css = factory.Faker("text", max_nb_chars=500)
    css_variables = factory.Dict({
        "font-size": "16px",
        "border-radius": "4px"
    })
    metadata = factory.Dict({
        "version": "1.0",
        "created_by": "factory"
    })


class BrandingAssetFactory(factory.django.DjangoModelFactory):
    """Factory for creating BrandingAsset instances."""
    
    class Meta:
        model = BrandingAsset
    
    file_name = factory.Faker("file_name", extension="png")
    file_type = factory.Iterator(["logo", "favicon", "icon", "background"])
    file_size = factory.Faker("random_int", min=1000, max=1000000)
    description = factory.Faker("text", max_nb_chars=100)
    file_url = factory.Faker("url")
    template = factory.SubFactory(BrandingTemplateFactory)
    metadata = factory.Dict({
        "original_name": "test.png"
    })


class CredentialFactory(factory.django.DjangoModelFactory):
    """Factory for creating Credential instances."""
    
    class Meta:
        model = Credential
    
    name = factory.Faker("company")
    description = factory.Faker("text", max_nb_chars=200)
    credential_type = factory.Iterator([
        CredentialType.GIT_SSH_KEY,
        CredentialType.GIT_TOKEN,
        CredentialType.DOCKER_REGISTRY,
        CredentialType.AWS_ECR
    ])
    
    @factory.lazy_attribute
    def encrypted_data(self):
        """Generate appropriate encrypted data based on credential type."""
        if self.credential_type == CredentialType.GIT_SSH_KEY:
            return {
                "private_key": "-----BEGIN RSA PRIVATE KEY-----\n...",
                "public_key": "ssh-rsa abc123 test@example.com"
            }
        elif self.credential_type == CredentialType.GIT_HTTPS_TOKEN:
            return {
                "token": "ghp_" + "x" * 40
            }
        elif self.credential_type == CredentialType.DOCKER_HUB:
            return {
                "username": "user",
                "password": "pass123"
            }
        elif self.credential_type == CredentialType.AWS_ECR:
            return {
                "access_key_id": "AKIA" + "X" * 16,
                "secret_access_key": "x" * 40,
                "region": "us-east-1"
            }
    
    is_active = True
    metadata = factory.Dict({
        "created_by": "factory"
    })


class GitRepositoryFactory(factory.django.DjangoModelFactory):
    """Factory for creating GitRepository instances."""
    
    class Meta:
        model = GitRepository
    
    name = factory.Faker("company")
    repository_url = factory.Faker("url")
    repository_type = factory.Iterator([
        RepositoryType.GITHUB,
        RepositoryType.GITLAB,
        RepositoryType.BITBUCKET,
        RepositoryType.GENERIC
    ])
    default_branch = "main"
    is_active = True
    is_verified = True
    verification_status = factory.Iterator([
        VerificationStatus.VERIFIED,
        VerificationStatus.PENDING,
        VerificationStatus.FAILED
    ])
    is_experimental = False
    credential = factory.SubFactory(CredentialFactory)
    branch = "main"
    commit_hash = factory.Faker("sha256")
    last_commit_date = factory.Faker("date_time_this_year")
    metadata = factory.Dict({
        "language": "python",
        "stars": 42
    })


class ContainerRegistryFactory(factory.django.DjangoModelFactory):
    """Factory for creating ContainerRegistry instances."""
    
    class Meta:
        model = ContainerRegistry
    
    name = factory.Faker("company")
    registry_url = factory.Faker("url")
    registry_type = factory.Iterator([
        RegistryType.DOCKER_HUB,
        RegistryType.GITHUB_PACKAGES,
        RegistryType.GITLAB_REGISTRY,
        RegistryType.AWS_ECR,
        RegistryType.GENERIC
    ])
    is_active = True
    credential = factory.SubFactory(CredentialFactory)
    namespace = factory.Faker("word")
    region = factory.Faker("word")
    metadata = factory.Dict({
        "created_by": "factory"
    })


class PipelineRunFactory(factory.django.DjangoModelFactory):
    """Factory for creating PipelineRun instances."""
    
    class Meta:
        model = PipelineRun
    
    status = factory.Iterator([
        PipelineStatus.PENDING,
        PipelineStatus.RUNNING,
        PipelineStatus.COMPLETED,
        PipelineStatus.FAILED
    ])
    output_type = factory.Iterator([
        OutputType.DOCKER_IMAGE,
        OutputType.UI_BUNDLE,
        OutputType.COMPLETE_BUILD
    ])
    git_repository = factory.SubFactory(GitRepositoryFactory)
    registry = factory.SubFactory(ContainerRegistryFactory)
    steps_to_execute = factory.List(["clone", "build", "brand", "push"])
    worker_id = factory.Faker("uuid4")
    progress_percentage = factory.Faker("random_int", min=0, max=100)
    current_step = factory.Faker("word")
    branch = "main"
    commit_hash = factory.Faker("sha256")
    image_tag = "latest"
    branding_template_id = factory.Faker("uuid4")
    build_arguments = factory.Dict({
        "DEBUG": "false"
    })
    environment_variables = factory.Dict({
        "NODE_ENV": "production"
    })
    error_message = factory.Faker("text", max_nb_chars=500)
    logs = factory.Faker("text", max_nb_chars=1000)
    log_file = factory.Faker("file_path")
    metadata = factory.Dict({
        "triggered_by": "manual"
    })


class BuildOutputFactory(factory.django.DjangoModelFactory):
    """Factory for creating BuildOutput instances."""
    
    class Meta:
        model = BuildOutput
    
    pipeline_run = factory.SubFactory(PipelineRunFactory)
    output_type = factory.Iterator([
        OutputType.DOCKER_IMAGE,
        OutputType.UI_BUNDLE,
        OutputType.COMPLETE_BUILD
    ])
    status = factory.Iterator([
        BuildStatus.AVAILABLE,
        BuildStatus.PENDING,
        BuildStatus.EXPIRED
    ])
    file_path = factory.Faker("file_path")
    file_url = factory.Faker("url")
    image_url = factory.Faker("url")
    file_size_bytes = factory.Faker("random_int", min=1000, max=1000000)
    checksum_sha256 = factory.Faker("sha256")
    build_metadata = factory.Dict({
        "build_time": 300,
        "docker_layers": 5
    })
    expires_at = factory.Faker("date_time_this_month")
    metadata = factory.Dict({
        "format": "tar.gz"
    })