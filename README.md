# Open WebUI Customizer with Custom Fork Cloning

Enhanced version of the Open WebUI Customizer that supports building custom packages from both the official repository and user-provided Git forks.

## 🚀 New Features

### Custom Fork Cloning
- **Git Repository Management**: Add and manage custom Git repositories (SSH & HTTPS)
- **Secure Credential Handling**: Store encrypted SSH keys and authentication tokens
- **Flexible Build Steps**: Choose which build operations to execute
- **Multiple Output Types**: Generate ZIP files, Docker images, or both
- **Container Registry Integration**: Push built images to Docker Hub, AWS ECR, and other registries

### Enhanced Pipeline System
- **Step-by-Step Control**: Select specific build steps (clone, apply branding, create ZIP, build image, push to registry)
- **Real-time Monitoring**: Track pipeline execution with live logs
- **Dependency Validation**: Automatic validation of build step dependencies
- **Error Handling**: Comprehensive error reporting and recovery

### Security Features
- **Encrypted Credentials**: All sensitive data encrypted at rest using AES-256-GCM
- **Temporary SSH Keys**: Secure handling of SSH keys with automatic cleanup
- **Access Control Role-based permissions for repository and credential management
- **Audit Logging**: Complete audit trail of all operations

## 📋 Prerequisites

- Python 3.8+
- Docker (for image building)
- Git
- PostgreSQL (or other supported database)
- Redis (for caching, optional)

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/open-webui-customizer.git
cd open-webui-customizer
```

### 2. Set Up Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Copy the example environment file and configure:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost/openwebui_customizer

# Encryption key (generate a strong key)
ENCRYPTION_KEY=your-32-character-hex-string-here

# Build directories
BUILD_BASE_DIR=/tmp/open_webui_builds

# Enable debug mode (development only)
DEBUG=false
```

Generate an encryption key:

```bash
python -c "
import secrets
print('ENCRYPTION_KEY=' + secrets.token_hex(32))
"
```

### 5. Set Up Database

Run database migrations:

```bash
# Initialize Alembic if not already done
alembic init alembic

# Run migrations
alembic upgrade head
```

### 6. Start the Application

```bash
python app/main.py
```

Or using the production script:

```bash
./run.py
```

## 🔧 Configuration

### Git Repository Setup

#### SSH Repositories

