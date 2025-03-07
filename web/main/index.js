// Base URL for poster images
const basePosterUrl = 'https://image.tmdb.org/t/p/w342';

// Default values for movies
const defaultPosterUrl = 'static/images/Question_Mark.svg';
const defaultTitle = 'Unknown Title';
const defaultRating = 'N/A';
const defaultDirector = 'Unknown';
sessionStorage.setItem('newMovie', 'false');

// Initialize variables
let sourceFilter = 'both'; // Default mode
let allMovies = []; // To store all fetched movies and their source codes

function reformatTitle(title) {
    // Check if the title matches the pattern "Title, The (Year)"
    const match = title.match(/^(.*),\s(The|A|An)\s(\(\d{4}\))$/);
    if (match) {
        // Reformat to "The Title (Year)"
        return `${match[2]} ${match[1]} ${match[3]}`;
    }
    return title; // Return the original title if no match
}

function renderMovies() {
    const container = document.getElementById('movies-container');
    container.innerHTML = ''; // Clear current display

    // Retrieve pending feedback from localStorage
    const ratedMovieIds = JSON.parse(sessionStorage.getItem('ratedMovies')) || [];
    
    allMovies.forEach(({ movie, source }) => {
        // Check if the movie matches the current source filter and is not in the pending feedback
        if ((sourceFilter === 'both' || sourceFilter === source) && !ratedMovieIds.includes(String(movie.movie_id))) {
            // Reformat the title if needed
            const formattedTitle = reformatTitle(movie.title || defaultTitle);

            const movieItem = `
                <a href="../movie/movie.html?movie_id=${movie.movie_id}&source=${source}" class="movie-item">
                    <img src="${movie.poster_url ? basePosterUrl + movie.poster_url : defaultPosterUrl}" alt="${formattedTitle}">
                    <div class="movie-item-content">
                        <div class="movie-item-title">${formattedTitle}</div>
                        <div class="movie-infos">
                            <div class="movie-info">
                                <i class="bx bxs-star"></i>
                                <span>${movie.rating || defaultRating}</span>
                            </div>
                            <div class="movie-info">
                                <span>HD</span>
                            </div>
                            <div class="movie-info">
                                <span>By ${movie.director || defaultDirector}</span>
                            </div>
                        </div>
                    </div>
                </a>`;
            container.innerHTML += movieItem;
        }
    });
}



const userId = sessionStorage.getItem('userId');


