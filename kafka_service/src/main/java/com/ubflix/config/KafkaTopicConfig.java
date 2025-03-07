package com.ubflix.config;

import org.apache.kafka.clients.admin.NewTopic;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.TopicBuilder;

@Configuration
public class KafkaTopicConfig {

    @Bean
    public NewTopic recommendationsRequestsTopic() {
        return TopicBuilder.name("recommendations_requests")
                .partitions(3)
                .replicas(1)
                .build();
    }

    @Bean
    public NewTopic movieRecommendationsTopic() {
        return TopicBuilder.name("recommendations_responses")
                .partitions(3)
                .replicas(1)
                .build();
    }

    @Bean
    public NewTopic feedbacksTopic() {
        return TopicBuilder.name("feedbacks")
                .partitions(3)
                .replicas(1)
                .build();
    }
    
}
