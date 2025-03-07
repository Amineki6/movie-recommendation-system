
const userId = sessionStorage.getItem('userId');

let selectedDirector = null; // the locally selected director
let selectedModel = null;    // the locally selected model

$(document).ready(function() {

    $('#suggestions').hide();

    // -----------------------------------------------
    // 1) DIRECTOR SEARCH + SUGGESTIONS (unchanged)
    // -----------------------------------------------
    $('#director-input').on('input', function() {
        var searchTerm = $(this).val();
        if (searchTerm.length > 2) {
            $.ajax({
                url: 'http://localhost:8081/search_director.php',
                method: 'GET',
                data: { term: searchTerm },
                success: function(response) {
                    var directors = Array.isArray(response) ? response : JSON.parse(response);
                    var suggestions = '';
                    if (directors.length > 0) {
                        directors.forEach(function(director) {
                            suggestions += '<div class="suggestion-item">' + director + '</div>';
                        });
                        $('#suggestions').html(suggestions).show(); 
                    } else {
                        $('#suggestions').hide();
                    }
                }
            });
        } else {
            $('#suggestions').hide();
        }
    });

    // When a suggestion is clicked, fill the input
    $(document).on('click', '.suggestion-item', function() {
        $('#director-input').val($(this).text());
        $('#suggestions').hide();
    });

    // Hide suggestions on outside click
    $(document).on('click', function(event) {
        if (!$(event.target).closest('.input-wrapper').length) {
            $('#suggestions').hide();
        }
    });


    // -----------------------------------------------
    // 2) SAVE DIRECTOR CLICK
    // -----------------------------------------------
    const saveButton = document.getElementById('save-button');
    const directorInput = document.getElementById('director-input');
    const directorDisplay = document.getElementById('director-display');

    saveButton.addEventListener('click', () => {
        const directorValue = directorInput.value.trim();
        // Store it in our local variable only if it differs from what we have now
        selectedDirector = directorValue ? directorValue : null;
        
        // Update the display
        updateDirectorDisplay(selectedDirector);

        // Now check if there’s a difference from the stored (sessionStorage) data
        updatePersonalizationStatus();
    });


    // -----------------------------------------------
    // 3) UPDATE DIRECTOR DISPLAY
    // -----------------------------------------------
    function updateDirectorDisplay(directorName) {
        if (directorName) {
            directorDisplay.innerHTML = `
                <div style="text-align: center;">
                    Selected as favorite: 
                    <span style="text-decoration: underline;">${directorName}</span> 
                    <button id="remove-director" 
                            style="border: none; background: none; color: red; cursor: pointer;">
                        ✖
                    </button>
                    <div><i>(click X to remove it)</i></div>
                </div>
            `;
            // "X" button to remove the director
            document.getElementById('remove-director')
                .addEventListener('click', () => {
                    selectedDirector = null;
                    directorDisplay.innerHTML = "";
                    updatePersonalizationStatus();
                });
        } else {
            directorDisplay.innerHTML = ""; 
        }
    }


    // -----------------------------------------------
    // 4) LOAD SAVED DIRECTOR FROM SESSION ON PAGE LOAD
    // -----------------------------------------------
    window.addEventListener('load', () => {
        const storedDirector = sessionStorage.getItem('favoriteDirector');
        if (storedDirector) {
            selectedDirector = storedDirector;
            updateDirectorDisplay(storedDirector);
        }
        const storedModel = sessionStorage.getItem('favoriteModel');
        if (storedModel) {
            selectedModel = storedModel;
            // Re-select the appropriate button
            const allModelButtons = document.querySelectorAll('.model-button');
            allModelButtons.forEach(btn => {
                btn.classList.remove('selected');
                if (
                    (storedModel === '01' && btn.textContent === 'Content-Based') ||
                    (storedModel === '02' && btn.textContent === 'Collaborative-Based') ||
                    (storedModel === '03' && btn.textContent === 'Popularity-Based')
                ) {
                    btn.classList.add('selected');
                }
            });
        }
        // After loading from session storage, button should be disabled unless user changes
        updatePersonalizationStatus();
    });
});


