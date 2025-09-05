// Django Admin Tshaleeh Theme JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize theme controller
    const adminTheme = {
        // Theme state
        darkMode: false,
        
        // Initialize the admin theme
        init() {
            this.initTheme();
            this.initEventListeners();
            this.initAnimations();
            this.initTooltips();
        },
        
        // Initialize theme from localStorage or system preference
        initTheme() {
            const savedTheme = localStorage.getItem('admin-theme');
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            
            this.darkMode = savedTheme ? savedTheme === 'dark' : prefersDark;
            this.updateTheme();
        },
        
        // Set up event listeners
        initEventListeners() {
            // Theme toggle button
            const themeToggle = document.getElementById('theme-toggle');
            if (themeToggle) {
                themeToggle.addEventListener('click', () => this.toggleTheme());
            }
            
            // System theme change listener
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
                if (!localStorage.getItem('admin-theme')) {
                    this.darkMode = e.matches;
                    this.updateTheme();
                }
            });
            
            // Smooth scroll for anchor links
            document.querySelectorAll('a[href^="#"]').forEach(anchor => {
                anchor.addEventListener('click', function (e) {
                    e.preventDefault();
                    const target = document.querySelector(this.getAttribute('href'));
                    if (target) {
                        target.scrollIntoView({
                            behavior: 'smooth',
                            block: 'start'
                        });
                    }
                });
            });
            
            // Enhanced form interactions
            this.enhanceFormElements();
            
            // Auto-save form data
            this.initAutoSave();
        },
        
        // Toggle between light and dark theme
        toggleTheme() {
            this.darkMode = !this.darkMode;
            this.updateTheme();
            this.showThemeChangeNotification();
        },
        
        // Update theme classes and save to localStorage
        updateTheme() {
            const html = document.documentElement;
            const body = document.body;
            const themeToggle = document.getElementById('theme-toggle');
            
            if (this.darkMode) {
                html.classList.add('dark');
                body.classList.add('dark');
                body.setAttribute('data-theme', 'dark');
                localStorage.setItem('admin-theme', 'dark');
                
                if (themeToggle) {
                    themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
                    themeToggle.title = 'تبديل للوضع المضيء';
                }
            } else {
                html.classList.remove('dark');
                body.classList.remove('dark');
                body.setAttribute('data-theme', 'light');
                localStorage.setItem('admin-theme', 'light');
                
                if (themeToggle) {
                    themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
                    themeToggle.title = 'تبديل للوضع المظلم';
                }
            }
            
            // Force repaint
            html.style.colorScheme = this.darkMode ? 'dark' : 'light';
        },
        
        // Initialize animations
        initAnimations() {
            // Fade in modules on page load
            const modules = document.querySelectorAll('.module, .content-wrapper, .form-row');
            modules.forEach((module, index) => {
                module.style.opacity = '0';
                module.style.transform = 'translateY(20px)';
                
                setTimeout(() => {
                    module.style.transition = 'all 0.6s ease-out';
                    module.style.opacity = '1';
                    module.style.transform = 'translateY(0)';
                }, index * 100);
            });
            
            // Hover effects for buttons and links
            document.querySelectorAll('.button, .btn, .nav-item').forEach(element => {
                element.addEventListener('mouseenter', function() {
                    this.style.transform = 'translateY(-2px)';
                });
                
                element.addEventListener('mouseleave', function() {
                    this.style.transform = 'translateY(0)';
                });
            });
            
            // Loading animation for forms
            document.querySelectorAll('form').forEach(form => {
                form.addEventListener('submit', function() {
                    const submitBtn = this.querySelector('input[type="submit"], button[type="submit"]');
                    if (submitBtn) {
                        const originalText = submitBtn.textContent || submitBtn.value;
                        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> جاري الحفظ...';
                        submitBtn.disabled = true;
                        
                        // Re-enable after 3 seconds in case of error
                        setTimeout(() => {
                            submitBtn.innerHTML = originalText;
                            submitBtn.disabled = false;
                        }, 3000);
                    }
                });
            });
        },
        
        // Enhanced form elements
        enhanceFormElements() {
            // Real-time validation feedback
            document.querySelectorAll('input, select, textarea').forEach(input => {
                input.addEventListener('focus', function() {
                    this.style.borderColor = 'var(--primary-400)';
                    this.style.boxShadow = '0 0 0 3px rgba(20, 184, 166, 0.1)';
                });
                
                input.addEventListener('blur', function() {
                    this.style.borderColor = 'var(--border-glass)';
                    this.style.boxShadow = 'none';
                });
                
                input.addEventListener('input', function() {
                    this.style.borderColor = this.checkValidity() ? 
                        'var(--primary-400)' : '#ef4444';
                });
            });
            
            // Enhanced select dropdowns
            document.querySelectorAll('select').forEach(select => {
                select.style.backgroundImage = `url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='m6 8 4 4 4-4'/%3e%3c/svg%3e")`;
                select.style.backgroundPosition = 'left 0.5rem center';
                select.style.backgroundRepeat = 'no-repeat';
                select.style.backgroundSize = '1.5em 1.5em';
                select.style.paddingLeft = '2.5rem';
            });
        },
        
        // Auto-save functionality
        initAutoSave() {
            const forms = document.querySelectorAll('form[method="post"]');
            forms.forEach(form => {
                const formId = form.action || window.location.pathname;
                const inputs = form.querySelectorAll('input, select, textarea');
                
                // Load saved data
                inputs.forEach(input => {
                    const savedValue = localStorage.getItem(`autosave_${formId}_${input.name}`);
                    if (savedValue && input.value === '') {
                        input.value = savedValue;
                    }
                });
                
                // Save data on input
                inputs.forEach(input => {
                    input.addEventListener('input', () => {
                        localStorage.setItem(`autosave_${formId}_${input.name}`, input.value);
                    });
                });
                
                // Clear saved data on successful submission
                form.addEventListener('submit', () => {
                    inputs.forEach(input => {
                        localStorage.removeItem(`autosave_${formId}_${input.name}`);
                    });
                });
            });
        },
        
        // Initialize tooltips
        initTooltips() {
            document.querySelectorAll('[title]').forEach(element => {
                element.addEventListener('mouseenter', function(e) {
                    const tooltip = document.createElement('div');
                    tooltip.className = 'admin-tooltip';
                    tooltip.textContent = this.title;
                    tooltip.style.cssText = `
                        position: absolute;
                        background: var(--bg-glass);
                        backdrop-filter: var(--backdrop-blur);
                        border: 1px solid var(--border-glass);
                        border-radius: 8px;
                        padding: 8px 12px;
                        color: var(--text-primary);
                        font-size: 12px;
                        z-index: 1000;
                        pointer-events: none;
                        box-shadow: var(--shadow-glass);
                        opacity: 0;
                        transform: translateY(-5px);
                        transition: all 0.3s ease;
                    `;
                    
                    document.body.appendChild(tooltip);
                    
                    const rect = this.getBoundingClientRect();
                    tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
                    tooltip.style.top = rect.top - tooltip.offsetHeight - 10 + 'px';
                    
                    // Remove original title to prevent browser tooltip
                    this.setAttribute('data-original-title', this.title);
                    this.removeAttribute('title');
                    
                    // Animate in
                    setTimeout(() => {
                        tooltip.style.opacity = '1';
                        tooltip.style.transform = 'translateY(0)';
                    }, 10);
                });
                
                element.addEventListener('mouseleave', function() {
                    // Restore original title
                    if (this.getAttribute('data-original-title')) {
                        this.title = this.getAttribute('data-original-title');
                        this.removeAttribute('data-original-title');
                    }
                    
                    // Remove tooltip
                    const tooltip = document.querySelector('.admin-tooltip');
                    if (tooltip) {
                        tooltip.style.opacity = '0';
                        tooltip.style.transform = 'translateY(-5px)';
                        setTimeout(() => tooltip.remove(), 300);
                    }
                });
            });
        },
        
        // Show theme change notification
        showThemeChangeNotification() {
            const notification = document.createElement('div');
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: var(--bg-glass);
                backdrop-filter: var(--backdrop-blur);
                border: 1px solid var(--border-glass);
                border-radius: 10px;
                padding: 15px 20px;
                color: var(--text-primary);
                font-family: 'Cairo', sans-serif;
                font-weight: 500;
                z-index: 9999;
                box-shadow: var(--shadow-glass);
                opacity: 0;
                transform: translateX(100%);
                transition: all 0.3s ease;
            `;
            
            notification.innerHTML = `
                <div style="display: flex; align-items: center; gap: 10px;">
                    <i class="fas fa-${this.darkMode ? 'moon' : 'sun'}" style="color: var(--primary-500);"></i>
                    <span>تم التبديل إلى الوضع ${this.darkMode ? 'المظلم' : 'المضيء'}</span>
                </div>
            `;
            
            document.body.appendChild(notification);
            
            // Animate in
            setTimeout(() => {
                notification.style.opacity = '1';
                notification.style.transform = 'translateX(0)';
            }, 10);
            
            // Animate out and remove
            setTimeout(() => {
                notification.style.opacity = '0';
                notification.style.transform = 'translateX(100%)';
                setTimeout(() => notification.remove(), 300);
            }, 3000);
        },
        
        // Utility function to show custom notifications
        showNotification(message, type = 'info', duration = 3000) {
            const notification = document.createElement('div');
            const colors = {
                success: '#10b981',
                error: '#ef4444',
                warning: '#f59e0b',
                info: 'var(--primary-500)'
            };
            
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: var(--bg-glass);
                backdrop-filter: var(--backdrop-blur);
                border: 1px solid var(--border-glass);
                border-radius: 10px;
                padding: 15px 20px;
                color: var(--text-primary);
                font-family: 'Cairo', sans-serif;
                font-weight: 500;
                z-index: 9999;
                box-shadow: var(--shadow-glass);
                opacity: 0;
                transform: translateY(-20px);
                transition: all 0.3s ease;
                border-left: 4px solid ${colors[type]};
                max-width: 300px;
            `;
            
            notification.textContent = message;
            document.body.appendChild(notification);
            
            // Animate in
            setTimeout(() => {
                notification.style.opacity = '1';
                notification.style.transform = 'translateY(0)';
            }, 10);
            
            // Animate out and remove
            setTimeout(() => {
                notification.style.opacity = '0';
                notification.style.transform = 'translateY(-20px)';
                setTimeout(() => notification.remove(), 300);
            }, duration);
        }
    };
    
    // Initialize the admin theme
    adminTheme.init();
    
    // Make adminTheme globally available
    window.adminTheme = adminTheme;
    
    // Enhanced Django Admin specific features
    function enhanceDjangoAdmin() {
        // Admin-specific enhancements
        
        // Enhanced navigation
        const adminLinks = document.querySelectorAll('#header a, .breadcrumbs a');
        adminLinks.forEach(link => {
            link.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-1px)';
            });
            
            link.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
            });
        });
        
        // Enhanced module interactions
        const modules = document.querySelectorAll('.module');
        modules.forEach((module, index) => {
            // Add staggered animation
            module.style.opacity = '0';
            module.style.transform = 'translateY(20px)';
            
            setTimeout(() => {
                module.style.transition = 'all 0.6s ease-out';
                module.style.opacity = '1';
                module.style.transform = 'translateY(0)';
            }, index * 100);
        });
        
        // Enhanced table interactions
        const tables = document.querySelectorAll('table');
        tables.forEach(table => {
            const rows = table.querySelectorAll('tbody tr');
            rows.forEach(row => {
                row.addEventListener('click', function(e) {
                    if (e.target.tagName !== 'A' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'BUTTON') {
                        const firstLink = this.querySelector('a');
                        if (firstLink && !e.target.closest('.action-checkbox-column')) {
                            window.location.href = firstLink.href;
                        }
                    }
                });
                
                row.style.cursor = 'pointer';
            });
        });
        
        // Enhanced form interactions
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            const inputs = form.querySelectorAll('input, select, textarea');
            inputs.forEach(input => {
                // Add floating label effect
                if (input.type !== 'hidden' && input.type !== 'checkbox' && input.type !== 'radio') {
                    input.addEventListener('focus', function() {
                        const label = this.closest('.form-row')?.querySelector('label');
                        if (label) {
                            label.style.color = 'var(--primary-500)';
                            label.style.transform = 'scale(0.9)';
                        }
                    });
                    
                    input.addEventListener('blur', function() {
                        const label = this.closest('.form-row')?.querySelector('label');
                        if (label) {
                            label.style.color = 'var(--text-primary)';
                            label.style.transform = 'scale(1)';
                        }
                    });
                }
            });
        });
        
        // Enhanced action dropdown
        const actionSelect = document.querySelector('select[name="action"]');
        if (actionSelect) {
            actionSelect.addEventListener('change', function() {
                const goButton = document.querySelector('button[name="index"]');
                if (this.value && goButton) {
                    goButton.style.background = 'var(--primary-500)';
                    goButton.style.color = 'white';
                } else if (goButton) {
                    goButton.style.background = 'var(--default-button-bg)';
                    goButton.style.color = 'var(--text-primary)';
                }
            });
        }
        
        // Enhanced pagination
        const paginationLinks = document.querySelectorAll('.paginator a');
        paginationLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                if (!this.href.includes('#')) {
                    this.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                    this.style.pointerEvents = 'none';
                }
            });
        });
        
        // Enhanced search functionality
        const searchForm = document.querySelector('#changelist-search form');
        if (searchForm) {
            const searchInput = searchForm.querySelector('input[type="text"]');
            const searchButton = searchForm.querySelector('input[type="submit"]');
            
            if (searchInput && searchButton) {
                // Add search suggestions (placeholder for future enhancement)
                searchInput.addEventListener('input', function() {
                    if (this.value.length > 2) {
                        // Here you could add AJAX search suggestions
                        console.log('Search for:', this.value);
                    }
                });
                
                // Enhanced search button
                searchForm.addEventListener('submit', function() {
                    searchButton.value = 'جاري البحث...';
                    searchButton.disabled = true;
            });
        }
    }

        // Auto-hide messages
        const messages = document.querySelectorAll('.messagelist li, .success, .error, .warning');
        messages.forEach(message => {
            setTimeout(() => {
                message.style.transition = 'all 0.5s ease-out';
                message.style.opacity = '0';
                message.style.transform = 'translateY(-20px)';
                
                setTimeout(() => {
                    message.remove();
                }, 500);
            }, 5000);
        });
        
        // Enhanced filter sidebar
        const filterSidebar = document.querySelector('#changelist-filter');
        if (filterSidebar) {
            const filterLinks = filterSidebar.querySelectorAll('a');
            filterLinks.forEach(link => {
                link.addEventListener('click', function() {
                    filterLinks.forEach(l => l.classList.remove('loading'));
                    this.classList.add('loading');
                    this.innerHTML += ' <i class="fas fa-spinner fa-spin" style="margin-right: 5px;"></i>';
                });
            });
        }
        
        // Enhanced delete confirmations
        const deleteLinks = document.querySelectorAll('.deletelink, .deletelink-box a');
        deleteLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                
                adminTheme.showNotification(
                    'هل أنت متأكد من الحذف؟ هذا الإجراء لا يمكن التراجع عنه.',
                    'warning',
                    0 // Don't auto-hide
                );
                
                // Add custom confirmation dialog
                const confirmDialog = document.createElement('div');
                confirmDialog.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0, 0, 0, 0.7);
                display: flex;
                align-items: center;
                justify-content: center;
                    z-index: 10000;
                `;
                
                confirmDialog.innerHTML = `
                    <div style="
                        background: var(--bg-glass);
                        backdrop-filter: var(--backdrop-blur);
                        border: 1px solid var(--border-glass);
                        border-radius: 20px;
                        padding: 30px;
                        max-width: 400px;
                        text-align: center;
                        color: var(--text-primary);
                        font-family: 'Cairo', sans-serif;
                    ">
                        <i class="fas fa-exclamation-triangle" style="font-size: 3rem; color: #f59e0b; margin-bottom: 20px;"></i>
                        <h3 style="margin: 0 0 15px 0;">تأكيد الحذف</h3>
                        <p style="margin: 0 0 25px 0; color: var(--text-secondary);">
                            هل أنت متأكد من حذف هذا العنصر؟ لا يمكن التراجع عن هذا الإجراء.
                        </p>
                        <div style="display: flex; gap: 15px; justify-content: center;">
                            <button class="cancel-btn" style="
                                background: var(--bg-surface);
                                color: var(--text-primary);
                                border: 1px solid var(--border-glass);
                                border-radius: 8px;
                                padding: 10px 20px;
                                cursor: pointer;
                                font-family: 'Cairo', sans-serif;
                                font-weight: 500;
                            ">إلغاء</button>
                            <button class="confirm-btn" style="
                                background: linear-gradient(135deg, #dc2626, #b91c1c);
                                color: white;
                                border: none;
                border-radius: 8px;
                                padding: 10px 20px;
                                cursor: pointer;
                                font-family: 'Cairo', sans-serif;
                font-weight: 500;
                            ">حذف</button>
                        </div>
                    </div>
                `;
                
                document.body.appendChild(confirmDialog);
                
                confirmDialog.querySelector('.cancel-btn').addEventListener('click', () => {
                    document.body.removeChild(confirmDialog);
                });
                
                confirmDialog.querySelector('.confirm-btn').addEventListener('click', () => {
                    window.location.href = link.href;
                });
                
                confirmDialog.addEventListener('click', (e) => {
                    if (e.target === confirmDialog) {
                        document.body.removeChild(confirmDialog);
                    }
                });
            });
        });
    }
    
    // Initialize Django Admin enhancements
    enhanceDjangoAdmin();
    
    // Enhanced table interactions
    document.querySelectorAll('table tbody tr').forEach(row => {
        row.addEventListener('click', function(e) {
            if (e.target.tagName !== 'A' && e.target.tagName !== 'BUTTON' && e.target.tagName !== 'INPUT') {
                const link = this.querySelector('a');
                if (link) {
                    window.location.href = link.href;
                }
            }
        });
        
        row.style.cursor = 'pointer';
    });
    
    // Enhanced search functionality
    const searchBar = document.getElementById('searchbar');
    if (searchBar) {
        searchBar.addEventListener('input', function() {
            const query = this.value.toLowerCase();
            const rows = document.querySelectorAll('table tbody tr');
            
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(query) ? '' : 'none';
            });
        });
    }
    
    // Auto-refresh functionality for dashboard
    if (window.location.pathname.includes('/admin/')) {
        // Refresh every 5 minutes for dashboard pages
        setTimeout(() => {
            if (document.hasFocus()) {
                window.location.reload();
            }
        }, 300000);
    }
    
    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + D to toggle dark mode
        if ((e.ctrlKey || e.metaKey) && e.key === 'd') {
            e.preventDefault();
            adminTheme.toggleTheme();
        }
        
        // Escape to close modals/notifications
        if (e.key === 'Escape') {
            document.querySelectorAll('.admin-tooltip').forEach(tooltip => tooltip.remove());
        }
    });
    
    // Performance monitoring
    if ('performance' in window) {
        window.addEventListener('load', () => {
            const loadTime = performance.timing.loadEventEnd - performance.timing.navigationStart;
            if (loadTime > 3000) {
                console.warn(`Page load time: ${loadTime}ms - Consider optimizing`);
            }
        });
    }
});

// Utility functions for external use
window.showAdminNotification = function(message, type = 'info', duration = 3000) {
    if (window.adminTheme) {
        window.adminTheme.showNotification(message, type, duration);
    }
};

// Export data functionality
window.exportTableData = function(tableSelector = 'table', filename = 'data') {
    const table = document.querySelector(tableSelector);
    if (!table) return;
    
    let csv = '';
    const rows = table.querySelectorAll('tr');
    
    rows.forEach(row => {
        const cells = row.querySelectorAll('th, td');
        const rowData = Array.from(cells).map(cell => 
            `"${cell.textContent.trim().replace(/"/g, '""')}"`
        ).join(',');
        csv += rowData + '\n';
    });
    
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${filename}_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    
    showAdminNotification('تم تصدير البيانات بنجاح', 'success');
};

// Print functionality
window.printPage = function() {
    window.print();
};