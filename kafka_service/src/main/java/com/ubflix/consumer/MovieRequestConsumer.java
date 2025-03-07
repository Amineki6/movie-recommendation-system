package com.ubflix.consumer;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpEntity;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import com.ubflix.models.MovieRequestModel;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;

@Service
public class MovieRequestConsumer {

    private static final String TOPIC = "recommendations_requests";
    private static final String FLASK_API_URL = "http://gen_service:6060/generate";
    private static final Logger logger = LoggerFactory.getLogger(MovieRequestConsumer.class);

    @Autowired
    private RestTemplate restTemplate;

    @KafkaListener(
        topics = TOPIC,
        groupId = "movie-recommendation-group",
        containerFactory = "kafkaListenerContainerFactory"
    )
    public void consumeMessage(MovieRequestModel request) {
        try {
            int userId = request.getUserId(); // Extract user ID
            logger.info("Received movie recommendation request for userId_{}", userId);
            logger.info("Request {}", request);

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            // This is your request body (the object you want to serialize):
            HttpEntity<MovieRequestModel> entity = new HttpEntity<>(request, headers);

            // Make the API call to Flask
            String response = restTemplate.postForObject(
                FLASK_API_URL,
                entity,
                String.class
            );

            if (response != null) {
                logger.info("Successfully sent recommendations to Flask API: {}", response);
            } else {
                logger.warn("Flask API response was null");
            }
    
        } catch (Exception e) {
            logger.error("Error processing message for userId_{}: {}", request.getUserId(), e.getMessage(), e);
        }
    }
    
}