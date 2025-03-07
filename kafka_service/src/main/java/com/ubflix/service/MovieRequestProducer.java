package com.ubflix.service;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;
import com.ubflix.models.MovieRequestModel; 
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.util.concurrent.CompletableFuture;
import org.springframework.kafka.support.SendResult;

@Service
public class MovieRequestProducer {
    
    private static final String REQUEST_TOPIC = "recommendations_requests";
    private static final Logger logger = LoggerFactory.getLogger(MovieRequestProducer.class);

    @Autowired
    private KafkaTemplate<String, MovieRequestModel> kafkaTemplate; 

    public void sendMessage(MovieRequestModel request) { 
        int userId = request.getUserId();
        logger.info("Sending userId_{} request to topic {}", userId, REQUEST_TOPIC);

        CompletableFuture<SendResult<String, MovieRequestModel>> future = kafkaTemplate.send(REQUEST_TOPIC, request);
        future.whenComplete((result, ex) -> {
            if (ex == null) {
                logger.info("userId_{} request sent successfully.", userId);
            } else {
                logger.error("userId_{} request failed.", userId, ex);
            }
        });
    }
}
