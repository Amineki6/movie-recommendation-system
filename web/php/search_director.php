<?php
// Enable CORS
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: GET, POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type");
header("Content-Type: application/json");

// Enable error reporting for debugging
error_reporting(E_ALL);
ini_set('display_errors', 1);

// Database connection credentials
$servername = "postgresinstance.cpyqmeeock79.eu-north-1.rds.amazonaws.com";
$username = "postgres";
$password = "postgre123";
$dbname = "postgresdb";
$port = "5432"; 

// Connect to PostgreSQL
$conn = pg_connect("host=$servername dbname=$dbname user=$username password=$password port=$port");

// Check connection
if (!$conn) {
    echo json_encode(["error" => "Connection failed: " . pg_last_error()]);
    exit;
}

// Fetch and validate the search term
if (!isset($_GET['term']) || empty(trim($_GET['term']))) {
    echo json_encode(["error" => "No search term provided"]);
    exit;
}

$searchTerm = trim($_GET['term']); // Trim whitespace

// Prepare and execute the query safely
$sql = "SELECT DISTINCT director FROM movies WHERE LOWER(director) LIKE LOWER($1)";
$result = pg_query_params($conn, $sql, ['%' . $searchTerm . '%']);

// Check for query execution errors
if (!$result) {
    echo json_encode(["error" => "Query failed: " . pg_last_error()]);
    pg_close($conn);
    exit;
}

// Fetch and return results as JSON
$directors = [];
while ($row = pg_fetch_assoc($result)) {
    $directors[] = $row['director'];
}

echo json_encode($directors);

// Close connection
pg_close($conn);

?>
