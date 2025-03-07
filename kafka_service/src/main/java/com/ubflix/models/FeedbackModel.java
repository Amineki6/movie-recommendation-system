package com.ubflix.models;

import com.fasterxml.jackson.annotation.JsonProperty;

public class FeedbackModel {
    
    @JsonProperty("user_id") 
    private int userId;

    @JsonProperty("movie_id") 
    private int movieId;
    
    private float rating;
    
    private String source;

    // Default Constructor
    public FeedbackModel() {
        this.source = "unknown"; // Default source
    }

    // Parameterized Constructor (All Fields)
    public FeedbackModel(int userId, int movieId, float rating, String source) {
        this.userId = userId;
        this.movieId = movieId;
        this.rating = rating;
        this.source = source;
    }

    // Constructor without rating
    public FeedbackModel(int userId, int movieId, String source) {
        this.userId = userId;
        this.movieId = movieId;
        this.rating = 0.0f; // Default rating
        this.source = source;
    }

    // Constructor without source
    public FeedbackModel(int userId, int movieId, float rating) {
        this.userId = userId;
        this.movieId = movieId;
        this.rating = rating;
        this.source = "unknown"; // Default source
    }

    // Getters and Setters

    public int getUserId() {
        return userId;
    }

    public void setUserId(int userId) {
        this.userId = userId;
    }

    public int getMovieId() {
        return movieId;
    }

    public void setMovieId(int movieId) {
        this.movieId = movieId;
    }

    public float getRating() {
        return rating;
    }

    public void setRating(float rating) {
        this.rating = rating;
    }
    
    public String getSource() {
        return source;
    }

    public void setSource(String source) {
        this.source = source;
    }

    // toString() method
    @Override
    public String toString() {
        return "FeedbackModel{" +
            "userId=" + userId +
            ", movieId=" + movieId +
            ", rating=" + rating +
            ", source='" + source + '\'' +
            '}';
    }
}
