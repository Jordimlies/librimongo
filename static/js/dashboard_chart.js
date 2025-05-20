document.addEventListener('DOMContentLoaded', function() {
    const ctx = document.getElementById('readingHistoryChart').getContext('2d');

    // Extraer datos de estadísticas desde una variable global definida en el HTML
    const monthlyReads = window.monthlyReads || [];
    const labels = monthlyReads.map(item => {
        const monthNames = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
        return `${monthNames[item.month - 1]} ${item.year}`;
    });
    const data = monthlyReads.map(item => item.count);

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Libros Leídos',
                data: data,
                backgroundColor: 'rgba(13, 110, 253, 0.7)',
                borderColor: 'rgba(13, 110, 253, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
});
