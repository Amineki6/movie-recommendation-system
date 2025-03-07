const BASE_URL = 'http://127.0.0.1:';

function fetchUserCounts() {
    fetch('http://127.0.0.1:3040/users/count')
        .then(response => response.json())
        .then(data => {
            // Target only the <p> elements inside the cards
            document.querySelector('.card:nth-child(1) p').textContent = data.total_users;
        })
        .catch(error => console.error('Error fetching data:', error));
}

// Call the function when the page loads
document.addEventListener("DOMContentLoaded", fetchUserCounts);


function fetchMovieCounts() {
    fetch('http://127.0.0.1:3040/movies/count')
        .then(response => response.json())
        .then(data => {
            document.querySelector('.card:nth-child(2) p').textContent = data.total_movies;
        })
        .catch(error => console.error('Error fetching data:', error));
}

// Call the function when the page loads
document.addEventListener("DOMContentLoaded", fetchMovieCounts);

$(document).ready(function () {
    function setupSearchBar(inputSelector, suggestionSelector, saveButtonSelector, detailsContainerSelector, first) {
        const $input = $(inputSelector);
        const $suggestions = $(suggestionSelector);
        let selectedUser = null;

        $suggestions.hide(); // Hide suggestions initially
        if (first){
            $input.on('input', function () {
                const searchTerm = $(this).val();
    
                if (searchTerm.length > 2) {
                    $.ajax({
                        url: 'http://localhost:8081/search_user.php',
                        method: 'GET',
                        data: { term: searchTerm },
                        success: function (response) {
                            
                            const users = JSON.parse(response);
                            console.log(users)
                            if (users.length > 0) {
                                const suggestionsHTML = users.map(user => `
                                    <div class="suggestion-item" data-user='${JSON.stringify(user)}'>
                                        ${user.firstname} ${user.lastname}
                                    </div>
                                `).join('');
    
                                $suggestions.html(suggestionsHTML).show();
                            } else {
                                $suggestions.hide();
                            }
                        },
                        error: function () {
                            console.error('Error fetching user suggestions');
                        }
                    });
                } else {
                    $suggestions.hide();
                }
            });
    
            $(document).on('click', `${suggestionSelector} .suggestion-item`, function () {
                selectedUser = $(this).data('user');
                $input.val(`${selectedUser.firstname} ${selectedUser.lastname}`);
                $suggestions.hide();
            });
    
            $(document).on('click', function (event) {
                if (!$(event.target).closest('.input-wrapper').length) {
                    $suggestions.hide();
                }
            });
    
            $(saveButtonSelector).on('click', async function () {
                if (!selectedUser) {
                    alert('Please select a user before saving.');
                    return;
                }
                try {
                    const response = await fetch(`${BASE_URL}3040/user/history`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ user_id: selectedUser.user_id })
                    });
    
                    if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
    
                    const data = await response.json();
                    const numSeenMovies = data.movies_seen || 0;
                    const userType = selectedUser.user_index === null ? "Cold" : "Warm";
                    $(detailsContainerSelector).html(`
                        <table class="user-table">
                            <tr>
                                <th>User ID</th>
                                <th>First Name</th>
                                <th>Last Name</th>
                                <th>Email</th>
                                <th>User Type</th>
                                <th>Movies Watched</th>
                            </tr>
                            <tr>
                                <td>${selectedUser.user_id}</td>
                                <td>${selectedUser.firstname}</td>
                                <td>${selectedUser.lastname}</td>
                                <td>${selectedUser.email}</td>
                                <td>${userType}</td>
                                <td>${numSeenMovies}</td>
                            </tr>
                        </table>

                        <div class="user-actions">
                            <button class="user-profile-btn" data-user-id="${selectedUser.user_id}">User Profile</button>
                            <button class="delete-user-btn delete-btn" data-user-id="${selectedUser.user_id}">Delete User</button>
                            <button class="close-details-btn" data-tooltip="Close Details">X</button>
                        </div>
                    `);

                    $(document).on('click', '.close-details-btn', function () {
                        $(detailsContainerSelector).html('');
                    });

                    $('.user-profile-btn').on('click', function () {
                        const user_id = $(this).data('user-id');
                        window.location.href = `http://127.0.0.1:5500/web/user/profile.html?userId=${user_id}`;
                    });
    
                    $('.delete-user-btn').on('click', function () {
                        const user_id = $(this).data('user-id');
                        if (confirm(`Are you sure you want to delete this user?`)) {
                            deleteUser(user_id);
                        }
                    });
                } catch (error) {
                    console.error('Error fetching user history:', error);
                    alert('Failed to fetch user history.');
                }
            });
        } else {
            $input.on('input', function () {
                const searchTerm = $(this).val();
    
                if (searchTerm.length > 2) {
                    $.ajax({
                        url: 'http://localhost:8081/search_movie.php',
                        method: 'GET',
                        data: { term: searchTerm },
                        success: function (response) {
                            const movies = JSON.parse(response);
                            if (movies.length > 0) {
                                const suggestionsHTML = movies.map(movie => `
                                    <div class="suggestion-item" data-movie='${JSON.stringify(movie).replace(/'/g, "&#39;")}'>
                                        ${reformatTitle(movie.title)}
                                    </div>
                                `).join('');
                                
    
                                $suggestions.html(suggestionsHTML).show();
                            } else {
                                $suggestions.hide();
                            }
                        },
                        error: function () {
                            console.error('Error fetching movie suggestions');
                        }
                    });
                } else {
                    $suggestions.hide();
                }
            });
            let selectedMovie;

            $(document).on('click', `${suggestionSelector} .suggestion-item`, function () {
                selectedMovie = $(this).data('movie');
                console.log(selectedMovie)
                $input.val(`${reformatTitle(selectedMovie.title)}`);
                $suggestions.hide();
            });
    
            $(document).on('click', function (event) {
                if (!$(event.target).closest('.input-wrapper').length) {
                    $suggestions.hide();
                }
            });

            $(saveButtonSelector).on('click', async function () {
                if (!selectedMovie) {
                    alert('Please select a movie before saving.');
                    return;
                }
                document.getElementById('user-details-2').style.display = 'flex';
                $(detailsContainerSelector).html(`
                    <table class="movie-table">
                        <tr>
                            <th>Movie ID</th>
                            <th>Title</th>
                            <th>Director</th>
                            <th>Genres</th>
                        </tr>
                        <tr>
                            <td>${selectedMovie.movie_id}</td>
                            <td>${reformatTitle(selectedMovie.title)}</td>
                            <td>${selectedMovie.director}</td>
                            <td>${selectedMovie.genres}</td>
                        </tr>
                    </table>
                    <div class="user-actions">
                        <button class="movie-poster-btn" data-movie-id="${selectedMovie.movie_id}">See Poster</button>
                        <button class="delete-movie-btn delete-btn" data-movie-id="${selectedMovie.movie_id}">Delete Movie</button>
                        <button class="close-details-btn" data-tooltip="Close Details">X</button>
                    </div>
                `);

            });

            $(document).on('click', '.close-details-btn', function () {
                $(detailsContainerSelector).html('');
                document.getElementById('add-movie-wrapper').style.display = 'block';
            });

            $(document).on('click', '.movie-edit-btn', function () {
                window.location.href = `#`;
            });

            $(document).on('click', '.delete-movie-btn', function () {
                const movie_id = $(this).data('movie-id');
                if (confirm(`Are you sure you want to delete this movie?`)) {
                    deleteMovie(movie_id);
                }
            });

            $(document).on('click', '.movie-poster-btn', function () {
                const BASE_POSTER_PATH = "https://image.tmdb.org/t/p/original";
            
                if (!selectedMovie || !selectedMovie.poster_path) {
                    alert("No poster available for this movie.");
                    return;
                }
            
                const posterURL = `${BASE_POSTER_PATH}${selectedMovie.poster_path}`;
                const $button = $(this);
                const $posterContainer = $('.movie-poster-container');
            
                if ($posterContainer.length === 0) {
                    // If poster is not displayed, append it and change button text
                    $(detailsContainerSelector).append(`
                        <div class="movie-poster-container" style="margin-top: 50px;">
                            <img src="${posterURL}" alt="${selectedMovie.title} Poster" class="movie-poster">
                        </div>
                    `);
                    $button.text('Hide Poster');
                } else {
                    // Toggle visibility and change button text accordingly
                    if ($posterContainer.is(':visible')) {
                        $posterContainer.hide();
                        $button.text('Show Poster');
                    } else {
                        $posterContainer.show();
                        $button.text('Hide Poster');
                    }
                }
            });

        }
        
        
    }

    // Setup for first search bar
    setupSearchBar('#director-input-1', '#suggestions-1', '#save-button-1', '#user-details-1', true);

    // Setup for second search bar
    setupSearchBar('#director-input-2', '#suggestions-2', '#save-button-2', '#user-details-2', false);
});


