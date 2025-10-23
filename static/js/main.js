// Global game state
let gameState = {
    currentScore: 0,
    usedHints: 0,
    completedImages: [],
    currentImage: null
};

// Status polling
function startStatusPolling() {
    setInterval(() => {
        fetch('/api/status')
            .then(response => response.json())
            .then(data => {
                updateStatus(data.status, data.score);
                
                if (data.status === 'offline' && window.location.pathname !== '/dashboard') {
                    alert('Admin has ended your game session!');
                    window.location.href = '/dashboard';
                }
            })
            .catch(error => console.error('Status check failed:', error));
    }, 3000);
}

function updateStatus(status, score) {
    const statusElement = document.getElementById('status-indicator');
    const startButton = document.getElementById('start-game-btn');
    
    if (statusElement) {
        statusElement.textContent = status === 'online' ? '🟢 Online' : '🔴 Offline';
        statusElement.className = `status-indicator ${status === 'online' ? 'status-online' : 'status-offline'}`;
    }
    
    if (startButton) {
        startButton.disabled = status !== 'online';
        if (status === 'online') {
            startButton.classList.add('pulse');
        } else {
            startButton.classList.remove('pulse');
        }
    }
    
    // Update score if on dashboard
    const scoreElement = document.getElementById('current-score');
    if (scoreElement) {
        scoreElement.textContent = score;
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    startStatusPolling();
    
    // Add floating animation to elements
    const cards = document.querySelectorAll('.glass-card, .stat-card');
    cards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
    });
});