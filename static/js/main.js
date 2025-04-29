// Main JavaScript File for Scientific Paper Explorer

document.addEventListener("DOMContentLoaded", function() {
  // Initialize components
  initializeThemeToggle();
  initializeNavbarToggle();
  initializeBookmarkButtons();
  initializeCharts();
  initializeExpandableAbstracts();
  
  // Form validation
  const forms = document.querySelectorAll('.needs-validation');
  Array.from(forms).forEach(form => {
    form.addEventListener('submit', event => {
      if (!form.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
      }
      form.classList.add('was-validated');
    }, false);
  });
});

// Dark mode toggle
function initializeThemeToggle() {
  const themeToggle = document.getElementById('theme-toggle');
  const themeIcon = document.getElementById('theme-icon');
  
  if (!themeToggle) return;
  
  // Check for saved theme preference or prefer-color-scheme
  const savedTheme = localStorage.getItem('theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  
  if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
    document.body.classList.add('dark-mode');
    themeIcon.classList.replace('fa-moon', 'fa-sun');
  }
  
  themeToggle.addEventListener('click', () => {
    document.body.classList.toggle('dark-mode');
    
    // Update icon
    if (document.body.classList.contains('dark-mode')) {
      themeIcon.classList.replace('fa-moon', 'fa-sun');
      localStorage.setItem('theme', 'dark');
    } else {
      themeIcon.classList.replace('fa-sun', 'fa-moon');
      localStorage.setItem('theme', 'light');
    }
  });
}

// Mobile navbar toggle
function initializeNavbarToggle() {
  const mobileToggle = document.getElementById('mobile-toggle');
  const navbarLinks = document.querySelector('.navbar-links');
  const navbarAuth = document.querySelector('.navbar-auth');
  
  if (!mobileToggle) return;
  
  mobileToggle.addEventListener('click', () => {
    navbarLinks.classList.toggle('active');
    navbarAuth.classList.toggle('active');
    
    // Update icon
    const icon = mobileToggle.querySelector('i');
    if (navbarLinks.classList.contains('active')) {
      icon.classList.replace('fa-bars', 'fa-times');
    } else {
      icon.classList.replace('fa-times', 'fa-bars');
    }
  });
}

// Bookmark functionality
function initializeBookmarkButtons() {
  const bookmarkButtons = document.querySelectorAll('.bookmark-btn');
  
  bookmarkButtons.forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      
      const paperData = JSON.parse(btn.dataset.paper);
      const icon = btn.querySelector('i');
      
      try {
        const response = await fetch('/bookmark', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(paperData)
        });
        
        const data = await response.json();
        
        // Show toast notification
        showToast(data.message);
        
        // Update icon state if successfully bookmarked
        if (response.ok && !data.message.includes('already')) {
          icon.classList.remove('far');
          icon.classList.add('fas');
          btn.classList.add('active');
        }
        
      } catch (error) {
        showToast('Error adding bookmark. Please try again.');
        console.error('Error:', error);
      }
    });
  });
}

// Delete bookmark functionality
function initializeDeleteBookmarks() {
  const deleteButtons = document.querySelectorAll('.delete-bookmark');
  const deleteAllButton = document.getElementById('delete-all-bookmarks');
  
  deleteButtons.forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      
      if (!confirm('Are you sure you want to remove this bookmark?')) {
        return;
      }
      
      const title = btn.dataset.title;
      
      try {
        const response = await fetch('/delete_bookmark', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ title })
        });
        
        const data = await response.json();
        showToast(data.message);
        
        // Remove the card from DOM
        if (response.ok) {
          const card = btn.closest('.card');
          card.style.opacity = '0';
          setTimeout(() => {
            card.remove();
            
            // Check if there are any bookmarks left
            const remainingCards = document.querySelectorAll('.bookmark-card');
            if (remainingCards.length === 0) {
              const resultsContainer = document.querySelector('.results-grid');
              resultsContainer.innerHTML = '<p class="text-center">No bookmarks found. Start exploring papers to add some!</p>';
              
              // Hide the delete all button
              if (deleteAllButton) {
                deleteAllButton.style.display = 'none';
              }
            }
          }, 300);
        }
      } catch (error) {
        showToast('Error deleting bookmark. Please try again.');
        console.error('Error:', error);
      }
    });
  });
  
  // Delete all bookmarks
  if (deleteAllButton) {
    deleteAllButton.addEventListener('click', async (e) => {
      e.preventDefault();
      
      if (!confirm('Are you sure you want to delete all bookmarks? This action cannot be undone.')) {
        return;
      }
      
      try {
        const response = await fetch('/delete_all_bookmarks', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          }
        });
        
        const data = await response.json();
        showToast(data.message);
        
        // Clear all bookmarks from DOM
        if (response.ok) {
          const resultsContainer = document.querySelector('.results-grid');
          resultsContainer.innerHTML = '<p class="text-center">No bookmarks found. Start exploring papers to add some!</p>';
          
          // Hide the delete all button
          deleteAllButton.style.display = 'none';
        }
      } catch (error) {
        showToast('Error deleting bookmarks. Please try again.');
        console.error('Error:', error);
      }
    });
  }
}

