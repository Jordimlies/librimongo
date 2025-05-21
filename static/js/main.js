/**
 * LibriMongo - Fitxer JavaScript principal
 */

document.addEventListener('DOMContentLoaded', function() {
    // Inicialitza els tooltips de Bootstrap
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Inicialitza els popovers de Bootstrap
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Tanca automàticament les alertes
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
    
    // Afegeix la classe activa a l'element de navegació actual
    var currentLocation = window.location.pathname;
    var navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    navLinks.forEach(function(link) {
        if (link.getAttribute('href') === currentLocation) {
            link.classList.add('active');
        }
    });

    // Funcionalitat del filtre lateral
    initSidebarFilters();
    
    // Millora de l'entrada de valoració
    initRatingInput();
    
    // Autocompletat de la cerca de llibres
    initSearchAutocomplete();
});

/**
 * Inicialitza la funcionalitat del filtre lateral
 */
function initSidebarFilters() {
    // Envia automàticament el formulari quan canvien els camps de selecció
    const autoSubmitFields = document.querySelectorAll('#sidebarFilterForm select, #sidebarFilterForm input[type="checkbox"]');
    if (autoSubmitFields.length > 0) {
        autoSubmitFields.forEach(field => {
            field.addEventListener('change', function() {
                document.getElementById('sidebarFilterForm').submit();
            });
        });
    }
    
    // Validació del filtre de rang d'anys
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
    
    // Alternança del filtre en dispositius mòbils
    const filterToggleBtn = document.getElementById('filterToggleBtn');
    const sidebarFilters = document.getElementById('sidebarFilters');
    
    if (filterToggleBtn && sidebarFilters) {
        filterToggleBtn.addEventListener('click', function() {
            sidebarFilters.classList.toggle('show');
        });
    }
}

/**
 * Inicialitza la millora de l'entrada de valoració
 */
function initRatingInput() {
    const ratingInputs = document.querySelectorAll('.rating-input');
    
    ratingInputs.forEach(container => {
        const radioInputs = container.querySelectorAll('input[type="radio"]');
        const labels = container.querySelectorAll('label');
        
        // Afegeix icones d'estrella a les etiquetes
        labels.forEach(label => {
            const value = label.getAttribute('for').replace('rating', '');
            label.innerHTML = '★';
            label.setAttribute('title', value + ' stars');
        });
        
        // Ressalta les estrelles en passar el cursor i fer clic
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
        
        // Inicialitza amb el valor actual
        for (let i = 0; i < radioInputs.length; i++) {
            if (radioInputs[i].checked) {
                updateStars(labels, i);
                break;
            }
        }
    });
}

/**
 * Actualitza la visualització de la valoració amb estrelles
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
 * Ressalta les estrelles en passar el cursor
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
 * Reinicia les estrelles per a coincidir amb el valor seleccionat
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
 * Inicialitza l'autocompletat de la cerca
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
                    // Això s'implementaria si tinguéssim un desplegable per a l'autocompletat
                    console.log('Search results:', data);
                })
                .catch(error => console.error('Error fetching search results:', error));
        }, 300));
    }
}

/**
 * Funció de debounce per limitar les crides a l'API
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