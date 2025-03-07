// Base URL of the Flask API
const BASE_URL = 'http://127.0.0.1:';
let sourceFilter = 'both';

const basePosterUrl = 'https://image.tmdb.org/t/p/w342';

// Default values for movies
const defaultPosterUrl = 'static/images/Question_Mark.svg';


// Function to call the user history endpoint
async function fetchUserProfile(userId) {
  try {
    const response = await fetch(`http://localhost:3040/profile`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ user_id: userId }),
    });

      if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const data = await response.json();

      document.getElementById("firstname").textContent = data.firstname || "N/A";
      document.getElementById("lastname").textContent = data.lastname || "N/A";
      document.getElementById("email").textContent = data.email || "N/A";

  } catch (error) {
      console.error('Error fetching user profile:', error.message);
  }
}


// Function to call the user history endpoint
async function fetchUserHistory(userId) {
  try {
    const response = await fetch(`http://localhost:3040/user/history`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ user_id: userId }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }

    const data = await response.json();
    const movieIds = Object.keys(data.history);
    console.log(data)

    if (data.movies_seen === 0) {
    } else {
        fetchAndRenderMovies(movieIds);
    }
  } catch (error) {
    console.error('Error fetching user history:', error.message);
    document.getElementById('history').innerText = `Error: ${error.message}`;
  }
}

// Function to call the user preferences endpoint
async function fetchUserPreferences(userId) {
  renderSkeletonLoaders();
  try {
    const response = await fetch(`http://localhost:3040/user/preferences`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ user_id: userId }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }

    const data = await response.json();
    console.log(data);
    
    // ---- CHART LOGIC ----
    const genresData = data.genres.genres;
    let labels = Object.keys(genresData);
    let genreValues = Object.values(genresData);

    // Combine labels and genre values into a single array
    let combinedData = labels.map((label, index) => ({
      label: label,
      value: genreValues[index],
    }));

    // Sort the combined data in descending order by value
    combinedData.sort((a, b) => b.value - a.value);

    // Separate the sorted data back into labels and values
    labels = combinedData.map(item => item.label);
    genreValues = combinedData.map(item => (Math.abs(item.value) < 1e-10 ? 0 : item.value));

    // Create a bar chart using Chart.js
    const ctx = document.getElementById('genreChart').getContext('2d');
    const chartData = {
      labels: labels,
      datasets: [
        {
          label: 'Genre Ratings',
          data: genreValues,
          backgroundColor: 'rgba(54, 162, 235, 0.2)',
          borderColor: 'rgba(54, 162, 235, 1)',
          borderWidth: 1,
        },
      ],
    };

    const chartConfig = {
      type: 'bar',
      data: chartData,
      options: {
        responsive: true,
        scales: {
          y: {
            beginAtZero: true,
          },
        },
      },
    };

    new Chart(ctx, chartConfig);
    return data.languages;

  } catch (error) {
    console.error('Error fetching user preferences:', error.message);
    document.getElementById('preferences').innerText = `Error: ${error.message}`;
  }
}

// We define the updateIndicator function outside the fetch function
function updateIndicator(englishValue, otherValue) {
  // 1. Clamp negative values to 0
  if (englishValue < 0) englishValue = 0;
  if (otherValue   < 0) otherValue   = 0;

  // 2. Compute total with clamped values
  let total = englishValue + otherValue;
  if (total === 0) {
    total = 1; // Prevent division by zero
  }
  let percentage = (otherValue / total) * 100;

  // 4. Clamp the percentage between 0 and 100
  percentage = Math.max(0, Math.min(percentage, 100));

  // 5. Update the indicator
  const indicator = document.getElementById('indicator');
  const container = document.querySelector('.language-bar-container');

  if (indicator && container) {
    const barWidth       = container.clientWidth;
    const indicatorWidth = indicator.clientWidth;

    // Convert percentage to pixel position
    let position = (percentage / 100) * barWidth;
    position    -= (indicatorWidth / 2);

    indicator.style.left = `${position}px`;
    console.log(`Indicator position: ${position}px (${percentage}%)`);
  } else {
    console.error("Indicator or container not found");
  }
}