// Toast notification
function showToast(message) {
  // Check if toast container exists, if not create it
  let toastContainer = document.querySelector('.toast-container');
  
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.className = 'toast-container';
    document.body.appendChild(toastContainer);
    
    // Add style for toast container if not in CSS
    toastContainer.style.position = 'fixed';
    toastContainer.style.bottom = '1rem';
    toastContainer.style.right = '1rem';
    toastContainer.style.zIndex = '1050';
  }
  
  // Create toast
  const toast = document.createElement('div');
  toast.className = 'toast show';
  toast.style.backgroundColor = 'var(--gray-800)';
  toast.style.color = 'white';
  toast.style.padding = '0.75rem 1.25rem';
  toast.style.borderRadius = 'var(--radius)';
  toast.style.marginTop = '0.5rem';
  toast.style.boxShadow = 'var(--shadow-md)';
  toast.style.minWidth = '250px';
  toast.style.opacity = '0';
  toast.style.transition = 'opacity 0.3s ease';
  
  toast.textContent = message;
  
  // Add to container
  toastContainer.appendChild(toast);
  
  // Animate in
  setTimeout(() => {
    toast.style.opacity = '1';
  }, 10);
  
  // Remove after 3 seconds
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => {
      toast.remove();
    }, 300);
  }, 3000);
}

// Initialize chart.js for visualizations
function initializeCharts() {
  // Source distribution chart
  const sourceChart = document.getElementById('sourceChart');
  if (sourceChart) {
    const labels = JSON.parse(sourceChart.dataset.labels);
    const data = JSON.parse(sourceChart.dataset.values);
    
    new Chart(sourceChart, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data: data,
          backgroundColor: [
            '#4361ee',
            '#3a0ca3',
            '#7209b7',
            '#f72585',
            '#4cc9f0',
            '#06d6a0',
            '#bb3e03',
            '#ee9b00',
            '#ae2012',
            '#6a4c93'
          ],
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: {
            position: 'right',
          },
          title: {
            display: true,
            text: 'Papers by Source'
          }
        }
      }
    });
  }
  
  // Year distribution chart
  const yearChart = document.getElementById('yearChart');
  if (yearChart) {
    const labels = JSON.parse(yearChart.dataset.labels);
    const data = JSON.parse(yearChart.dataset.values);
    
    new Chart(yearChart, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Papers by Year',
          data: data,
          backgroundColor: '#7209b7',
          borderColor: '#3a0ca3',
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: {
            display: false,
          },
          title: {
            display: true,
            text: 'Papers by Year'
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              precision: 0
            }
          }
        }
      }
    });
  }
}

// Expandable abstracts
function initializeExpandableAbstracts() {
  const abstracts = document.querySelectorAll('.truncate-multi');
  const expandButtons = document.querySelectorAll('.expand-abstract');
  
  expandButtons.forEach((btn, index) => {
    btn.addEventListener('click', () => {
      const abstract = abstracts[index];
      abstract.classList.toggle('truncate-multi');
      
      if (abstract.classList.contains('truncate-multi')) {
        btn.textContent = 'Read more';
      } else {
        btn.textContent = 'Read less';
      }
    });
  });
}

// Export results functionality
document.addEventListener('DOMContentLoaded', function() {
  const exportButton = document.getElementById('export-results');
  
  if (exportButton) {
    exportButton.addEventListener('click', function() {
      window.location.href = '/download_csv';
    });
  }
});