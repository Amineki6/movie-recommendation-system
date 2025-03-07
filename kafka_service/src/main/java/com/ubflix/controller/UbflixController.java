package com.ubflix.controller;

import com.ubflix.service.MovieRequestProducer;
import com.ubflix.service.MovieResponseProducer;
import com.ubflix.service.FeedbackProducer;
import com.ubflix.models.MovieRequestModel;
import com.ubflix.models.FeedbackModel;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.beans.factory.annotation.Autowired;
import jakarta.validation.Valid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;



@CrossOrigin(origins = "*")
@RestController
@RequestMapping("/recommend")
public class UbflixController {
    
    private static final Logger logger = LoggerFactory.getLogger(UbflixController.class);

    @Autowired
    private MovieRequestProducer requestproducerService;

    @Autowired
    private MovieResponseProducer responseproducerService;
    
    @Autowired
    private FeedbackProducer feedbackProducerService;

    @PostMapping
    public ResponseEntity<String> sendRecommendationRequest(@Valid @RequestBody MovieRequestModel request) {
        String responseMessage = String.format("Sending userId_%s request to producer.", request.getUserId());
        logger.info("{}", responseMessage);
        requestproducerService.sendMessage(request);

        return ResponseEntity.ok(responseMessage);
    }

    @PostMapping("/response")
    public ResponseEntity<String> handleFlaskResponse(@RequestBody String recommendationsResponse) {
        try {
            logger.info("Received response: {}", recommendationsResponse);
            responseproducerService.sendResponseMessage(recommendationsResponse);
            return ResponseEntity.ok("Response successfully sent to Kafka topic!");
        } catch (Exception e) {
            logger.error("Error processing Flask response: {}", e.getMessage());
            return ResponseEntity.internalServerError().body("Error processing response: " + e.getMessage());
        }
    }
    
    @PostMapping("/feedback")
    public ResponseEntity<String> receiveUserFeedback(@Valid @RequestBody FeedbackModel feedback) {
        try {
            feedbackProducerService.sendFeedback(feedback);
            return ResponseEntity.ok("Feedback successfully sent to Kafka topic!");
        } catch (Exception e) {
            logger.error("Error processing user feedback: {}", e.getMessage());
            return ResponseEntity.internalServerError().body("Error processing feedback: " + e.getMessage());
        }
    }
}
