# HTMX Integration Addendum for Django Migration

This document provides detailed guidance on integrating HTMX into the Django 6 migration, following the user's feedback that "Django works great with htmx, we can use htmx where applicable."

## Why HTMX with Django?

HTMX is a perfect companion for Django because:

1. **Server-Side Rendering**: Both favor server-side HTML generation
2. **Progressive Enhancement**: Add interactivity without JavaScript frameworks
3. **Simpler Architecture**: No need for separate frontend build process
4. **Smaller Bundle Size**: ~14KB vs hundreds of KB for React/Vue
5. **Django Template Integration**: Works seamlessly with Django templates
6. **Fast Development**: Rapid prototyping with immediate results

## Setup and Configuration

### 1. Install django-htmx

Add to `requirements/base.txt`:
```text
django-htmx>=1.17.0
```

### 2. Configure Settings

Update `config/settings/base.py`:

```python
INSTALLED_APPS = [
    # ... existing apps ...
    'django_htmx',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django_htmx.middleware.HtmxMiddleware',  # Add after CommonMiddleware
    # ... rest of middleware ...
]
```

### 3. Download HTMX

```bash
# From Django project root
mkdir -p static/js
curl -o static/js/htmx.min.js https://unpkg.com/htmx.org@1.9.10/dist/htmx.min.js

# Optional extensions
curl -o static/js/htmx-sse.js https://unpkg.com/htmx.org@1.9.10/dist/ext/sse.js
curl -o static/js/htmx-ws.js https://unpkg.com/htmx.org@1.9.10/dist/ext/ws.js
```

## Base Template with HTMX

**File: `templates/base.html`**

```html
{% load static django_htmx %}
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Open WebUI Customizer{% endblock %}</title>
    <link rel="stylesheet" href="{% static 'css/style.css' %}">
    <link rel="stylesheet" href="{% static 'css/htmx.css' %}">
    {% block extra_css %}{% endblock %}
</head>
<body hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'>
    <nav class="navbar">
        <div class="container">
            <a href="{% url 'dashboard:index' %}" class="brand">Open WebUI Customizer</a>
            <ul class="nav-links">
                <li><a href="{% url 'dashboard:index' %}" hx-boost="true">Dashboard</a></li>
                <li><a href="{% url 'branding:list' %}" hx-boost="true">Branding</a></li>
                <li><a href="{% url 'pipelines:list' %}" hx-boost="true">Pipelines</a></li>
                <li><a href="{% url 'credentials:list' %}" hx-boost="true">Credentials</a></li>
            </ul>
        </div>
    </nav>
    
    <main class="container" id="main-content">
        {% block content %}{% endblock %}
    </main>
    
    <!-- Toast notifications for HTMX responses -->
    <div id="toast-container" class="toast-container"></div>
    
    <!-- HTMX library -->
    <script src="{% static 'js/htmx.min.js' %}"></script>
    
    <!-- HTMX configuration -->
    <script>
        // Handle validation errors (422 status)
        document.body.addEventListener('htmx:beforeSwap', function(evt) {
            if (evt.detail.xhr.status === 422 || evt.detail.xhr.status === 400) {
                evt.detail.shouldSwap = true;
                evt.detail.isError = false;
            }
        });
        
        // Loading indicators
        document.body.addEventListener('htmx:beforeRequest', function(evt) {
            evt.target.classList.add('htmx-request');
        });
        
        document.body.addEventListener('htmx:afterRequest', function(evt) {
            evt.target.classList.remove('htmx-request');
        });
        
        // Toast notifications from HX-Trigger header
        document.body.addEventListener('showToast', function(evt) {
            const toast = document.createElement('div');
            toast.className = `toast toast-${evt.detail.type}`;
            toast.textContent = evt.detail.message;
            document.getElementById('toast-container').appendChild(toast);
            
            setTimeout(() => toast.remove(), 5000);
        });
    </script>
    
    <script src="{% static 'js/script.js' %}"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>
```

## HTMX Patterns for Each Feature

### Pattern 1: List with Live Search and Pagination

**File: `apps/credentials/templates/credentials/list.html`**

