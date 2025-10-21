// API Configuration
const API_BASE_URL = 'http://127.0.0.1:5000';

// Global State
let confirmToken = '';
let userEmail = '';
let resendTimer = null;
let resendCountdown = 60;

// DOM Elements
const step1 = document.getElementById('step1');
const step2 = document.getElementById('step2');
const registerForm = document.getElementById('registerForm');
const verificationForm = document.getElementById('verificationForm');
const registerBtn = document.getElementById('registerBtn');
const verifyBtn = document.getElementById('verifyBtn');
const resendBtn = document.getElementById('resendBtn');
const backBtn = document.getElementById('backBtn');
const successMessage = document.getElementById('successMessage');
const loadingOverlay = document.getElementById('loadingOverlay');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Generate unique device ID if not exists
    if (!localStorage.getItem('deviceId')) {
        localStorage.setItem('deviceId', generateDeviceId());
    }

    // Form validation on input
    setupInputValidation();

    // Event listeners
    registerForm.addEventListener('submit', handleRegister);
    verificationForm.addEventListener('submit', handleVerification);
    resendBtn.addEventListener('click', handleResendCode);
    backBtn.addEventListener('click', handleBackToRegister);

    // Auto-format verification code input
    const codeInput = document.getElementById('verificationCode');
    codeInput.addEventListener('input', (e) => {
        e.target.value = e.target.value.replace(/\D/g, '').substring(0, 6);
    });
});

// Generate unique device ID
function generateDeviceId() {
    return 'device-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
}

// Setup input validation
function setupInputValidation() {
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    const confirmPasswordInput = document.getElementById('confirmPassword');
    const usernameInput = document.getElementById('username');

    emailInput.addEventListener('blur', () => validateEmail(emailInput.value));
    passwordInput.addEventListener('blur', () => validatePassword(passwordInput.value));
    confirmPasswordInput.addEventListener('blur', () => validateConfirmPassword());
    usernameInput.addEventListener('blur', () => validateUsername(usernameInput.value));
}

// Validation Functions
function validateEmail(email) {
    const emailError = document.getElementById('emailError');
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    
    if (!email) {
        emailError.textContent = 'Email is required';
        return false;
    }
    
    if (!emailRegex.test(email)) {
        emailError.textContent = 'Please enter a valid email address';
        return false;
    }
    
    emailError.textContent = '';
    return true;
}

function validatePassword(password) {
    const passwordError = document.getElementById('passwordError');
    
    if (!password) {
        passwordError.textContent = 'Password is required';
        return false;
    }
    
    if (password.length < 6 || password.length > 20) {
        passwordError.textContent = 'Password must be 6-20 characters long';
        return false;
    }
    
    passwordError.textContent = '';
    return true;
}

function validateConfirmPassword() {
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const confirmPasswordError = document.getElementById('confirmPasswordError');
    
    if (!confirmPassword) {
        confirmPasswordError.textContent = 'Please confirm your password';
        return false;
    }
    
    if (password !== confirmPassword) {
        confirmPasswordError.textContent = 'Passwords do not match';
        return false;
    }
    
    confirmPasswordError.textContent = '';
    return true;
}

function validateUsername(username) {
    const usernameError = document.getElementById('usernameError');
    
    if (!username) {
        usernameError.textContent = 'Username is required';
        return false;
    }
    
    if (username.length < 3) {
        usernameError.textContent = 'Username must be at least 3 characters';
        return false;
    }
    
    usernameError.textContent = '';
    return true;
}

function validateAllFields() {
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const username = document.getElementById('username').value;
    const name = document.getElementById('name').value;
    
    const isEmailValid = validateEmail(email);
    const isPasswordValid = validatePassword(password);
    const isConfirmPasswordValid = validateConfirmPassword();
    const isUsernameValid = validateUsername(username);
    
    if (!name) {
        document.getElementById('nameError').textContent = 'Full name is required';
        return false;
    }
    
    return isEmailValid && isPasswordValid && isConfirmPasswordValid && isUsernameValid;
}

