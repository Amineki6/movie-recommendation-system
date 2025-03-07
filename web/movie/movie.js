const userId = sessionStorage.getItem('userId');
const basePosterUrl = 'https://image.tmdb.org/t/p/original';
const defaultPosterUrl = 'static/images/Question_Mark.svg';
const defaultTitle = 'Unknown'

const params = new URLSearchParams(window.location.search);
const movieId = params.get('movie_id');

const allMovies = JSON.parse(sessionStorage.getItem('allMovies') || '[]');
const newMovie = sessionStorage.getItem('newMovie');

const findselectedMovie = allMovies.find(item => String(item.movie.movie_id) === movieId);
let selectedMovie = null;

async function fetchAndRenderMovie() {
    const findselectedMovie = allMovies.find(item => String(item.movie.movie_id) === movieId);
    if (!findselectedMovie && newMovie !== 'true') {
        selectedMovie = await callMovie(); // Wait for the fetch to complete
        if (selectedMovie) {
            renderSelectedMovie(); // Pass the movie object
        } else {
            console.error("Movie not found.");
        }
    } else {
        if(newMovie !== 'true'){
            selectedMovie = findselectedMovie.movie;
        } else {
            selectedMovie = await callMovie();
        }
        
        renderSelectedMovie(true); // Pass the movie object
    }
}

fetchAndRenderMovie();

async function callMovie() {
    if (!movieId) {
        console.error("Movie ID is missing.");
        return null;
    }

    try {
        const response = await fetch(`http://localhost:3030/api/movies?movie_id=${movieId}&include_all=True`);
        
        if (!response.ok) {
            throw new Error(`Failed to fetch movie data: ${response.status} ${response.statusText}`);
        }

        const movies = await response.json();

        if (!movies || movies.length === 0) {
            throw new Error("No movie data found.");
        }

        // Assume the API returns an array; get the first movie
        const movie = movies[0];

        return movie; // Return the movie object

    } catch (error) {
        console.error("Error fetching movie:", error);
        alert("Failed to fetch movie data. Please try again later.");
        return null;
    }
}




function reformatTitle(title) {
    // Check if the title matches the pattern "Title, The (Year)"
    const match = title.match(/^(.*),\s(The|A|An)\s(\(\d{4}\))$/);
    if (match) {
        // Reformat to "The Title (Year)"
        return `${match[2]} ${match[1]} ${match[3]}`;
    }
    return title; // Return the original title if no match
}

// Helper function to safely get a value, defaulting if not found
function safeGet(value, defaultValue) {
    return value !== undefined && value !== null ? value : defaultValue;
}

// Builds the star rating HTML based on a numeric rating
function buildStarRatingHTML(rating) {
    const fullStars = Math.floor(rating);
    const halfStar = rating % 1 !== 0;
    const emptyStars = 5 - fullStars - (halfStar ? 1 : 0);

    const fullStarsHTML = '<i class="bx bxs-star"></i>'.repeat(fullStars);
    const halfStarHTML = halfStar ? '<i class="bx bxs-star-half"></i>' : '';
    const emptyStarsHTML = '<i class="bx bx-star"></i>'.repeat(emptyStars);

    return fullStarsHTML + halfStarHTML + emptyStarsHTML;
}

// Builds the HTML for the main movie detail section
function buildMovieDetailHTML(movie) {
    const rating = safeGet(movie.rating, 0);
    const starsHTML = buildStarRatingHTML(rating);
    const formattedTitle = reformatTitle(safeGet(movie.title, defaultTitle));

    return `
        <div class="movie-detail">
            <img 
                class="movie-poster" 
                src="${movie.poster_url ? basePosterUrl + movie.poster_url : defaultPosterUrl}" 
                alt="${movie.title}"
            >
            <div class="movie-info">
                <div class="movie-item-title">${formattedTitle}</div>
                <p><strong>Overview:</strong> ${safeGet(movie.overview, 'No description available.')}</p>
                <p><strong>Directed By:</strong> ${safeGet(movie.director, 'Unknown')}</p>
                <p><strong>Genres:</strong> ${safeGet(movie.genres, 'Unknown')}</p>
                <p><strong>Average Rating:</strong> ${starsHTML}</p>
            </div>
        </div>
    `;
}