```html
{% extends 'base.html' %}
{% load static %}

{% block content %}
<div class="page-header">
    <h1>Credentials</h1>
    <button 
        hx-get="{% url 'credentials:create-form' %}"
        hx-target="#modal-container"
        hx-swap="innerHTML"
        class="btn btn-primary">
        Add Credential
    </button>
</div>

<!-- Live search -->
<div class="search-box">
    <input 
        type="search" 
        name="search"
        placeholder="Search credentials..."
        hx-get="{% url 'credentials:list-partial' %}"
        hx-trigger="keyup changed delay:300ms"
        hx-target="#credentials-table"
        hx-swap="innerHTML"
        hx-indicator="#search-spinner">
    <span id="search-spinner" class="htmx-indicator">🔄</span>
</div>

<div id="credentials-table">
    {% include 'credentials/partials/table.html' %}
</div>

<div id="modal-container"></div>
{% endblock %}
```

**File: `apps/credentials/templates/credentials/partials/table.html`**

```html
<table class="data-table">
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Status</th>
            <th>Actions</th>
        </tr>
    </thead>
    <tbody>
        {% for credential in credentials %}
        <tr id="credential-row-{{ credential.id }}">
            <td>{{ credential.name }}</td>
            <td>{{ credential.get_credential_type_display }}</td>
            <td>
                {% if credential.is_expired %}
                    <span class="badge badge-danger">Expired</span>
                {% else %}
                    <span class="badge badge-success">Active</span>
                {% endif %}
            </td>
            <td>
                <button 
                    hx-post="{% url 'credentials:verify' credential.id %}"
                    hx-target="#credential-row-{{ credential.id }}"
                    hx-swap="outerHTML"
                    class="btn btn-sm btn-info">
                    Verify
                </button>
                <button 
                    hx-delete="{% url 'credentials:delete' credential.id %}"
                    hx-target="#credential-row-{{ credential.id }}"
                    hx-swap="outerHTML swap:1s"
                    hx-confirm="Delete this credential?"
                    class="btn btn-sm btn-danger">
                    Delete
                </button>
            </td>
        </tr>
        {% empty %}
        <tr>
            <td colspan="4" class="text-center">No credentials found</td>
        </tr>
        {% endfor %}
    </tbody>
</table>

{% if is_paginated %}
<nav class="pagination">
    {% if page_obj.has_previous %}
    <a hx-get="?page={{ page_obj.previous_page_number }}"
       hx-target="#credentials-table"
       hx-swap="innerHTML"
       class="btn btn-link">Previous</a>
    {% endif %}
    
    <span>Page {{ page_obj.number }} of {{ page_obj.paginator.num_pages }}</span>
    
    {% if page_obj.has_next %}
    <a hx-get="?page={{ page_obj.next_page_number }}"
       hx-target="#credentials-table"
       hx-swap="innerHTML"
       class="btn btn-link">Next</a>
    {% endif %}
</nav>
{% endif %}
```

### Pattern 2: Modal Forms with Validation

**File: `apps/credentials/templates/credentials/partials/form_modal.html`**

```html
<div class="modal" id="credential-modal">
    <div class="modal-content">
        <div class="modal-header">
            <h2>{% if credential %}Edit{% else %}Create{% endif %} Credential</h2>
            <button type="button" class="close" onclick="this.closest('.modal').remove()">×</button>
        </div>
        
        <form 
            hx-post="{% if credential %}{% url 'credentials:update' credential.id %}{% else %}{% url 'credentials:create' %}{% endif %}"
            hx-target="#credentials-table"
            hx-swap="innerHTML"
            hx-on::after-request="if(event.detail.successful) this.closest('.modal').remove()">
            {% csrf_token %}
            
            <div class="form-group {% if form.name.errors %}has-error{% endif %}">
                <label for="id_name">Name</label>
                {{ form.name }}
                {% if form.name.errors %}
                <div class="error-message">{{ form.name.errors.0 }}</div>
                {% endif %}
            </div>
            
            <div class="form-group">
                <label for="id_credential_type">Type</label>
                <select 
                    name="credential_type" 
                    id="id_credential_type"
                    hx-get="{% url 'credentials:type-fields' %}"
                    hx-target="#credential-fields"
                    hx-trigger="change"
                    hx-include="[name='credential_type']">
                    <option value="">Select type...</option>
                    {% for value, label in form.credential_type.field.choices %}
                    <option value="{{ value }}">{{ label }}</option>
                    {% endfor %}
                </select>
            </div>
            
            <div id="credential-fields">
                <!-- Dynamically loaded based on type -->
            </div>
            
            <div class="form-actions">
                <button type="button" class="btn btn-secondary" 
                        onclick="this.closest('.modal').remove()">
                    Cancel
                </button>
                <button type="submit" class="btn btn-primary">
                    <span class="htmx-indicator">Saving...</span>
                    <span>Save</span>
                </button>
            </div>
        </form>
    </div>
</div>
```

### Pattern 3: Real-Time Updates with Server-Sent Events

