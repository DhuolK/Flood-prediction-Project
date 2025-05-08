// Handle form submissions
document.addEventListener('DOMContentLoaded', function() {
    // Login form
    const loginForm = document.querySelector('form[name="login_form"]');
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            
            // Basic validation
            if (!email || !password) {
                showError('Please fill in all fields');
                return;
            }
            
            // Submit form
            this.submit();
        });
    }
    
    // Signup form
    const signupForm = document.querySelector('form[name="signup_form"]');
    if (signupForm) {
        signupForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const name = document.getElementById('name').value;
            const email = document.getElementById('email').value;
            const mobile = document.getElementById('mobilenumber').value;
            const password = document.getElementById('password').value;
            
            // Basic validation
            if (!name || !email || !mobile || !password) {
                showError('Please fill in all fields');
                return;
            }
            
            // Submit form
            this.submit();
        });
    }
    
    // Reset password form
    const resetPasswordForm = document.querySelector('form[name="reset_password_form"]');
    if (resetPasswordForm) {
        resetPasswordForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const password = document.getElementById('password').value;
            const confirmPassword = document.getElementById('confirm_password').value;
            
            // Basic validation
            if (!password || !confirmPassword) {
                showError('Please fill in all fields');
                return;
            }
            
            if (password !== confirmPassword) {
                showError('Passwords do not match');
                return;
            }
            
            // Submit form
            this.submit();
        });
    }
    
    // Forgot password form
    const forgotPasswordForm = document.querySelector('form[name="reset_password_form"]');
    if (forgotPasswordForm && window.location.pathname === '/forgot_password') {
        forgotPasswordForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const email = document.getElementById('email').value;
            
            // Basic validation
            if (!email) {
                showError('Please enter your email address');
                return;
            }
            
            // Submit form
            this.submit();
        });
    }
    
    // Prediction form
    const predictionForm = document.querySelector('form[action="/predict"]');
    if (predictionForm) {
        predictionForm.addEventListener('submit', function(e) {
            const cityInput = document.getElementById('city');
            if (cityInput && !cityInput.value.trim()) {
                e.preventDefault();
                showError('Please enter a city name');
            }
        });
    }
    
    // Chart form
    const chartForm = document.querySelector('form[action="/chart"]');
    if (chartForm) {
        chartForm.addEventListener('submit', function(e) {
            const citySelect = document.getElementById('city');
            if (citySelect && !citySelect.value) {
                e.preventDefault();
                showError('Please select a city');
            }
        });
    }
});

// Show error message
function showError(message) {
    const errorElement = document.querySelector('.error');
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.classList.remove('error--hidden');
    }
}

// Show success message
function showSuccess(message) {
    const successElement = document.querySelector('.success');
    if (successElement) {
        successElement.textContent = message;
        successElement.classList.remove('success--hidden');
    }
}

// Handle flash messages
document.addEventListener('DOMContentLoaded', function() {
    const flashMessages = document.querySelectorAll('.flash-message');
    if (flashMessages.length > 0) {
        // Auto-hide flash messages after 5 seconds
        setTimeout(function() {
            flashMessages.forEach(function(message) {
                message.style.opacity = '0';
                setTimeout(function() {
                    message.remove();
                }, 500);
            });
        }, 5000);
    }
}); 