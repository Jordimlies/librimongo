document.addEventListener('DOMContentLoaded', function () {
    // === Gráfico de historial de lectura ===
    const chartCanvas = document.getElementById('readingHistoryChart');

    if (chartCanvas) {
        const ctx = chartCanvas.getContext('2d');

        // Datos insertados desde el template con data-* o directamente en una variable global en el template
        const monthlyReads = JSON.parse(chartCanvas.dataset.reads);  // [{year: 2025, month: 5, count: 3}, ...]

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
                        ticks: { stepSize: 1 }
                    }
                }
            }
        });
    }

    // === Otros eventos personalizados del dashboard se pueden añadir aquí ===
});