async function fetchAndRenderMovies(movieIds) {
    try {
        // Construct the API URL with all movie IDs in a single request
        const queryParams = movieIds.map(id => `movie_id=${id}`).join('&');
        const url = `http://localhost:3030/api/movies?${queryParams}&include_all=False`;

        // Fetch movie details
        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`Failed to fetch movie data: ${response.status} ${response.statusText}`);
        }

        const movies = await response.json();

        const allMovies = movies.map(movie => ({
            movie: {
                movie_id: movie.movie_id,
                title: movie.title,
                poster_url: movie.poster_url,
                rating: movie.rating,
                director: movie.director,
            },
            source: 'both',
        }));

        renderMovies(allMovies);
    } catch (error) {
        console.error('Error fetching movie details:', error.message);
        document.getElementById('movies-container').innerText = `Error: ${error.message}`;
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

  
// Render movies dynamically
function renderMovies(allMovies) {
const container = document.getElementById('movies-container');
container.innerHTML = ''; // Clear current display

let movieItemsHTML = '';
allMovies.forEach(({ movie, source }) => {
if (sourceFilter === 'both' || sourceFilter === source) {
    const formattedTitle = reformatTitle(movie.title || defaultTitle);
    const posterUrl = movie.poster_url ? basePosterUrl + movie.poster_url : defaultPosterUrl;
    movieItemsHTML += `
    <a href="../movie/movie.html?movie_id=${movie.movie_id}" class="movie-item">
        <img src="${posterUrl}">
        <div class="movie-item-content">
        <div class="movie-item-title">${formattedTitle}</div>
        </div>
    </a>`;
}
});
container.innerHTML = movieItemsHTML;
}
  

function getQueryParam(param) {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get(param);
}

// Function to get URL parameters
function getQueryParam(param) {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get(param);
}

// Get userId from the URL or sessionStorage
const urlUserId = getQueryParam('userId');
const storedUserId = sessionStorage.getItem('userId');

const isUserIdFromUrl = !!urlUserId;  
const userId = urlUserId || storedUserId;  

if(isUserIdFromUrl){
  document.querySelector(".title").innerHTML = `Profile of user ${userId}`;
}


let languagesData;  

if (userId) {
  fetchUserProfile(userId);
  fetchUserHistory(userId);
  languagesData = fetchUserPreferences(userId); 
} else {
  console.warn('No userId found in URL or sessionStorage.');
  window.location.replace('../auth/login.html');
}




updateIndicator(languagesData.English, languagesData.Other);

function renderSkeletonLoaders() {
    const container = document.getElementById('movies-container');
    container.innerHTML = ''; // Clear current display

    // Add skeleton loaders
    for (let i = 0; i < 10; i++) { // Adjust the number of placeholders as needed
        const skeletonItem = `
            <div class="skeleton-movie-item">
                <div class="skeleton skeleton-movie-image"></div>
                
            </div>`;
        container.innerHTML += skeletonItem;
    }
}


function DeleteUser() {
  fetch(`http://localhost:3303/delete_user/${userId}`, {
      method: 'DELETE',
      headers: {
          'Content-Type': 'application/json'
      }
  })
  .then(response => response.json())
  .then(data => {
      if (data.success) {
          // Clear userId from sessionStorage
          sessionStorage.removeItem('userId');

          // Redirect the user to the login page
          window.location.href = '../auth/login.html';
      } else {
          alert('Action failed.');
      }
  })
  .catch(error => {
      console.error('Error deleting user:', error);
      alert('An error occurred while deleting the user.');
  });
}


function Redirect(url) {
  if(!isUserIdFromUrl){
    window.location.href = url;
  }
}

function LogOut(){
  if(!isUserIdFromUrl){
    sessionStorage.removeItem('userId');
    window.location.href = '../auth/login.html';
  }
}