// Sets up the feedback section, including event listeners
function setupFeedbackSection(ratingContainer) {
    const ratingSectionHTML = `
        <h3>Select Your Rating:</h3>
        <div id="user-rating-stars" class="rating-stars">
            ${'<i class="bx bx-star big-star" data-value="1"></i>'}
            ${'<i class="bx bx-star big-star" data-value="2"></i>'}
            ${'<i class="bx bx-star big-star" data-value="3"></i>'}
            ${'<i class="bx bx-star big-star" data-value="4"></i>'}
            ${'<i class="bx bx-star big-star" data-value="5"></i>'}
        </div>
        <button id="submit-rating" class="submit-btn">Submit</button>
    `;
    ratingContainer.innerHTML = ratingSectionHTML;

    const stars = document.querySelectorAll('.big-star');
    let selectedRating = 0;

    stars.forEach((star) => {
        // Hover effect
        star.addEventListener('mouseover', () => {
            const value = parseInt(star.getAttribute('data-value'), 10);
            highlightStars(stars, value);
        });

        // Remove hover effect
        star.addEventListener('mouseout', () => {
            highlightStars(stars, selectedRating); 
        });

        // Click to select rating
        star.addEventListener('click', () => {
            selectedRating = parseInt(star.getAttribute('data-value'), 10);
            highlightStars(stars, selectedRating);
        });
    });

    // Set up the submit button
    const submitButton = document.getElementById('submit-rating');
    submitButton.addEventListener('click', async () => {
        if (selectedRating > 0) {
            // Change button text to spinner
            submitButton.innerHTML = '<div class="spinner"></div>';

            // Call submitRating function
            await submitRating(selectedRating, submitButton);

            // Optionally, change the button text back to 'Submit' after the rating is submitted
            submitButton.innerHTML = 'Submit';
        }
    });
}

// Highlights the stars up to the given rating
function highlightStars(stars, rating) {
    stars.forEach((star) => {
        const value = parseInt(star.getAttribute('data-value'), 10);
        star.classList.toggle('bxs-star', value <= rating);
        star.classList.toggle('bx-star', value > rating);
    });
}


// Main function to render the selected movie
function renderSelectedMovie(showFeedback = false) {
    const container = document.getElementById('movie-container');
    const ratingContainer = document.getElementById('rating-container');

    if (!selectedMovie) {
        container.innerHTML = '<p>Movie not found.</p>';
        return;
    }

    // Render the main movie details
    container.innerHTML = buildMovieDetailHTML(selectedMovie);

    // Toggle the title element visibility
    const titleElement = document.querySelector('.title');
    if (titleElement) {
        titleElement.style.display = showFeedback ? 'block' : 'none';
    }
    
    // Conditionally render the feedback section
    if (showFeedback) {
        setupFeedbackSection(ratingContainer);
    } else {
        ratingContainer.innerHTML = '';
    }
}


// Toggle between Kafka or direct feedback endpoints
const USE_KAFKA = true;
const API_URL = USE_KAFKA
  ? 'http://localhost:8080/recommend/feedback'
  : 'http://localhost:6090/feedback';

/**
 * Returns the user and movie IDs based on session storage and URL params.
 * @returns {{ user_id: string, movie_id: string }}
 */
function getIds() {
  const userId = sessionStorage.getItem('userId');
  const urlParams = new URLSearchParams(window.location.search);
  const movieId = urlParams.get('movie_id');
  let source = urlParams.get('source');

  // Modify source if it is '03:c'
  if (source === '03:c') {
    source = '03';
  }

  return { user_id: userId, movie_id: movieId, source: source };
}


/**
 * Sends feedback to the server via a POST request.
 * @param {Object} feedback - The feedback payload (user_id, movie_id, rating).
 * @returns {Promise<boolean>} - True if sent successfully, false otherwise.
 */
async function sendFeedback(feedback) {
  try {
    const response = await fetch(API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(feedback),
    });

    if (response.ok) {
      console.log('Feedback sent successfully:', feedback);
      return true;
    } else {
      console.error('Error:', response.status);
      return false;
    }
  } catch (error) {
    console.error('Request failed:', error);
    return false;
  }
}

