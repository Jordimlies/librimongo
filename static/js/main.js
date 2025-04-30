/**
 * LibriMongo - Main JavaScript File
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize Bootstrap popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Auto-dismiss alerts
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
    
    // Add active class to current nav item
    var currentLocation = window.location.pathname;
    var navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    navLinks.forEach(function(link) {
        if (link.getAttribute('href') === currentLocation) {
            link.classList.add('active');
        }
    });

    // Sidebar filter functionality
    initSidebarFilters();
    
    // Rating input enhancement
    initRatingInput();
    
    // Book search autocomplete
    initSearchAutocomplete();
});

/**
 * Initialize sidebar filter functionality
 */
function initSidebarFilters() {
    // Auto-submit form when select fields change
    const autoSubmitFields = document.querySelectorAll('#sidebarFilterForm select, #sidebarFilterForm input[type="checkbox"]');
    if (autoSubmitFields.length > 0) {
        autoSubmitFields.forEach(field => {
            field.addEventListener('change', function() {
                document.getElementById('sidebarFilterForm').submit();
            });
        });
    }
    
    // Year range filter validation
    const yearFromInput = document.getElementById('year_from');
    const yearToInput = document.getElementById('year_to');
    
    if (yearFromInput && yearToInput) {
        yearFromInput.addEventListener('change', function() {
            if (yearToInput.value && parseInt(yearFromInput.value) > parseInt(yearToInput.value)) {
                yearToInput.value = yearFromInput.value;
            }
        });
        
        yearToInput.addEventListener('change', function() {
            if (yearFromInput.value && parseInt(yearToInput.value) < parseInt(yearFromInput.value)) {
                yearFromInput.value = yearToInput.value;
            }
        });
    }
    
    // Mobile filter toggle
    const filterToggleBtn = document.getElementById('filterToggleBtn');
    const sidebarFilters = document.getElementById('sidebarFilters');
    
    if (filterToggleBtn && sidebarFilters) {
        filterToggleBtn.addEventListener('click', function() {
            sidebarFilters.classList.toggle('show');
        });
    }
}

/**
 * Initialize rating input enhancement
 */
function initRatingInput() {
    const ratingInputs = document.querySelectorAll('.rating-input');
    
    ratingInputs.forEach(container => {
        const radioInputs = container.querySelectorAll('input[type="radio"]');
        const labels = container.querySelectorAll('label');
        
        // Add star icons to labels
        labels.forEach(label => {
            const value = label.getAttribute('for').replace('rating', '');
            label.innerHTML = '★';
            label.setAttribute('title', value + ' stars');
        });
        
        // Highlight stars on hover and click
        radioInputs.forEach((input, index) => {
            input.addEventListener('change', function() {
                updateStars(labels, index);
            });
            
            labels[index].addEventListener('mouseenter', function() {
                highlightStars(labels, index);
            });
        });
        
        container.addEventListener('mouseleave', function() {
            resetStars(labels, radioInputs);
        });
        
        // Initialize with current value
        for (let i = 0; i < radioInputs.length; i++) {
            if (radioInputs[i].checked) {
                updateStars(labels, i);
                break;
            }
        }
    });
}

/**
 * Update star ratings display
 */
function updateStars(labels, selectedIndex) {
    labels.forEach((label, i) => {
        if (i <= selectedIndex) {
            label.classList.add('text-warning');
        } else {
            label.classList.remove('text-warning');
        }
    });
}

/**
 * Highlight stars on hover
 */
function highlightStars(labels, hoverIndex) {
    labels.forEach((label, i) => {
        if (i <= hoverIndex) {
            label.classList.add('text-warning');
        } else {
            label.classList.remove('text-warning');
        }
    });
}

/**
 * Reset stars to match selected value
 */
function resetStars(labels, radioInputs) {
    let selectedIndex = -1;
    
    for (let i = 0; i < radioInputs.length; i++) {
        if (radioInputs[i].checked) {
            selectedIndex = i;
            break;
        }
    }
    
    labels.forEach((label, i) => {
        if (i <= selectedIndex) {
            label.classList.add('text-warning');
        } else {
            label.classList.remove('text-warning');
        }
    });
}

/**
 * Initialize search autocomplete
 */
function initSearchAutocomplete() {
    const searchInput = document.querySelector('input[name="query"]');
    
    if (searchInput) {
        searchInput.addEventListener('input', debounce(function() {
            const query = searchInput.value.trim();
            
            if (query.length < 2) return;
            
            fetch(`/books/api/search?query=${encodeURIComponent(query)}&per_page=5`)
                .then(response => response.json())
                .then(data => {
                    // This would be implemented if we had a dropdown for autocomplete
                    console.log('Search results:', data);
                })
                .catch(error => console.error('Error fetching search results:', error));
        }, 300));
    }
}

/**
 * Debounce function to limit API calls
 */
function debounce(func, wait) {
    let timeout;
    return function() {
        const context = this;
        const args = arguments;
        clearTimeout(timeout);
        timeout = setTimeout(() => {
            func.apply(context, args);
        }, wait);
    };
}