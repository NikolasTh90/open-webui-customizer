// Drag and drop functionality for file uploads
document.addEventListener('DOMContentLoaded', function() {
    const dragDropAreas = document.querySelectorAll('.drag-drop-area');
    
    dragDropAreas.forEach(area => {
        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            area.addEventListener(eventName, preventDefaults, false);
        });
        
        // Highlight drop area when item is dragged over it
        ['dragenter', 'dragover'].forEach(eventName => {
            area.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            area.addEventListener(eventName, unhighlight, false);
        });
        
        // Handle dropped files
        area.addEventListener('drop', handleDrop, false);
        
        // Handle file input change
        const fileInput = area.querySelector('input[type="file"]');
        if (fileInput) {
            fileInput.addEventListener('change', handleFileSelect, false);
        }
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    function highlight(e) {
        const area = e.target.closest('.drag-drop-area');
        if (area) {
            area.classList.add('drag-over');
        }
    }
    
    function unhighlight(e) {
        const area = e.target.closest('.drag-drop-area');
        if (area) {
            area.classList.remove('drag-over');
        }
    }
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        const area = e.target.closest('.drag-drop-area');
        if (area) {
            handleFiles(files, area);
        }
    }
    
    function handleFileSelect(e) {
        const files = e.target.files;
        const area = e.target.closest('.drag-drop-area');
        if (area) {
            handleFiles(files, area);
        }
    }
    
    function handleFiles(files, area) {
        const fileList = area.querySelector('.file-list');
        if (!fileList) return;
        
        fileList.innerHTML = '';
        [...files].forEach(file => {
            const fileItem = document.createElement('div');
            fileItem.className = 'flex justify-between items-center p-2 bg-gray-50 rounded';
            fileItem.innerHTML = `
                <div>
                    <p class="text-sm font-medium text-gray-900">${file.name}</p>
                    <p class="text-xs text-gray-500">${formatFileSize(file.size)}</p>
                </div>
                <button type="button" class="text-red-500 hover:text-red-700 remove-file">
                    <i class="fas fa-times"></i>
                </button>
            `;
            fileList.appendChild(fileItem);
            
            // Add event listener to remove button
            fileItem.querySelector('.remove-file').addEventListener('click', function() {
                fileItem.remove();
                updateFileInputValue(area);
            });
        });
        
        // Update file input value for form submission
        updateFileInputValue(area);
    }
    
    function updateFileInputValue(area) {
        const fileInput = area.querySelector('input[type="file"]');
        const fileList = area.querySelector('.file-list');
        if (!fileInput || !fileList) return;
        
        // Get file names from the list
        const fileNames = Array.from(fileList.querySelectorAll('.file-list-item'))
            .map(item => item.dataset.fileName);
        
        // Update the file input value (this is a bit of a hack for display purposes)
        if (fileNames.length > 0) {
            fileInput.nextElementSibling.innerHTML = `${fileNames.length} file(s) selected`;
        } else {
            fileInput.nextElementSibling.innerHTML = 'Choose files or drag & drop here';
        }
    }
    
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    // Add file item to list (for programmatically adding files)
    window.addFileToList = function(fileName, fileSize, area) {
        const fileList = area.querySelector('.file-list');
        if (!fileList) return;
        
        const fileItem = document.createElement('div');
        fileItem.className = 'file-list-item flex justify-between items-center p-2 bg-gray-50 rounded';
        fileItem.dataset.fileName = fileName;
        fileItem.innerHTML = `
            <div>
                <p class="text-sm font-medium text-gray-900">${fileName}</p>
                <p class="text-xs text-gray-500">${formatFileSize(fileSize)}</p>
            </div>
            <button type="button" class="text-red-500 hover:text-red-700 remove-file">
                <i class="fas fa-times"></i>
            </button>
        `;
        fileList.appendChild(fileItem);
        
        // Add event listener to remove button
        fileItem.querySelector('.remove-file').addEventListener('click', function() {
            fileItem.remove();
            updateFileInputValue(area);
        });
        
        // Update file input value
        updateFileInputValue(area);
    };
    
    // Pipeline execution with real-time logs
    const pipelineForm = document.getElementById('pipeline-form');
    if (pipelineForm) {
        pipelineForm.addEventListener('htmx:afterRequest', function(evt) {
            if (evt.detail.successful) {
                // Refresh pipeline runs list
                htmx.ajax('GET', '/api/v1/pipeline/runs', '#pipeline-runs');
            }
        });
    }
    
    // Auto-refresh for running pipelines
    function autoRefreshPipelineRuns() {
        const pipelineRuns = document.getElementById('pipeline-runs');
        if (pipelineRuns) {
            // Check if there are any running pipelines
            const runningPipelines = pipelineRuns.querySelectorAll('.status-running');
            if (runningPipelines.length > 0) {
                // Refresh the list
                htmx.ajax('GET', '/api/v1/pipeline/runs', '#pipeline-runs');
                
                // Schedule next refresh
                setTimeout(autoRefreshPipelineRuns, 5000);
            }
        }
    }
    
    // Start auto-refresh if there are running pipelines
    setTimeout(autoRefreshPipelineRuns, 5000);
});