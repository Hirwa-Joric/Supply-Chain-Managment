// Chart.js configurations and utilities

// Common chart options
const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            position: 'bottom'
        }
    }
};

// Color schemes
const colors = {
    primary: '#4e73df',
    success: '#1cc88a',
    info: '#36b9cc',
    warning: '#f6c23e',
    danger: '#e74a3b',
    secondary: '#858796'
};

// Create line chart
function createLineChart(ctx, labels, data, label) {
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: data,
                borderColor: colors.primary,
                tension: 0.3,
                fill: false
            }]
        },
        options: {
            ...commonOptions,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Create bar chart
function createBarChart(ctx, labels, data, label) {
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: data,
                backgroundColor: Object.values(colors),
                borderWidth: 1
            }]
        },
        options: {
            ...commonOptions,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Create doughnut chart
function createDoughnutChart(ctx, labels, data) {
    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: Object.values(colors),
                borderWidth: 1
            }]
        },
        options: commonOptions
    });
}

// Format currency
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(value);
}

// Format date
function formatDate(date) {
    return new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric'
    }).format(new Date(date));
}

// Update chart data
function updateChartData(chart, labels, data) {
    chart.data.labels = labels;
    chart.data.datasets[0].data = data;
    chart.update();
}

// Export functions
window.chartUtils = {
    createLineChart,
    createBarChart,
    createDoughnutChart,
    formatCurrency,
    formatDate,
    updateChartData,
    colors
};