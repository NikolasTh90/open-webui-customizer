/**
 * Enhanced Pipeline JavaScript for Custom Fork Cloning.
 * 
 * This script provides frontend functionality for the enhanced pipeline
 * features including custom Git repository management, build step configuration,
 * and pipeline execution monitoring.
 * 
 * Author: Open WebUI Customizer Team
 */

class EnhancedPipelineManager {
    constructor() {
        this.apiBase = '/api/pipelines';
        this.repositoryApiBase = '/api/repositories';
        this.credentialApiBase = '/api/credentials';
        
        this.currentPipelineRun = null;
        this.availableSteps = [];
        this.repositories = [];
        this.credentials = [];
        
        this.init();
    }
    
    async init() {
        console.log('Initializing Enhanced Pipeline Manager...');
        
        // Load initial data
        await this.loadAvailableSteps();
        await this.loadRepositories();
        await this.loadCredentials();
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Initialize UI components
        this.initializeUIComponents();
        
        console.log('Enhanced Pipeline Manager initialized successfully');
    }
    
    async loadAvailableSteps() {
        try {
            const response = await fetch(`${this.apiBase}/steps`);
            const data = await response.json();
            
            if (data.success) {
                this.availableSteps = data.build_steps;
                this.renderBuildSteps();
            } else {
                console.error('Failed to load build steps:', data);
                this.showError('Failed to load available build steps');
            }
        } catch (error) {
            console.error('Error loading build steps:', error);
            this.showError('Error loading build steps');
        }
    }
    
    async loadRepositories() {
        try {
            const response = await fetch(`${this.repositoryApiBase}?include_experimental=true`);
            const data = await response.json();
            
            if (data.success) {
                this.repositories = data.repositories;
                this.renderRepositoryOptions();
            } else {
                console.error('Failed to load repositories:', data);
            }
        } catch (error) {
            console.error('Error loading repositories:', error);
        }
    }
    
    async loadCredentials() {
        try {
            const response = await fetch(`${this.credentialApiBase}`);
            const data = await response.json();
            
            if (data.success) {
                this.credentials = data.credentials;
            } else {
                console.error('Failed to load credentials:', data);
            }
        } catch (error) {
            console.error('Error loading credentials:', error);
        }
    }
    