function deleteUser(user_id) {
    fetch(`http://localhost:3303/delete_user/${user_id}`, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('User deleted successfully.');
            // Optionally refresh the user list or update the UI
            location.reload();
        } else {
            alert('Failed to delete user.');
        }
    })
    .catch(error => {
        console.error('Error deleting user:', error);
        alert('An error occurred while deleting the user.');
    });
};


function deleteMovie(movie_id) {
    fetch(`http://localhost:3303/delete_movie/${movie_id}`, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Movie deleted successfully.');
            // Optionally refresh the movie list or update the UI
            location.reload();
        } else {
            alert('Failed to delete movie.');
        }
    })
    .catch(error => {
        console.error('Error deleting movie:', error);
        alert('An error occurred while deleting the movie.');
    });
};




function reformatTitle(title) {
    // Check if the title matches the pattern "Title, The (Year)"
    const match = title.match(/^(.*),\s(The|A|An)\s(\(\d{4}\))$/);
    if (match) {
        // Reformat to "The Title (Year)"
        return `${match[2]} ${match[1]} ${match[3]}`;
    }
    return title; // Return the original title if no match
}

function switchTab(tabId) {
    // Remove active class from all tab contents
    document.querySelectorAll('.tab-content-movie').forEach(tab => {
        tab.classList.remove('active');
    });

    // Remove active class from all tabs
    document.querySelectorAll('.tab-second').forEach(tab => {
        tab.classList.remove('active');
    });

    // Add active class to the selected tab content
    document.getElementById(tabId).classList.add('active');

    // Add active class to the correct tab button
    if (tabId === 'input-tab') {
        document.querySelector('.tabs .tab-second:nth-child(1)').classList.add('active');
    } else {
        document.querySelector('.tabs .tab-second:nth-child(2)').classList.add('active');
    }
}

