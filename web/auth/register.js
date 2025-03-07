// Function to redirect to the login page
function redirectToLogin() {
    window.location.href = '../auth/login.html';
}

document.getElementById('register-btn').addEventListener('click', function (event) {
    event.preventDefault(); // Prevent the form from submitting normally

    // Retrieve form inputs
    const firstName = document.getElementById('firstname').value.trim();
    const lastName = document.getElementById('lastname').value.trim();
    const email = document.getElementById('Email').value.trim();
    const password = document.getElementById('password-1').value.trim();
    const retypePassword = document.getElementById('password-2').value.trim();

    // Check if passwords match
    if (password !== retypePassword) {
        alert('Passwords do not match!');
        return;
    }

    // Prepare payload for API request
    const payload = {
        firstname: firstName,
        lastname: lastName,
        email: email,
        plain_password: password
    };

    // Send data to the API
    fetch('http://localhost:3303/add_user', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                sessionStorage.setItem('userId', data.user_id);
                window.location.href = '../main/index.html';
            } else {
                alert('Error: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An unexpected error occurred. Please try again later.');
        });
});