/**
 * Handles actions needed when feedback is successfully sent:
 *  - Updates the UI
 *  - Removes certain session storage items
 *  - Potentially sets 'changedDirector'
 * @param {HTMLElement} submitButton - The button used to submit the rating.
 */
function handleSuccessfulFeedback(submitButton) {
    const feedbackText = document.createElement('span');
    feedbackText.textContent = 'Feedback Sent!';
    feedbackText.style.fontWeight = 'bold';

    // Remove "allMovies" from session storage
    sessionStorage.removeItem('allMovies');
    
    // Replace the button with feedback text
    submitButton.replaceWith(feedbackText);

    // If there's a favoriteDirector, mark that the director changed
    if (sessionStorage.getItem('favoriteDirector')) {
        sessionStorage.setItem('changedDirector', 'true');
    }
}

/**
 * Handles actions needed when feedback fails:
 *  - Stores feedback in localStorage (pending)
 *  - Initiates retry logic
 * @param {Object} payload - The feedback payload.
 */
function handleFailedFeedback(payload, submitButton) {

    const feedbackText = document.createElement('span');
    feedbackText.textContent = 'Feedback Saved!';
    feedbackText.style.fontWeight = 'bold';

    // Remove "allMovies" from session storage
    sessionStorage.removeItem('allMovies');

    // Replace the button with feedback text
    submitButton.replaceWith(feedbackText);

    // If there's a favoriteDirector, mark that the director changed
    if (sessionStorage.getItem('favoriteDirector')) {
        sessionStorage.setItem('changedDirector', 'true');
    }

    const storedFeedback = JSON.parse(localStorage.getItem('pendingFeedback')) || [];
    storedFeedback.push(payload);
    localStorage.setItem('pendingFeedback', JSON.stringify(storedFeedback));
    console.log('Feedback stored:', localStorage.getItem('pendingFeedback'));

    console.log('Feedback stored locally. Will retry sending.');

    retryPendingFeedbacks();
}

/**
 * Tries to resend any pending feedback from localStorage at regular intervals.
 * If no pending feedback remains, the interval is cleared.
 */
function retryPendingFeedbacks() {
  // Avoid creating multiple intervals
  if (window.feedbackRetryInterval) return;

  window.feedbackRetryInterval = setInterval(async () => {
    let pending = JSON.parse(localStorage.getItem('pendingFeedback')) || [];
    if (pending.length === 0) {
      clearInterval(window.feedbackRetryInterval);
      window.feedbackRetryInterval = null;
      return;
    }

    // Attempt to send each feedback; remove from pending if successful
    for (let i = 0; i < pending.length; i++) {
      if (await sendFeedback(pending[i])) {
        pending.splice(i, 1);
        i--; // Adjust index after removal
      }
    }

    localStorage.setItem('pendingFeedback', JSON.stringify(pending));
  }, 10000); // Retry every 10 seconds
}

/**
 * Submits a rating for a movie.
 * @param {number} rating - The rating the user selected.
 * @param {HTMLElement} submitButton - The button element that triggered the rating.
 */
async function submitRating(rating, submitButton) {
  const { user_id, movie_id, source } = getIds();

  const payload = {
    user_id,
    movie_id,
    rating,
    source
  };

  if (await sendFeedback(payload)) {
    addToSessionStorage(movie_id);
    handleSuccessfulFeedback(submitButton);
  } else {
    addToSessionStorage(movie_id);
    handleFailedFeedback(payload, submitButton);
  }
}

// Ensure pending feedback retries start when the page loads
document.addEventListener('DOMContentLoaded', () => {
  retryPendingFeedbacks();
});

function addToSessionStorage(movie_id) {
    // Get existing movie IDs from session storage or initialize an empty array
    const movieIds = JSON.parse(sessionStorage.getItem('ratedMovies')) || [];
  
    // Only add the movie_id if it's not already in the array
    if (!movieIds.includes(movie_id)) {
      movieIds.push(movie_id);
      sessionStorage.setItem('ratedMovies', JSON.stringify(movieIds));
    }
  }

document.addEventListener("DOMContentLoaded", function () {
    if (!sessionStorage.getItem('userId')) {
      window.location.replace('../auth/login.html');
    }
  });
  