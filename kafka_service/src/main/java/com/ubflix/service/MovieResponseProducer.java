package com.ubflix.service;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.util.concurrent.CompletableFuture;
import org.springframework.kafka.support.SendResult;


@Service
public class MovieResponseProducer {

    private static final String RESPONSE_TOPIC = "recommendations_responses";
    private static final Logger logger = LoggerFactory.getLogger(MovieResponseProducer.class);

    @Autowired
    private KafkaTemplate<String, String> kafkaTemplate;

    public void sendResponseMessage(String response) {
        logger.info("Sending response to topic {}", RESPONSE_TOPIC);

        CompletableFuture<SendResult<String, String>> future = kafkaTemplate.send(RESPONSE_TOPIC, response);
        future.whenComplete((result, ex) -> {
            if (ex == null) {
                logger.info("Response sent successfully.");
            } else {
                logger.error("Failed to send response.", ex);
            }
        });
    }
}

