package com.ubflix.service;

import com.ubflix.models.FeedbackModel;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;
import org.springframework.kafka.support.SendResult;
import java.util.concurrent.CompletableFuture;

@Service
public class FeedbackProducer {
    
    private static final String FEEDBACK_TOPIC = "feedbacks";
    private static final Logger logger = LoggerFactory.getLogger(FeedbackProducer.class);

    @Autowired
    private KafkaTemplate<String, FeedbackModel> kafkaTemplate;

    public void sendFeedback(FeedbackModel feedback) {
        int userId = feedback.getUserId();
        logger.info("Sending feedback from userId_{} to topic {}", userId, FEEDBACK_TOPIC);

        CompletableFuture<SendResult<String, FeedbackModel>> future = kafkaTemplate.send(FEEDBACK_TOPIC, feedback);
        future.whenComplete((result, ex) -> {
            if (ex == null) {
                logger.info("Feedback from userId_{} sent successfully.", userId);
            } else {
                logger.error("Feedback from userId_{} failed.", userId, ex);
            }
        });
    }
}