 
    // static/js/api_client.js

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    async function apiClient(url, options = {}) {
        const defaultOptions = {
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
                ...options.headers,
            },
        };

        const finalOptions = { ...options, ...defaultOptions };

        try {
            const response = await fetch(url, finalOptions);

            if (response.status === 204) { // No Content
                return null;
            }

            const data = await response.json();

            if (!response.ok) {
                const errorMessage = data.detail || data.error || JSON.stringify(data);
                throw new Error(errorMessage);
            }

            return data;
        } catch (error) {
            console.error(`API Client Error for ${url}:`, error);
            throw error;
        }
    }
    