**File: `apps/pipelines/templates/pipelines/run_detail.html`**

```html
{% extends 'base.html' %}

{% block content %}
<div class="pipeline-run">
    <h1>Pipeline Run #{{ run.id }}</h1>
    
    <!-- Real-time status updates -->
    <div 
        id="pipeline-status"
        hx-ext="sse"
        sse-connect="{% url 'pipelines:run-events' run.id %}"
        sse-swap="message"
        hx-swap="innerHTML">
        {% include 'pipelines/partials/status.html' %}
    </div>
    
    <!-- Live log streaming -->
    <div class="logs-container">
        <h3>Build Logs</h3>
        <pre 
            id="build-logs"
            hx-ext="sse"
            sse-connect="{% url 'pipelines:run-logs' run.id %}"
            sse-swap="log"
            hx-swap="beforeend">{{ run.logs }}</pre>
    </div>
    
    <div class="actions" id="pipeline-actions">
        {% if run.status == 'running' %}
        <button 
            hx-post="{% url 'pipelines:cancel' run.id %}"
            hx-target="#pipeline-status"
            class="btn btn-danger">
            Cancel Build
        </button>
        {% elif run.status == 'completed' %}
        <a href="{% url 'pipelines:download' run.id %}" class="btn btn-success">
            Download Output
        </a>
        {% endif %}
    </div>
</div>
{% endblock %}
```

## Django Views for HTMX

### ListView with HTMX Support

```python
from django.views.generic import ListView
from django.shortcuts import render

class CredentialListView(ListView):
    model = Credential
    template_name = 'credentials/list.html'
    context_object_name = 'credentials'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(is_active=True)
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset
    
    def get_template_names(self):
        # Return partial for HTMX requests
        if self.request.htmx:
            return ['credentials/partials/table.html']
        return [self.template_name]
```

### Form View with HTMX

```python
from django.views.generic import CreateView
from django.http import HttpResponse

class CredentialCreateView(CreateView):
    model = Credential
    form_class = CredentialForm
    template_name = 'credentials/partials/form_modal.html'
    
    def form_valid(self, form):
        self.object = form.save()
        
        if self.request.htmx:
            # Return updated table
            credentials = Credential.objects.filter(is_active=True)
            response = render(
                self.request,
                'credentials/partials/table.html',
                {'credentials': credentials}
            )
            # Trigger success toast
            response['HX-Trigger'] = json.dumps({
                'showToast': {
                    'type': 'success',
                    'message': 'Credential created successfully'
                }
            })
            return response
        
        return super().form_valid(form)
    
    def form_invalid(self, form):
        # Return form with errors
        return render(
            self.request,
            self.template_name,
            {'form': form},
            status=422  # Unprocessable Entity
        )
```

### SSE View for Real-Time Updates

```python
from django.http import StreamingHttpResponse
import time
import json

def pipeline_run_events(request, run_id):
    """Stream pipeline status updates via SSE."""
    
    def event_stream():
        pipeline = PipelineRun.objects.get(id=run_id)
        
        while pipeline.status in ['pending', 'running']:
            # Refresh from database
            pipeline.refresh_from_db()
            
            # Send status update
            status_html = render_to_string(
                'pipelines/partials/status.html',
                {'run': pipeline}
            )
            
            yield f"event: message\n"
            yield f"data: {status_html}\n\n"
            
            if pipeline.status in ['completed', 'failed']:
                break
            
            time.sleep(2)  # Poll every 2 seconds
    
    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
```

## HTMX CSS Styles

**File: `static/css/htmx.css`**