1. **Generate SSH Key** (if you don't have one):
   ```bash
   ssh-keygen -t rsa -b 4096 -C "open-webui-customizer"
   ```

2. **Add SSH Key to GitHub/GitLab**:
   - Copy the public key: `cat ~/.ssh/id_rsa.pub`
   - Add it to your repository's deploy keys or your account's SSH keys

3. **Add Repository to Customizer**:
   - Navigate to "Repositories" in the UI
   - Add the SSH URL: `git@github.com:your-username/your-fork.git`
   - Select or create SSH credential

#### HTTPS Repositories

1. **Create Personal Access Token**:
   - GitHub: Settings → Developer settings → Personal access tokens
   - GitLab: User Settings → Access Tokens

2. **Add HTTPS Repository**:
   - Use URL: `https://github.com/your-username/your-fork.git`
   - Create HTTPS credential with username and token

### Container Registry Setup

#### Docker Hub

```json
{
  "name": "Docker Hub",
  "registry_type": "docker_hub",
  "username": "your-dockerhub-username",
  "password": "your-dockerhub-token-or-password",
  "base_image": "yourusername/open-webui-custom"
}
```

#### AWS ECR

```json
{
  "name": "AWS ECR",
  "registry_type": "aws_ecr",
  "aws_account_id": "123456789012",
  "aws_region": "us-west-2",
  "repository_name": "open-webui-custom"
}
```

## 🚀 Usage

### Building from Official Repository

1. Navigate to **Enhanced Pipeline**
2. Select output type (ZIP/Docker/Both)
3. Choose build steps
4. Click **Create Pipeline Run**
5. Click **Execute** when ready

### Building from Custom Fork

1. **Add Repository**:
   - Go to **Repositories** → **Add Repository**
   - Enter repository URL and credentials
   - Verify repository access

2. **Create Pipeline**:
   - In Enhanced Pipeline, select your custom repository
   - Choose output type and build steps
   - Create and execute the pipeline

3. **Monitor Progress**:
   - View real-time logs
   - Download ZIP outputs
   - Access Docker images in registry

### Build Steps Explained

| Step | Description | Required |
|------|-------------|----------|
| **Clone Git Repository** | Downloads source code from official or custom repository | ✓ |
| **Apply Branding Template** | Applies custom branding (colors, logos, names) | |
| **Apply Configuration** | Applies environment variables and settings | |
| **Create ZIP Archive** | Packages source into downloadable ZIP file | |
| **Build Docker Image** | Creates containerized Docker image | |
| **Push to Registry** | Pushes image to configured container registry | |

### Output Types

- **ZIP File**: Downloadable archive ready for deployment
- **Docker Image**: Container image for containerized deployment  
- **Both**: Generate both ZIP and Docker outputs

## 🔐 Security

### Credential Management

All credentials are encrypted using AES-256-GCM:

- **SSH Keys**: Stored encrypted, written to temporary files during use
- **Access Tokens**: Encrypted at rest, never exposed in logs
- **Automatic Cleanup**: Temporary files deleted immediately after use

### Security Best Practices

1. **Use Dedicated Credentials**: Create specific tokens for the customizer
2. **Limit Permissions**: Grant minimal required permissions
3. **Regular Rotation**: Rotate credentials periodically
4. **Audit Logs**: Monitor credential usage in audit logs

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_enhanced_pipeline_service.py

# Run with coverage
pytest --cov=app tests/
```

### Test Categories

- **Unit Tests**: Individual service and component tests
- **Integration Tests**: Service interaction tests
- **API Tests**: Endpoint functionality tests

## 📊 Monitoring

### Pipeline Statistics

Access usage statistics and metrics:

- Success/failure rates
- Popular build configurations
- Resource usage trends
- Repository usage analytics

### Logs and Monitoring

- **Pipeline Logs**: Detailed execution logs for each run
- **Error Tracking**: Comprehensive error reporting
- **Performance Metrics**: Build time and resource usage
- **Audit Trail**: Complete operation audit log

## 🔄 Maintenance

### Cleanup Operations

Regularly clean up expired build outputs:

```bash
# Via API
curl -X POST "https://your-domain.com/api/pipelines/cleanup" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Via CLI (if implemented)
python manage.py cleanup-builds
```

### Database Maintenance

Run regular database maintenance:

```bash
# Backup database
pg_dump openwebui_customizer > backup.sql

# Analyze tables
python manage.py analyze-db

# Update statistics
python manage.py update-stats
```

## 🐛 Troubleshooting

### Common Issues

#### Repository Access Denied

1. **Verify Credentials**: Check SSH key or token is correct
2. **Check Permissions**: Ensure credentials have repository access
3. **Test Repository**: Use repository verification feature

#### Build Fails During Clone

1. **Network Issues**: Check internet connectivity
2. **Repository URL**: Verify URL is correct and accessible
3. **Disk Space**: Ensure sufficient disk space for clone

#### Docker Build Fails

1. **Docker Installation**: Verify Docker is running
2. **Dockerfile**: Ensure repository contains valid Dockerfile
3. **Permissions**: Check Docker daemon permissions

#### Image Push Fails

1. **Registry Credentials**: Verify registry credentials are correct
2. **Image Name**: Ensure image name follows registry naming rules
3. **Network Access**: Check firewall and network settings

### Debug Mode

Enable debug logging:

```bash
export DEBUG=true
python app/main.py
```

### Log Locations

- **Application Logs**: `logs/open_webui_customizer.log`
- **Pipeline Logs**: Available in UI and API
- **Error Logs**: Logged to standard error and file

## 📚 API Documentation

See the complete API documentation:

- **Enhanced Pipeline API**: [docs/api/enhanced-pipeline-api.md](docs/api/enhanced-pipeline-api.md)
- **Git Repository API**: [docs/api/git-repository-api.md](docs/api/git-repository-api.md)
- **Credential API**: [docs/api/credential-api.md](docs/api/credential-api.md)

### API Examples

```bash
# Create pipeline run
curl -X POST "https://your-domain.com/api/pipelines/runs" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "steps_to_execute": ["clone_repo", "create_zip"],
    "output_type": "zip"
  }'

# Execute pipeline
curl -X POST "https://your-domain.com/api/pipelines/runs/1/execute" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get pipeline logs
curl -X GET "https://your-domain.com/api/pipelines/runs/1/logs" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🤝 Contributing

We welcome contributions! Please follow our guidelines:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/new-feature`
3. **Make changes** and add tests
4. **Run tests**: `pytest`
5. **Commit changes**: `git commit -m "Add new feature"`
6. **Push to fork**: `git push origin feature/new-feature`
7. **Create Pull Request**

### Code Style

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Add docstrings for all functions and classes
- Write comprehensive tests

## 📄 License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## 🆘 Support

### Getting Help

- **Documentation**: Check the docs folder for detailed guides
- **Issues**: Report bugs on GitHub Issues
- **Discussions**: Use GitHub Discussions for questions
- **Community**: Join our community chat for real-time help

### FAQ

**Q: Can I use private repositories?**
A: Yes! Private repositories are fully supported with SSH keys or access tokens.

**Q: Are credentials secure?**
A: All credentials are encrypted at rest using AES-256-GCM. SSH keys are handled securely with temporary files and automatic cleanup.

**Q: Can I build multiple packages from different repositories?**
A: Yes, you can configure unlimited repositories and build pipelines from any of them.

**Q: How long are build outputs stored?**
A: ZIP files are stored for 7 days, Docker images for 1 day (unless pushed to a registry).

**Q: Can I automate builds?**
A: Yes, the API provides full automation capabilities. You can integrate with CI/CD systems or schedule builds.

---

## 🗺️ Roadmap

### Upcoming Features

- [ ] **Webhook Integration**: Trigger builds from GitHub/GitLab webhooks
- [ ] **Build Queues**: Support for concurrent build processing
- [ ] **Advanced Branding**: More sophisticated customization options
- [ ] **Multi-arch Builds**: Support for ARM64 and other architectures
- [ ] **Build Caching**: Faster builds with intelligent caching
- [ ] **Build Templates**: Predefined build configurations
- [ ] **Integration Library**: Python/Node.js client libraries

### Version History

- **v1.0.0**: Initial release with custom fork cloning support
- **v0.9.x**: Legacy Open WebUI Customizer

---

**Built with ❤️ by the Open WebUI Customizer Team**
