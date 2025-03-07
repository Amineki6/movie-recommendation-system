package com.ubflix.models;

import com.fasterxml.jackson.annotation.JsonProperty;

public class MovieRequestModel {
    @JsonProperty("user_id") 
    private int userId;

    @JsonProperty("director")
    private String director;

    @JsonProperty("model")
    private String model;

    // Default Constructor
    public MovieRequestModel() {}

    // Parameterized Constructor
    public MovieRequestModel(int userId, String director, String model) {
        this.userId = userId;
        this.director = director;
        this.model = model;
    }

    @Override
    public String toString() {
        return "{" +
            "userId=" + userId +
            ", director='" + director + '\'' +
            ", model='" + model + '\'' +
            '}';
    }

    // Getter and Setter for userId
    public int getUserId() {
        return userId;
    }

    public void setUserId(int userId) {
        this.userId = userId;
    }

    // Getter and Setter for director
    public String getDirector() {
        return director;
    }

    public void setDirector(String director) {
        this.director = director;
    }

    // Getter and Setter for model
    public String getModel() {
        return model;
    }

    public void setModel(String model) {
        this.model = model;
    }
}