async function loadRecommendations() {
    if (!userId) {
        window.location.href = '../auth/login.html';
        return;
    }

    const sourceToggle = document.getElementById('source-toggle');
    sourceToggle.style.display = 'none';
    
    const requestBody = { user_id: parseInt(userId, 10) };
    
    try {
        const response = await fetch('http://localhost/fetch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);

        const data = await response.json();
        const recommendations = data.recommendations;
        console.log(data)
        

        const movieIds = recommendations.map(rec => rec[0]);
        const movieIdsWithSource = recommendations.map(rec => ({ id: rec[0], source: rec[1] }));

        // Ensure fetchMovieDetails completes before resolving
        await fetchMovieDetails(movieIds, movieIdsWithSource);
    } catch (error) {
        console.error('Error fetching recommendations:', error);
        throw error;  // Propagate the error to stop further execution
    }
    
}



async function fetchMovieDetails(movieIds, movieIdsWithSource) {
    return fetch(`http://localhost:3030/api/movies?movie_id=${movieIds.join('&movie_id=')}&include_all=True`)
        .then(response => response.ok ? response.json() : Promise.reject(response))
        .then(movies => {
            
            const sourceLookup = Object.fromEntries(movieIdsWithSource.map(item => [item.id, item.source]));
            allMovies = movies.map(movie => ({
                movie,
                source: sourceLookup[movie.movie_id] || 'unknown'
            }));

            sessionStorage.setItem('allMovies', JSON.stringify(allMovies));
            configureSourceToggle(allMovies);
            renderMovies();
        })
        .catch(error => console.error('Error fetching movie details:', error));
}

function configureSourceToggle(movies) {
    const sourceToggle = document.getElementById('source-toggle');
    const sources = new Set(movies.map(movie => movie.source));
    
    sourceToggle.innerHTML = '';
    
    if (sources.size === 1) {
        if (sources.has('03') || sources.has('03:c')) {
            sourceToggle.innerHTML = '<span id="option-03" class="toggle-option active">Popular</span>';
        } else if (sources.has('02')) {
            sourceToggle.innerHTML = '<span id="option-02" class="toggle-option active">Peers\' Picks</span>';
        } else if (sources.has('01')) {
            sourceToggle.innerHTML = '<span id="option-01" class="toggle-option active">For You</span>';
        }
    } else {
        sourceToggle.innerHTML = `
            <span id="option-01" class="toggle-option">For You</span>
            <span id="option-auto" class="toggle-option active">All</span>
            <span id="option-02" class="toggle-option">Peers' Picks</span>
        `;
    }
    
    sourceToggle.style.display = 'flex';
    
    
    document.getElementById('guide').style.display = 'block';

    if (!sources.has('03:c')) {
        document.getElementById('personalize').style.display = 'block';
        document.getElementById('profile').style.display = 'block';
    } else {
        document.getElementById('personalize').style.display = 'none';
        document.getElementById('profile').style.display = 'none';
    }
}




// Add toggle functionality
const toggle = document.getElementById('source-toggle');
toggle.addEventListener('click', (e) => {
    if (e.target.id === 'option-01') {
        sourceFilter = '01';
    } else if (e.target.id === 'option-02') {
        sourceFilter = '02';
    } else if (e.target.id === 'option-auto') {
        sourceFilter = 'both';
    }
    // Update UI to reflect active toggle state
    document.querySelectorAll('.toggle-option').forEach(option => option.classList.remove('active'));
    e.target.classList.add('active');

    // Re-render movies based on the selected filter
    renderMovies();
});



function renderSkeletonLoaders() {
    const container = document.getElementById('movies-container');
    container.innerHTML = ''; // Clear current display

    // Add skeleton loaders
    for (let i = 0; i < 30; i++) { // Adjust the number of placeholders as needed
        const skeletonItem = `
            <div class="skeleton-movie-item">
                <div class="skeleton skeleton-movie-image"></div>
                
            </div>`;
        container.innerHTML += skeletonItem;
    }
}

document.addEventListener("DOMContentLoaded", function () {
    // Select the logout link element
    const logoutLink = document.getElementById("user-name");

    // Add a click event listener to the logout link
    logoutLink.addEventListener("click", function (event) {
        // Clear sessionStorage
        sessionStorage.clear();
    });
});

sessionStorage.setItem('changedDirector', false);
sessionStorage.setItem('changedModel', false);


async function fetchRecentRelease() {
    try {
        const response = await fetch('http://localhost:3030/api/recent_release');
        const data = await response.json();

        if (data.image_path && data.title && data.overview && data.director && data.vote_average) {
            const basePath = "https://image.tmdb.org/t/p/original";
            const posterUrl = basePath + data.image_path;

            // Remove year in parentheses from title
            const cleanedTitle = data.title.replace(/\(\d{4}\)$/, "").trim();

            // Create the movie section dynamically
            const movieSection = document.createElement("div");
            movieSection.classList.add("section");
            movieSection.innerHTML = `
                <div class="hero-slide-item">
                    <img src="${posterUrl}" alt="${cleanedTitle}">
                    <div class="overlay"></div>
                    <div class="hero-slide-item-content">
                        <div class="item-content-wraper">
                            <div class="item-content-title main-color">NEW</div>
                            <div class="item-content-title">${cleanedTitle}</div>
                            <div class="movie-infos">
                                <div class="movie-info">
                                    <i class="bx bxs-star"></i>
                                    <span>${data.vote_average}</span>
                                </div>
                                <div class="movie-info">
                                    <span>By ${data.director}</span>
                                </div>
                            </div>
                            <div class="item-content-description">
                                ${data.overview}
                            </div>
                            <div class="item-action">
                                <a href="../movie/movie.html?movie_id=${data.movie_id}&source=01" class="btn btn-hover" onclick="sessionStorage.setItem('newMovie', 'true')">
                                    <i class="bx bxs-right-arrow"></i>
                                    <span>Watch now</span>
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            // Append the newly created movie section to the document
            const container = document.querySelector(".release-container"); // Change this selector if needed
            if (container) {
                container.innerHTML = ""; // Clear existing content
                container.appendChild(movieSection); // Add the new content
            } else {
                console.error("Error: Container not found in DOM");
            }
        }
    } catch (error) {
        console.error("Error fetching recent release:", error);
    }
}


async function sendRecommendationRequest(userId) {
    const url = 'http://localhost:8080/recommend'; 

    // Retrieve values from sessionStorage, set to null if not found
    const favoriteDirector = sessionStorage.getItem('favoriteDirector') || null;
    const favoriteModel = sessionStorage.getItem('favoriteModel') || null;
    
    // Prepare the request body with the additional values
    const requestBody = {
        user_id: userId,
        director: favoriteDirector,
        model: favoriteModel
    };

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        // Process response as text (since API returns plain text)
        const textData = await response.text();
        
        return textData;

    } catch (error) {
        console.error('Error sending request:', error.message);
        throw error;
    }
}

window.onload = async function () {
    try {
        renderSkeletonLoaders();
        await loadRecommendations();  // Ensures recommendations & movie details are fully loaded
        await fetchRecentRelease();
        await sendRecommendationRequest(userId);
        
    } catch (error) {
        console.error('Request failed:', error);
    }
};


document.getElementById("adminLink").addEventListener("click", function() {
    sessionStorage.removeItem('userId'); 
});