function switchTabOverview(tabId) {
    // Remove active class from all tab contents
    document.querySelectorAll('.tab-content-overview').forEach(tab => {
        tab.classList.remove('active');
    });

    // Remove active class from all tabs
    document.querySelectorAll('.tab-first').forEach(tab => {
        tab.classList.remove('active');
    });

    // Add active class to the selected tab content
    document.getElementById(tabId).classList.add('active');

    // Add active class to the correct tab button
    if (tabId === 'overview-tab') {
        document.querySelector('.tabs .tab-first:nth-child(1)').classList.add('active');
    } else {
        document.querySelector('.tabs .tab-first:nth-child(2)').classList.add('active');
    }
}




function nextStep(step) {
    document.querySelectorAll('.form-step').forEach(stepDiv => stepDiv.style.display = 'none');
    document.getElementById('step-' + step).style.display = 'flex';
}

function prevStep(step) {
    document.querySelectorAll('.form-step').forEach(stepDiv => stepDiv.style.display = 'none');
    document.getElementById('step-' + step).style.display = 'flex';
}

document.getElementById("movie-form").addEventListener("submit", async function(event) {
    event.preventDefault(); // Prevent default form submission
    
    // Collect form data
    const formData = new FormData(event.target);
    const jsonData = Object.fromEntries(formData.entries()); // Convert to JSON object
    try {
        const response = await fetch("http://localhost:3303/add_movie", { // Replace with your API endpoint
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(jsonData)
        });

        if (!response.ok) {
            throw new Error(`Error: ${response.status} ${response.statusText}`);
        }

        const result = await response.json();
        alert("Movie submitted successfully!");

    } catch (error) {
        console.error("Submission failed", error);
        alert("Failed to submit movie. Check console for details.");
    }
});

function trainModel() {
    // Get the number of nodes from input
    const numNodes = parseInt(document.getElementById("num-nodes").value, 10);

    // Hide the button
    document.getElementById("train-button").style.display = "none";
    
    // Show training status with spinner
    const trainStatus = document.getElementById("train-status");
    trainStatus.style.display = "block";
    trainStatus.innerHTML = `<span class="spinner"></span> Model training...`;

    // API request body
    const requestBody = {
        train_cb: false,
        train_cbf: true,
        online: true,
        num_nodes: numNodes
    };

    // Send API request
    fetch('http://localhost:7070/train', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
    })
    .then(response => response.json())
    .then(data => {
        trainStatus.innerHTML = "✅ Model trained and rolled out successfully!";
    })
    .catch(error => {
        trainStatus.innerHTML = "❌ Error during model training.";
        console.error("Error:", error);
    });
}


  