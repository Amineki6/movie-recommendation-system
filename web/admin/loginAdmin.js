// Function to handle login
async function loginAdmin(event) {
    event.preventDefault(); // Prevent the default form submission

    // Get the form values
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    console.log(username)

    try {
        // Send a POST request to the authenticate endpoint
        const response = await fetch('http://localhost:3300/authenticate/admin', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: username,
                password: password
            }),
        });

        // Parse the response from the server
        const data = await response.json();

        // Check if authentication was successful
        if (data.authenticated) {
            window.location.href = '../admin/adminPage.html';
        } else {
            alert('Invalid username or password. Please try again.');
        }
    } catch (error) {
        console.error('Error logging in:', error);
        alert('An error occurred. Please try again later.');
    }
}


  