# Use a base image with Java (since Kafka requires Java)
FROM openjdk:17-jdk-slim

# Set the working directory
WORKDIR /app

# Copy the JAR file to the container
COPY target/ubflix-0.0.1-SNAPSHOT.jar /app/kafka_service.jar

# Expose the port Kafka will run on
EXPOSE 8080

# Define environment variables
ENV KAFKA_BROKER_ID=1
ENV KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181
ENV KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:8080
ENV KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=PLAINTEXT:PLAINTEXT
ENV KAFKA_INTER_BROKER_LISTENER_NAME=PLAINTEXT

# Run the Kafka service
ENTRYPOINT ["java", "-jar", "kafka_service.jar"]
