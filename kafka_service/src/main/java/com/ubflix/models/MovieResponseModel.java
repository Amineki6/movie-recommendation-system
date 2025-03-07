package com.ubflix.models;

import java.time.Instant;
import java.util.List;
import com.fasterxml.jackson.annotation.JsonProperty;

public class MovieResponseModel {
    @JsonProperty("timestamp")
    private Instant timestamp;
    
    @JsonProperty("user_id")
    private Long userId;
    
    @JsonProperty("recommendations")
    private List<List<Object>> recommendations;  // List of [movieId, Source]

    // Getters and Setters
    public Instant getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(Instant timestamp) {
        this.timestamp = timestamp;
    }

    public Long getUserId() {
        return userId;
    }

    public void setUserId(Long userId) {
        this.userId = userId;
    }

    public List<List<Object>> getRecommendations() {
        return recommendations;
    }

    public void setRecommendations(List<List<Object>> recommendations) {
        this.recommendations = recommendations;
    }

    // toString() method
    @Override
    public String toString() {
        return "MovieResponseModel{" +
            "timestamp=" + timestamp +
            ", userId=" + userId +
            ", recommendations=" + recommendations +
            '}';
    }
}