// -----------------------------------------------
// 5) MODEL TOGGLE LOGIC
// -----------------------------------------------
function toggleButton(button) {
    const buttons = document.querySelectorAll('.model-button');
    let newSelectedModel = null;

    // If clicking on the same button that is already selected => unselect
    if (button.classList.contains('selected')) {
        newSelectedModel = null;
    } else {
        // Otherwise figure out which was clicked
        if (button.textContent === 'Content-Based') {
            newSelectedModel = '01';
        } else if (button.textContent === 'Collaborative-Based') {
            newSelectedModel = '02';
        } else if (button.textContent === 'Popularity-Based') {
            newSelectedModel = '03';
        }
    }

    // Update the UI
    buttons.forEach(btn => btn.classList.remove('selected'));
    if (newSelectedModel) {
        button.classList.add('selected');
    }

    // Update our local variable
    selectedModel = newSelectedModel;
    // Check if it differs from what's stored
    updatePersonalizationStatus();
}


// -----------------------------------------------
// 6) UPDATE PERSONALIZATION BUTTON STATUS
// -----------------------------------------------
function updatePersonalizationStatus() {
    const button = document.getElementById('save-personalization');

    // Get currently stored values
    const storedDirector = sessionStorage.getItem('favoriteDirector');
    const storedModel = sessionStorage.getItem('favoriteModel');

    // If either the director or model differs from what's stored, enable button
    const directorChanged = (selectedDirector || '') !== (storedDirector || '');
    const modelChanged   = (selectedModel   || '') !== (storedModel   || '');

    if (directorChanged || modelChanged) {
        button.disabled = false;
        button.innerHTML = 'Save Personalization';
        button.style.backgroundColor = '#1f83ed';
    } else {
        button.disabled = true;
        button.innerHTML = 'Save Personalization';
        button.style.backgroundColor = ''; // or revert to original
    }
}


// -----------------------------------------------
// 7) SAVE PERSONALIZATION
// -----------------------------------------------
function savePersonalization() {
    // Write the updated values to sessionStorage
    if (selectedDirector !== null) {
        sessionStorage.setItem('favoriteDirector', selectedDirector);
    } else {
        sessionStorage.removeItem('favoriteDirector');
    }

    if (selectedModel !== null) {
        sessionStorage.setItem('favoriteModel', selectedModel);
    } else {
        sessionStorage.removeItem('favoriteModel');
    }

    // After saving, show success
    const button = document.getElementById('save-personalization');
    button.innerHTML = 'Personalization Saved';
    button.style.backgroundColor = '#4CAF50';
    button.disabled = true;

    // Make your recommendation request
    sendRecommendationRequest(userId);
}


// Call updatePersonalizationStatus() whenever selectedModel or selectedDirector changes
// For example, whenever either of these is updated by your app logic, call this function






// Function to initialize button state based on sessionStorage
function initializeButtonState() {
    const favoriteModel = sessionStorage.getItem('favoriteModel');
    const buttons = document.querySelectorAll('.model-button');

    if (favoriteModel) {
        buttons.forEach(btn => {
            if (favoriteModel === '01' && btn.textContent === 'Content-Based') {
                btn.classList.add('selected');
            } else if (favoriteModel === '02' && btn.textContent === 'Collaborative-Based') {
                btn.classList.add('selected');
            } else if (favoriteModel === '03' && btn.textContent === 'Popularity-Based') {
                btn.classList.add('selected');
            }
        });
    }
}

window.onload = initializeButtonState;


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
        console.log('Response:', textData);
        return textData;

    } catch (error) {
        console.error('Error sending request:', error.message);
        throw error;
    }
}

document.addEventListener("DOMContentLoaded", function () {
    if (!sessionStorage.getItem('userId')) {
      window.location.replace('../auth/login.html');
    }
  });
  