    setupEventListeners() {
        // Create pipeline form
        const createForm = document.getElementById('create-pipeline-form');
        if (createForm) {
            createForm.addEventListener('submit', (e) => this.handleCreatePipeline(e));
        }
        
        // Output type selection
        const outputTypeSelect = document.getElementById('output-type');
        if (outputTypeSelect) {
            outputTypeSelect.addEventListener('change', () => this.updateStepSelection());
        }
        
        // Repository selection
        const repositorySelect = document.getElementById('git-repository');
        if (repositorySelect) {
            repositorySelect.addEventListener('change', () => this.updateRepositoryInfo());
        }
        
        // Execute pipeline buttons
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('execute-pipeline-btn')) {
                const runId = parseInt(e.target.dataset.runId);
                this.executePipeline(runId);
            }
        });
        
        // View logs buttons
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('view-logs-btn')) {
                const runId = parseInt(e.target.dataset.runId);
                this.viewPipelineLogs(runId);
            }
        });
        
        // Download output buttons
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('download-output-btn')) {
                const outputId = parseInt(e.target.dataset.outputId);
                this.downloadBuildOutput(outputId);
            }
        });
        
        // Refresh pipeline runs
        const refreshBtn = document.getElementById('refresh-pipelines-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadPipelineRuns());
        }
    }
    
    initializeUIComponents() {
        // Initialize tooltips
        this.initializeTooltips();
        
        // Initialize status badges
        this.updateStatusBadges();
        
        // Load initial pipeline runs
        this.loadPipelineRuns();
    }
    
    renderBuildSteps() {
        const container = document.getElementById('build-steps-container');
        if (!container) return;
        
        const stepsHtml = this.availableSteps.map(step => `
            <div class="build-step-item">
                <label class="checkbox-label">
                    <input type="checkbox" 
                           name="build_steps" 
                           value="${step.key}"
                           data-step="${step.key}"
                           data-required="${step.required}"
                           ${step.required ? 'checked disabled' : ''}>
                    <span class="step-name">${step.name}</span>
                    <span class="step-description">${step.description}</span>
                    ${step.required ? '<span class="required-badge">Required</span>' : ''}
                </label>
            </div>
        `).join('');
        
        container.innerHTML = stepsHtml;
        
        // Add step dependency listeners
        container.querySelectorAll('input[name="build_steps"]').forEach(checkbox => {
            checkbox.addEventListener('change', () => this.validateStepDependencies());
        });
    }
    
    renderRepositoryOptions() {
        const select = document.getElementById('git-repository');
        if (!select) return;
        
        // Clear existing options except the first (default) option
        while (select.children.length > 1) {
            select.removeChild(select.lastChild);
        }
        
        // Add repository options
        this.repositories.forEach(repo => {
            const option = document.createElement('option');
            option.value = repo.id;
            option.textContent = `${repo.name} (${repo.repository_url})`;
            option.dataset.repositoryType = repo.repository_type;
            option.dataset.isVerified = repo.is_verified;
            
            // Add verification status indicator
            if (repo.is_verified) {
                option.textContent += ' ✓';
            } else {
                option.textContent += ' ⚠️';
            }
            
            select.appendChild(option);
        });
    }
    
    updateStepSelection() {
        const outputType = document.getElementById('output-type').value;
        
        // Auto-select relevant steps based on output type
        const steps = {
            zip: ['clone_repo', 'create_zip'],
            docker_image: ['clone_repo', 'build_image'],
            both: ['clone_repo', 'create_zip', 'build_image']
        };
        
        const relevantSteps = steps[outputType] || [];
        
        document.querySelectorAll('input[name="build_steps"]').forEach(checkbox => {
            const stepKey = checkbox.dataset.step;
            
            if (checkbox.dataset.required === 'true') {
                // Keep required steps checked
                return;
            }
            
            // Check if step is relevant for the output type
            checkbox.checked = relevantSteps.includes(stepKey);
        });
        
        this.validateStepDependencies();
    }
    
    validateStepDependencies() {
        const selectedSteps = Array.from(document.querySelectorAll('input[name="build_steps"]:checked'))
                                  .map(cb => cb.dataset.step);
        
        // Define dependencies
        const dependencies = {
            create_zip: ['clone_repo'],
            build_image: ['clone_repo'],
            push_registry: ['clone_repo', 'build_image'],
            apply_branding: ['clone_repo'],
            apply_config: ['clone_repo']
        };
        
        // Check and highlight dependency issues
        Object.entries(dependencies).forEach(([step, deps]) => {
            const checkbox = document.querySelector(`input[data-step="${step}"]`);
            if (!checkbox || checkbox.dataset.required === 'true') return;
            
            const isSelected = selectedSteps.includes(step);
            const depsSatisfied = deps.every(dep => selectedSteps.includes(dep));
            
            if (isSelected && !depsSatisfied) {
                checkbox.parentElement.classList.add('dependency-warning');
                checkbox.parentElement.title = `Missing dependencies: ${deps.join(', ')}`;
            } else {
                checkbox.parentElement.classList.remove('dependency-warning');
                checkbox.parentElement.title = '';
            }
        });
    }
    
    updateRepositoryInfo() {
        const select = document.getElementById('git-repository');
        const infoContainer = document.getElementById('repository-info');
        
        if (!select || !infoContainer) return;
        
        const repositoryId = parseInt(select.value);
        
        if (!repositoryId) {
            infoContainer.innerHTML = '';
            return;
        }
        
        const repository = this.repositories.find(r => r.id === repositoryId);
        if (!repository) return;
        
        const infoHtml = `
            <div class="repository-info-card ${repository.is_verified ? 'verified' : 'unverified'}">
                <h4>Repository Information</h4>
                <p><strong>Name:</strong> ${repository.name}</p>
                <p><strong>URL:</strong> <code>${repository.repository_url}</code></p>
                <p><strong>Type:</strong> ${repository.repository_type.toUpperCase()}</p>
                <p><strong>Default Branch:</strong> ${repository.default_branch}</p>
                <p><strong>Status:</strong> 
                    <span class="status-badge ${repository.is_verified ? 'success' : 'warning'}">
                        ${repository.is_verified ? 'Verified' : 'Not Verified'}
                    </span>
                </p>
                ${repository.verification_message ? 
                    `<p><strong>Verification:</strong> ${repository.verification_message}</p>` : ''}
                <p><strong>Created:</strong> ${new Date(repository.created_at).toLocaleDateString()}</p>
            </div>
        `;
        
        infoContainer.innerHTML = infoHtml;
    }
    
    async handleCreatePipeline(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        const data = Object.fromEntries(formData.entries());
        
        // Process build steps
        const buildSteps = Array.from(document.querySelectorAll('input[name="build_steps"]:checked'))
                               .map(cb => cb.dataset.step);
        
        if (buildSteps.length === 0) {
            this.showError('Please select at least one build step');
            return;
        }
        
        // Validate dependencies
        if (!this.validateStepDependenciesForSubmission(buildSteps)) {
            return;
        }
        
        // Prepare API data
        const pipelineData = {
            steps_to_execute: buildSteps,
            git_repository_id: data.git_repository_id || null,
            output_type: data.output_type || 'zip',
            registry_id: data.registry_id || null
        };
        
        try {
            const response = await fetch(`${this.apiBase}/runs`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(pipelineData)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Pipeline run created successfully');
                this.loadPipelineRuns(); // Refresh the list
                
                // Optionally execute immediately
                if (data.execute_immediately) {
                    this.executePipeline(result.pipeline_run.id);
                }
                
                // Reset form
                event.target.reset();
                this.updateRepositoryInfo();
            } else {
                this.showError(result.message || 'Failed to create pipeline run');
            }
        } catch (error) {
            console.error('Error creating pipeline run:', error);
            this.showError('Error creating pipeline run');
        }
    }
    
    validateStepDependenciesForSubmission(selectedSteps) {
        const dependencies = {
            create_zip: ['clone_repo'],
            build_image: ['clone_repo'],
            push_registry: ['clone_repo', 'build_image'],
            apply_branding: ['clone_repo'],
            apply_config: ['clone_repo']
        };
        
        for (const [step, deps] of Object.entries(dependencies)) {
            if (selectedSteps.includes(step)) {
                const missingDeps = deps.filter(dep => !selectedSteps.includes(dep));
                if (missingDeps.length > 0) {
                    this.showError(`Step '${step}' requires: ${missingDeps.join(', ')}`);
                    return false;
                }
            }
        }
        
        return true;
    }
    
    async loadPipelineRuns() {
        try {
            const response = await fetch(`${this.apiBase}/runs`);
            const data = await response.json();
            
            if (data.success) {
                this.renderPipelineRuns(data.runs);
            } else {
                console.error('Failed to load pipeline runs:', data);
            }
        } catch (error) {
            console.error('Error loading pipeline runs:', error);
        }
    }
    
    renderPipelineRuns(runs) {
        const container = document.getElementById('pipeline-runs-container');
        if (!container) return;
        
        if (runs.length === 0) {
            container.innerHTML = '<p class="no-data">No pipeline runs found</p>';
            return;
        }
        
        const runsHtml = runs.map(run => `
            <div class="pipeline-run-card" data-run-id="${run.id}">
                <div class="run-header">
                    <h3>Run #${run.id}</h3>
                    <span class="status-badge ${run.status}">${run.status.toUpperCase()}</span>
                </div>
                
                <div class="run-details">
                    <p><strong>Output Type:</strong> ${run.output_type}</p>
                    <p><strong>Steps:</strong> ${run.steps_to_execute.join(', ')}</p>
                    <p><strong>Started:</strong> ${new Date(run.started_at).toLocaleString()}</p>
                    ${run.completed_at ? 
                        `<p><strong>Completed:</strong> ${new Date(run.completed_at).toLocaleString()}</p>` : ''}
                    
                    ${run.repository_info ? `
                        <div class="repository-summary">
                            <strong>Repository:</strong> ${run.repository_info.name} 
                            (${run.repository_info.repo_name})
                        </div>
                    ` : ''}
                </div>
                
                <div class="run-actions">
                    ${run.status === 'pending' ? 
                        `<button class="btn btn-primary execute-pipeline-btn" data-run-id="${run.id}">
                            Execute
                        </button>` : ''}
                    
                    <button class="btn btn-secondary view-logs-btn" data-run-id="${run.id}">
                        View Logs
                    </button>
                    
                    ${run.build_outputs && run.build_outputs.length > 0 ? 
                        `<button class="btn btn-success view-outputs-btn" data-run-id="${run.id}">
                            View Outputs (${run.build_outputs.length})
                        </button>` : ''}
                </div>
            </div>
        `).join('');
        
        container.innerHTML = runsHtml;
    }
    
    async executePipeline(runId) {
        try {
            const btn = document.querySelector(`.execute-pipeline-btn[data-run-id="${runId}"]`);
            if (btn) {
                btn.disabled = true;
                btn.textContent = 'Executing...';
            }
            
            const response = await fetch(`${this.apiBase}/runs/${runId}/execute`, {
                method: 'POST'
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Pipeline execution started');
                // Start monitoring the run
                this.monitorPipelineRun(runId);
            } else {
                this.showError(result.message || 'Failed to execute pipeline');
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = 'Execute';
                }
            }
        } catch (error) {
            console.error('Error executing pipeline:', error);
            this.showError('Error executing pipeline');
        }
    }
    
    async monitorPipelineRun(runId) {
        const checkStatus = async () => {
            try {
                const response = await fetch(`${this.apiBase}/runs/${runId}`);
                const data = await response.json();
                
                if (data.success) {
                    const run = data.pipeline_run;
                    
                    // Update the UI
                    this.updatePipelineRunCard(run);
                    
                    // Continue monitoring if still running
                    if (run.status === 'running') {
                        setTimeout(checkStatus, 5000); // Check every 5 seconds
                    } else {
                        // Execution completed
                        this.showSuccess(`Pipeline ${run.status}`);
                        this.loadPipelineRuns(); // Refresh the list
                    }
                }
            } catch (error) {
                console.error('Error monitoring pipeline run:', error);
            }
        };
        
        checkStatus();
    }
    
    updatePipelineRunCard(run) {
        const card = document.querySelector(`.pipeline-run-card[data-run-id="${run.id}"]`);
        if (!card) return;
        
        // Update status badge
        const statusBadge = card.querySelector('.status-badge');
        if (statusBadge) {
            statusBadge.className = `status-badge ${run.status}`;
            statusBadge.textContent = run.status.toUpperCase();
        }
        
        // Update completed time
        if (run.completed_at) {
            const completedAtEl = card.querySelector('p:contains("Completed")');
            if (completedAtEl) {
                completedAtEl.textContent = `Completed: ${new Date(run.completed_at).toLocaleString()}`;
            }
        }
    }
    
    async viewPipelineLogs(runId) {
        try {
            const response = await fetch(`${this.apiBase}/runs/${runId}/logs`);
            const logs = await response.text();
            
            // Show logs in modal
            this.showLogsModal(runId, logs);
        } catch (error) {
            console.error('Error viewing logs:', error);
            this.showError('Error loading logs');
        }
    }
    
    showLogsModal(runId, logs) {
        const modal = document.createElement('div');
        modal.className = 'modal logs-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Pipeline Run #${runId} - Logs</h3>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    <pre class="logs-content">${logs}</pre>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary modal-close">Close</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Setup modal close handlers
        modal.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', () => {
                document.body.removeChild(modal);
            });
        });
        
        // Close on outside click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                document.body.removeChild(modal);
            }
        });
    }
    
    async downloadBuildOutput(outputId) {
        try {
            window.open(`${this.apiBase}/outputs/${outputId}/download`, '_blank');
        } catch (error) {
            console.error('Error downloading output:', error);
            this.showError('Error downloading output');
        }
    }
    
    initializeTooltips() {
        // Initialize any tooltip library if present
        if (typeof tippy !== 'undefined') {
            tippy('[data-tooltip]', {
                theme: 'light',
                placement: 'top'
            });
        }
    }
    
    updateStatusBadges() {
        // Update status badge colors and animations
        document.querySelectorAll('.status-badge').forEach(badge => {
            const status = badge.textContent.toLowerCase();
            
            // Add animation for running status
            if (status === 'running') {
                badge.classList.add('pulse');
            }
        });
    }
    
    showSuccess(message) {
        this.showNotification(message, 'success');
    }
    
    showError(message) {
        this.showNotification(message, 'error');
    }
    
    showNotification(message, type) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        // Add to page
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (document.body.contains(notification)) {
                document.body.removeChild(notification);
            }
        }, 5000);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.enhancedPipelineManager = new EnhancedPipelineManager();
});

// Export for potential module usage
export { EnhancedPipelineManager };