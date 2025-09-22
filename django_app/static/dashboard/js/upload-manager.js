/**
 * Upload Manager for per-row image uploads
 * Allows adding new item rows while images are uploading
 */

class UploadManager {
    constructor() {
        this.uploadStates = new Map(); // Track upload states per row
        this.uploadQueue = []; // Queue for pending uploads
        this.isProcessing = false;
    }

    /**
     * Initialize upload manager for a form
     */
    init(formSelector) {
        const form = document.querySelector(formSelector);
        if (!form) return;

        // Add event listeners for file inputs
        form.addEventListener('change', (e) => {
            if (e.target.type === 'file' && e.target.multiple) {
                this.handleFileSelection(e.target);
            }
        });

        // Add event listeners for new row buttons
        form.addEventListener('click', (e) => {
            if (e.target.classList.contains('add-item-row')) {
                this.addNewItemRow(e.target);
            }
        });
    }

    /**
     * Handle file selection for a specific row
     */
    handleFileSelection(fileInput) {
        const rowId = this.getRowId(fileInput);
        const files = Array.from(fileInput.files);
        
        if (files.length === 0) return;

        // Set upload state for this row
        this.uploadStates.set(rowId, {
            status: 'uploading',
            files: files,
            progress: 0
        });

        // Update UI to show upload status
        this.updateRowStatus(rowId, 'uploading');

        // Process uploads
        this.processUploads(rowId, files);
    }

    /**
     * Process file uploads for a specific row
     */
    async processUploads(rowId, files) {
        const uploadPromises = files.map(file => this.uploadFile(file, rowId));
        
        try {
            const results = await Promise.allSettled(uploadPromises);
            const successful = results.filter(r => r.status === 'fulfilled').length;
            const failed = results.filter(r => r.status === 'rejected').length;

            if (failed === 0) {
                this.updateRowStatus(rowId, 'completed');
                this.uploadStates.set(rowId, { status: 'completed', files: files });
            } else if (successful > 0) {
                this.updateRowStatus(rowId, 'partial');
                this.uploadStates.set(rowId, { status: 'partial', files: files });
            } else {
                this.updateRowStatus(rowId, 'failed');
                this.uploadStates.set(rowId, { status: 'failed', files: files });
            }
        } catch (error) {
            console.error('Upload error:', error);
            this.updateRowStatus(rowId, 'failed');
        }
    }

    /**
     * Upload a single file
     */
    async uploadFile(file, rowId) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('row_id', rowId);

        try {
            const response = await fetch('/api/upload/image/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            if (!response.ok) {
                throw new Error(`Upload failed: ${response.statusText}`);
            }

            const result = await response.json();
            return result;
        } catch (error) {
            console.error('File upload error:', error);
            throw error;
        }
    }

    /**
     * Update row status UI
     */
    updateRowStatus(rowId, status) {
        const row = document.querySelector(`[data-row-id="${rowId}"]`);
        if (!row) return;

        const statusElement = row.querySelector('.upload-status');
        if (!statusElement) return;

        // Remove existing status classes
        statusElement.className = 'upload-status';
        
        switch (status) {
            case 'uploading':
                statusElement.classList.add('uploading');
                statusElement.innerHTML = '<i class="fas fa-spinner fa-spin"></i> رفع الصور...';
                break;
            case 'completed':
                statusElement.classList.add('completed');
                statusElement.innerHTML = '<i class="fas fa-check-circle"></i> تم الرفع بنجاح';
                break;
            case 'partial':
                statusElement.classList.add('partial');
                statusElement.innerHTML = '<i class="fas fa-exclamation-triangle"></i> رفع جزئي';
                break;
            case 'failed':
                statusElement.classList.add('failed');
                statusElement.innerHTML = '<i class="fas fa-times-circle"></i> فشل الرفع';
                break;
        }
    }

    /**
     * Add new item row
     */
    addNewItemRow(button) {
        const container = button.closest('.items-container');
        if (!container) return;

        const rowTemplate = container.querySelector('.item-row-template');
        if (!rowTemplate) return;

        // Clone the template
        const newRow = rowTemplate.cloneNode(true);
        newRow.classList.remove('item-row-template');
        newRow.classList.add('item-row');
        
        // Generate unique row ID
        const rowId = 'row_' + Date.now();
        newRow.setAttribute('data-row-id', rowId);
        
        // Clear form fields
        newRow.querySelectorAll('input, textarea').forEach(input => {
            if (input.type !== 'file') {
                input.value = '';
            }
        });

        // Insert before the add button
        button.parentNode.insertBefore(newRow, button);
        
        // Initialize upload state
        this.uploadStates.set(rowId, { status: 'ready', files: [] });
    }

    /**
     * Get row ID from element
     */
    getRowId(element) {
        const row = element.closest('[data-row-id]');
        return row ? row.getAttribute('data-row-id') : null;
    }

    /**
     * Get CSRF token
     */
    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    /**
     * Check if any uploads are in progress
     */
    hasActiveUploads() {
        return Array.from(this.uploadStates.values()).some(state => 
            state.status === 'uploading'
        );
    }

    /**
     * Get upload status for a row
     */
    getRowStatus(rowId) {
        return this.uploadStates.get(rowId) || { status: 'ready', files: [] };
    }
}

// Initialize upload manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.uploadManager = new UploadManager();
    window.uploadManager.init('#request-form');
});

// Export for use in other scripts
window.UploadManager = UploadManager;