```css
/* Loading indicators */
.htmx-indicator {
    display: none;
}

.htmx-request .htmx-indicator {
    display: inline-block;
}

.htmx-request.htmx-indicator {
    display: inline-block;
}

/* Dim elements while loading */
.htmx-request {
    opacity: 0.7;
    pointer-events: none;
    cursor: wait;
}

/* Smooth transitions */
.htmx-swapping {
    opacity: 0;
    transition: opacity 0.2s ease-out;
}

.htmx-settling {
    opacity: 1;
    transition: opacity 0.2s ease-in;
}

/* Toast notifications */
.toast-container {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 1000;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.toast {
    padding: 1rem 1.5rem;
    border-radius: 4px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    animation: slideIn 0.3s ease-out;
    min-width: 250px;
}

.toast-success {
    background: #10b981;
    color: white;
}

.toast-error {
    background: #ef4444;
    color: white;
}

.toast-info {
    background: #3b82f6;
    color: white;
}

@keyframes slideIn {
    from {
        transform: translateX(100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

/* Modal styles */
.modal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

.modal-content {
    background: white;
    border-radius: 8px;
    padding: 2rem;
    max-width: 600px;
    width: 90%;
    max-height: 90vh;
    overflow-y: auto;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
}

.modal-header h2 {
    margin: 0;
}

.close {
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    color: #6b7280;
}

.close:hover {
    color: #111827;
}

/* Form styles */
.form-group {
    margin-bottom: 1rem;
}

.form-group.has-error input,
.form-group.has-error select,
.form-group.has-error textarea {
    border-color: #ef4444;
}

.error-message {
    color: #ef4444;
    font-size: 0.875rem;
    margin-top: 0.25rem;
}

.form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
    margin-top: 1.5rem;
}

/* Progress indicators */
.progress-bar {
    width: 100%;
    height: 4px;
    background: #e5e7eb;
    border-radius: 2px;
    overflow: hidden;
}

.progress-bar-fill {
    height: 100%;
    background: #3b82f6;
    transition: width 0.3s ease;
}

/* Skeleton loading */
.skeleton {
    background: linear-gradient(90deg, #f3f4f6 25%, #e5e7eb 50%, #f3f4f6 75%);
    background-size: 200% 100%;
    animation: loading 1.5s ease-in-out infinite;
}

@keyframes loading {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}
```

## URL Configuration

**File: `apps/credentials/urls.py`**

```python
from django.urls import path
from apps.credentials import views

app_name = 'credentials'

urlpatterns = [
    # Full page views
    path('', views.CredentialListView.as_view(), name='list'),
    
    # HTMX partial endpoints
    path('list-partial/', views.CredentialListView.as_view(), name='list-partial'),
    path('create-form/', views.CredentialCreateView.as_view(), name='create-form'),
    path('<int:pk>/edit-form/', views.CredentialUpdateView.as_view(), name='edit-form'),
    path('type-fields/', views.CredentialTypeFieldsView.as_view(), name='type-fields'),
    
    # Actions
    path('create/', views.CredentialCreateView.as_view(), name='create'),
    path('<int:pk>/update/', views.CredentialUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.CredentialDeleteView.as_view(), name='delete'),
    path('<int:pk>/verify/', views.CredentialVerifyView.as_view(), name='verify'),
]
```

## Testing HTMX Views

```python
import pytest
from django.urls import reverse
from django_htmx.middleware import HtmxDetails

@pytest.mark.django_db
class TestHTMXViews:
    
    def test_htmx_request_returns_partial(self, client, credential_factory):
        """Test that HTMX requests get partial templates."""
        credential_factory()
        
        url = reverse('credentials:list')
        response = client.get(url, HTTP_HX_REQUEST='true')
        
        assert response.status_code == 200
        # Should return partial, not full page
        assert b'<html' not in response.content
        assert b'<table' in response.content
    
    def test_htmx_form_validation(self, client):
        """Test HTMX form validation errors."""
        url = reverse('credentials:create')
        response = client.post(
            url,
            {'name': ''},  # Invalid
            HTTP_HX_REQUEST='true'
        )
        
        assert response.status_code == 422
        assert b'error' in response.content.lower()
    
    def test_htmx_delete(self, client, credential_factory):
        """Test HTMX delete returns empty response."""
        credential = credential_factory()
        
        url = reverse('credentials:delete', kwargs={'pk': credential.id})
        response = client.delete(url, HTTP_HX_REQUEST='true')
        
        assert response.status_code == 200
        assert response.content == b''  # Empty to remove row
```

## Migration Checklist for HTMX

- [ ] Install django-htmx package
- [ ] Add HTMX middleware to settings
- [ ] Download HTMX library to static files
- [ ] Create base template with HTMX setup
- [ ] Add HTMX CSS styles
- [ ] Convert list views to support HTMX partials
- [ ] Create modal form templates
- [ ] Implement dynamic form field loading
- [ ] Add real-time updates with SSE
- [ ] Test all HTMX interactions
- [ ] Add loading indicators
- [ ] Implement toast notifications
- [ ] Test form validation
- [ ] Add HTMX tests

## Benefits of This Approach

1. **Faster Development**: No separate frontend build process
2. **Better Performance**: Smaller payloads, faster page loads
3. **Easier Maintenance**: Single codebase, no API versioning issues
4. **Progressive Enhancement**: Works without JavaScript
5. **SEO Friendly**: Server-rendered HTML
6. **Django Native**: Leverages Django's strengths

---

*This addendum should be integrated into Phase 5 of the main migration plan.*