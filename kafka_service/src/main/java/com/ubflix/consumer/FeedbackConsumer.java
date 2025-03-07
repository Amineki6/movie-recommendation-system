package com.ubflix.consumer;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import com.ubflix.models.FeedbackModel;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@Service
public class FeedbackConsumer {

    private static final String TOPIC = "feedbacks";
    private static final String FLASK_API_URL = "http://feedback_service:6090/feedback";
    private static final Logger logger = LoggerFactory.getLogger(FeedbackConsumer.class);

    @Autowired
    private RestTemplate restTemplate;

    @KafkaListener(
        topics = TOPIC,
        groupId = "feedback-processing-group",
        containerFactory = "feedbackKafkaListenerContainerFactory"
    )
    public void consumeFeedback(FeedbackModel feedback) {
        try {
            int userId = feedback.getUserId(); // Extract user ID
            logger.info("Received feedback from userId_{}", userId);
    
            // Make the API call to Flask
            String response = restTemplate.postForObject(
                FLASK_API_URL,
                feedback,
                String.class
            );
            logger.info("Response from Flask API: {}", response);
    
        } catch (Exception e) {
            logger.error("Error processing feedback from userId_{}: {}", feedback.getUserId(), e.getMessage(), e);
        }
    }
}
