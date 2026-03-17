/**
 * API Helper Functions
 * Handles all API requests with authentication
 */

const API_BASE_URL = '';  // Use relative URLs since frontend is served by FastAPI

/**
 * Make authenticated API request
 */
async function apiRequest(endpoint, method = 'GET', body = null) {
    const token = localStorage.getItem('token');
    
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        }
    };

    // Add authorization header if token exists
    if (token) {
        options.headers['Authorization'] = `Bearer ${token}`;
    }

    // Add body for POST/PUT requests
    if (body && (method === 'POST' || method === 'PUT')) {
        options.body = JSON.stringify(body);
    }

    try {
        const response = await fetch(API_BASE_URL + endpoint, options);
        
        // Handle 401 Unauthorized
        if (response.status === 401) {
            localStorage.removeItem('token');
            window.location.href = '/login';
            throw new Error('Unauthorized');
        }

        // Parse JSON response
        const data = await response.json();

        // Handle error responses
        if (!response.ok) {
            throw new Error(data.detail || 'Request failed');
        }

        return data;
    } catch (error) {
        console.error('API Request Error:', error);
        throw error;
    }
}

/**
 * Check if user is authenticated
 */
function isAuthenticated() {
    return !!localStorage.getItem('token');
}

/**
 * Logout user
 */
function logout() {
    localStorage.removeItem('token');
    window.location.href = '/login';
}

/**
 * Check authentication and redirect if not logged in
 */
function checkAuth() {
    if (!isAuthenticated()) {
        window.location.href = '/login';
    }
}

/**
 * Format date
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

/**
 * Format match score as percentage
 */
function formatMatchScore(score) {
    return (score * 100).toFixed(1) + '%';
}

/**
 * Get match class based on score
 */
function getMatchClass(score) {
    const percent = score * 100;
    if (percent >= 90) return 'success';
    if (percent >= 80) return 'primary';
    if (percent >= 75) return 'info';
    return 'secondary';
}