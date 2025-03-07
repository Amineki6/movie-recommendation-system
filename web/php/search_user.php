<?php

header("Access-Control-Allow-Origin: *"); 
header("Access-Control-Allow-Methods: GET, POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type, Authorization");
// Enable error reporting
error_reporting(E_ALL);
ini_set('display_errors', 1);

// Database connection (replace with your actual credentials and port if necessary)
$servername = "postgresinstance.cpyqmeeock79.eu-north-1.rds.amazonaws.com";
$username = "postgres";
$password = "postgre123";
$dbname = "postgresdb";
$port = "5432"; 

// Connect to PostgreSQL (including the port)
$conn = pg_connect("host=$servername dbname=$dbname user=$username password=$password port=$port");

// Check connection
if (!$conn) {
    echo json_encode(["error" => "Connection failed: " . pg_last_error()]);
    exit;  // Ensure no further output
}

// Fetch the search term from the query string
$searchTerm = $_GET['term'];

// Prepare and execute the query to search for directors
$sql = "SELECT * FROM users WHERE LOWER(firstname) LIKE LOWER($1) AND (password IS NULL OR password <> 'deleted')";
$result = pg_query_params($conn, $sql, array('%' . $searchTerm . '%'));

// Check for query errors
if (!$result) {
    echo json_encode(["error" => "Query failed: " . pg_last_error()]);
    exit;
}

// Fetch the results and return as JSON
$rows = []; // Array to store all rows

while ($row = pg_fetch_assoc($result)) {
    $rows[] = $row; // Add the entire row to the array
}

echo json_encode($rows);

// Close the connection
pg_close($conn);

?>
