package com.ubflix.consumer;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.ubflix.models.MovieResponseModel;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@Service
public class MovieResponseConsumer {
    private static final String TOPIC = "recommendations_responses";
    private static final String FLASK_API_URL = "http://store_service:6061/store";
    private static final Logger logger = LoggerFactory.getLogger(MovieResponseConsumer.class);
    
    private final ObjectMapper objectMapper;
    @Autowired
    private RestTemplate restTemplate;

    public MovieResponseConsumer(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
        this.objectMapper = new ObjectMapper()
            .registerModule(new JavaTimeModule())
            .configure(DeserializationFeature.ADJUST_DATES_TO_CONTEXT_TIME_ZONE, false);
    }

    @KafkaListener(
        topics = TOPIC,
        groupId = "movie-recommendations-group",
        containerFactory = "recommendationsKafkaListenerContainerFactory"
    )
    public void consumeRecommendations(String message) {
        try {
            MovieResponseModel recommendations = objectMapper.readValue(message, MovieResponseModel.class);

            String response = restTemplate.postForObject(
                FLASK_API_URL,
                recommendations,
                String.class
            );

            if (response != null) {
                logger.info("Successfully sent recommendations to Flask API: {}", response);
            } else {
                logger.warn("Flask API response was null");
            }

            
        } catch (Exception e) {
            logger.error("Error processing recommendations: {}", e.getMessage(), e);
        }
    }
}