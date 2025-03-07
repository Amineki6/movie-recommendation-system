// Function to handle login
async function loginUser(event) {
    event.preventDefault(); // Prevent the default form submission

    // Get the form values
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    try {
        // Send a POST request to the authenticate endpoint
        const response = await fetch('http://localhost:3300/authenticate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email: username, // Match the Flask API field 'email'
                password: password
            }),
        });

        // Parse the response from the server
        const data = await response.json();

        // Check if authentication was successful
        if (data.authenticated) {
            sessionStorage.setItem('userId', data.user_id);
            //sessionStorage.setItem('userId', 22);
            window.location.href = '../main/index.html';
        } else {
            alert('Invalid username or password. Please try again.');
        }
    } catch (error) {
        console.error('Error logging in:', error);
        alert('An error occurred. Please try again later.');
    }
}

// Function to redirect to the register page
function redirectToRegister() {
    window.location.href = '../auth/register.html';
}