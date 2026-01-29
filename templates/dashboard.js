new Chart(document.getElementById('monthlyChart'), {
  type: 'bar',
  data: {
    labels: MONTHLY_LABELS,
    datasets: [{
      label: 'Applications per month',
      data: MONTHLY_DATA
    }]
  }
});

// Status pie chart
new Chart(document.getElementById('statusChart'), {
  type: 'pie',
  data: {
    labels: STATUS_LABELS,
    datasets: [{
      data: STATUS_VALUES
    }]
  }
});