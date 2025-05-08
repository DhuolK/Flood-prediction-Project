document.addEventListener('DOMContentLoaded', () => {
    const signupForm = document.forms.signup_form;
    const loginForm = document.forms.login_form;
    const resetForm = document.forms.reset_password_form;
    const newPasswordForm = document.forms.new_password_form;

    if (signupForm) {
        signupForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const errorElement = signupForm.querySelector('.error');
            
            try {
                const response = await fetch('/signup', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        name: signupForm.name.value,
                        email: signupForm.email.value,
                        mobilenumber: signupForm.mobilenumber.value,
                        password: signupForm.password.value
                    })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    alert('Operation successful! Redirecting to the predict page.');
                    window.location.href = '/index';
                } else {
                    errorElement.textContent = data.error;
                    errorElement.classList.remove('error--hidden');
                }
            } catch (error) {
                errorElement.textContent = 'An error occurred. Please try again.';
                errorElement.classList.remove('error--hidden');
            }
        });
    }

    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const errorElement = loginForm.querySelector('.error');
            
            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        email: loginForm.email.value,
                        password: loginForm.password.value
                    })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    window.location.href = '/index';
                } else {
                    errorElement.textContent = data.error;
                    errorElement.classList.remove('error--hidden');
                }
            } catch (error) {
                console.error('Login error:', error);
                errorElement.textContent = 'An error occurred. Please try again.';
                errorElement.classList.remove('error--hidden');
            }
        });
    }

    if (resetForm) {
        resetForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const errorElement = resetForm.querySelector('.error');
            const successElement = resetForm.querySelector('.success');
            
            try {
                const response = await fetch('/auth/forgot-password', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        email: resetForm.email.value
                    })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    errorElement.classList.add('error--hidden');
                    successElement.textContent = 'Reset link sent to your email';
                    successElement.classList.remove('success--hidden');
                    resetForm.reset();
                } else {
                    errorElement.textContent = data.error;
                    errorElement.classList.remove('error--hidden');
                }
            } catch (error) {
                errorElement.textContent = 'An error occurred. Please try again.';
                errorElement.classList.remove('error--hidden');
            }
        });
    }

    if (newPasswordForm) {
        newPasswordForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const errorElement = newPasswordForm.querySelector('.error');
            const successElement = newPasswordForm.querySelector('.success');
            
            if (newPasswordForm.password.value !== newPasswordForm.confirm_password.value) {
                errorElement.textContent = 'Passwords do not match';
                errorElement.classList.remove('error--hidden');
                successElement.classList.add('success--hidden');
                return;
            }
            
            try {
                const token = window.location.pathname.split('/').pop();
                
                const response = await fetch(`/reset-password/${token}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        password: newPasswordForm.password.value
                    })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    errorElement.classList.add('error--hidden');
                    successElement.textContent = 'Password updated successfully! Redirecting...';
                    successElement.classList.remove('success--hidden');
                    
                    setTimeout(() => {
                        window.location.href = '/login';
                    }, 2000);
                } else {
                    errorElement.textContent = data.error;
                    errorElement.classList.remove('error--hidden');
                    successElement.classList.add('success--hidden');
                }
            } catch (error) {
                errorElement.textContent = 'An error occurred. Please try again.';
                errorElement.classList.add('error--hidden');
                successElement.classList.remove('success--hidden');
            }
        });
    }
});