// Handle Registration
async function handleRegister(e) {
    e.preventDefault();
    
    // Clear previous errors
    clearAllErrors();
    
    // Validate all fields
    if (!validateAllFields()) {
        return;
    }
    
    // Get form data
    const formData = {
        email: document.getElementById('email').value.trim(),
        password: document.getElementById('password').value,
        username: document.getElementById('username').value.trim(),
        name: document.getElementById('name').value.trim(),
        language: document.getElementById('language').value,
        timezone: document.getElementById('timezone').value,
        deviceId: localStorage.getItem('deviceId')
    };
    
    // Save email for later use
    userEmail = formData.email;
    
    // Show loading
    setButtonLoading(registerBtn, true);
    
    try {
        const response = await fetch(`${API_BASE_URL}/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Save tokens để user có thể dùng ngay
            const responseData = data.data || data;
            console.log('Registration successful:', responseData);
            localStorage.setItem('access_token', responseData.access_token);
            localStorage.setItem('refresh_token', responseData.refresh_token);
            localStorage.setItem('user', JSON.stringify(responseData.user));
            
            // Save confirm token cho việc verify sau này (nếu muốn verify sau)
            if (responseData.confirm_token) {
                localStorage.setItem('confirmToken', responseData.confirm_token);
                confirmToken = responseData.confirm_token;
            }
            
            // Show success and redirect to dashboard
            const message = data.resultMessage?.en || 'Registration successful! Redirecting to dashboard...';
            showAlert(message, 'success');
            
            // Redirect to dashboard after 1.5 seconds
            setTimeout(() => {
                window.location.href = 'dashboard.html';
            }, 1500);
            
        } else {
            // Handle error
            handleApiError(data);
        }
        
    } catch (error) {
        console.error('Registration error:', error);
        showAlert('An error occurred. Please try again.', 'error');
    } finally {
        setButtonLoading(registerBtn, false);
    }
}

// Handle Verification
async function handleVerification(e) {
    e.preventDefault();
    
    const verificationCode = document.getElementById('verificationCode').value.trim();
    const codeError = document.getElementById('codeError');
    
    // Validate code
    if (!verificationCode || verificationCode.length !== 6) {
        codeError.textContent = 'Please enter a valid 6-digit code';
        return;
    }
    
    codeError.textContent = '';
    
    // Show loading
    setButtonLoading(verifyBtn, true);
    
    try {
        const response = await fetch(`${API_BASE_URL}verify-email`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                confirm_token: confirmToken,
                verification_code: verificationCode
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Save tokens
            localStorage.setItem('access_token', data.access_token);
            localStorage.setItem('refresh_token', data.refresh_token);
            
            // Show success message
            showSuccess();
            
            // Redirect to dashboard after 2 seconds
            setTimeout(() => {
                window.location.href = 'dashboard.html';
            }, 2000);
            
        } else {
            // Handle error
            if (data.resultCode === '00054') {
                codeError.textContent = 'Invalid verification code. Please try again.';
            } else {
                codeError.textContent = data.resultMessage.en || 'Verification failed';
            }
        }
        
    } catch (error) {
        console.error('Verification error:', error);
        codeError.textContent = 'An error occurred. Please try again.';
    } finally {
        setButtonLoading(verifyBtn, false);
    }
}

// Handle Resend Code
async function handleResendCode() {
    // Disable resend button
    resendBtn.disabled = true;
    
    try {
        const response = await fetch(`${API_BASE_URL}/send-verification-code`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                email: userEmail
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            //next step: verify mail
            confirmToken = data.confirm_token;
            
            // Show success message
            showAlert('New verification code sent to your email!', 'success');
            
            // Restart timer
            startResendTimer();
            
        } else {
            showAlert(data.resultMessage.en || 'Failed to resend code', 'error');
            resendBtn.disabled = false;
        }
        
    } catch (error) {
        console.error('Resend error:', error);
        showAlert('An error occurred. Please try again.', 'error');
        resendBtn.disabled = false;
    }
}

// Handle Back to Register
function handleBackToRegister() {
    step2.classList.remove('active');
    step1.classList.add('active');
    
    // Clear verification form
    document.getElementById('verificationCode').value = '';
    document.getElementById('codeError').textContent = '';
    
    // Stop timer
    if (resendTimer) {
        clearInterval(resendTimer);
        resendTimer = null;
    }
}

// Show Verification Step
function showVerificationStep() {
    step1.classList.remove('active');
    step2.classList.add('active');
    
    // Update email display
    document.getElementById('userEmail').textContent = userEmail;
    
    // Focus on verification code input
    setTimeout(() => {
        document.getElementById('verificationCode').focus();
    }, 300);
}

// Start Resend Timer
function startResendTimer() {
    resendCountdown = 60;
    resendBtn.disabled = true;
    
    updateTimerDisplay();
    
    resendTimer = setInterval(() => {
        resendCountdown--;
        
        if (resendCountdown <= 0) {
            clearInterval(resendTimer);
            resendTimer = null;
            resendBtn.disabled = false;
            document.getElementById('resendTimer').textContent = '';
        } else {
            updateTimerDisplay();
        }
    }, 1000);
}

function updateTimerDisplay() {
    const timerText = document.getElementById('resendTimer');
    timerText.textContent = `Resend available in ${resendCountdown}s`;
}

// UI Helper Functions
function setButtonLoading(button, isLoading) {
    const btnText = button.querySelector('.btn-text');
    const spinner = button.querySelector('.spinner');
    
    if (isLoading) {
        btnText.classList.add('hidden');
        spinner.classList.remove('hidden');
        button.disabled = true;
    } else {
        btnText.classList.remove('hidden');
        spinner.classList.add('hidden');
        button.disabled = false;
    }
}

function showSuccess() {
    successMessage.classList.remove('hidden');
}

function showAlert(message, type = 'info') {
    // Remove existing alerts
    const existingAlert = document.querySelector('.alert');
    if (existingAlert) {
        existingAlert.remove();
    }
    
    // Create alert
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;
    
    // Insert at top of active step
    const activeStep = document.querySelector('.step.active');
    activeStep.insertBefore(alert, activeStep.firstChild);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        alert.remove();
    }, 5000);
}

function handleApiError(data) {
    const errorCode = data.resultCode;
    const errorMessage = data.resultMessage?.en || 'An error occurred';
    
    switch (errorCode) {
        case '00032':
            document.getElementById('emailError').textContent = 'This email is already registered';
            break;
        case '00067':
            document.getElementById('usernameError').textContent = 'This username is already taken';
            break;
        case '00066':
            document.getElementById('passwordError').textContent = 'Password must be 6-20 characters';
            break;
        case '00005':
            document.getElementById('emailError').textContent = 'Invalid email format';
            break;
        default:
            showAlert(errorMessage, 'error');
    }
}

function clearAllErrors() {
    const errorElements = document.querySelectorAll('.error-message');
    errorElements.forEach(el => el.textContent = '');
    
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => alert.remove());
}
