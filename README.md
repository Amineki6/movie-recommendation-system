# Movie Recommendation System

This project is a **microservices-based movie recommendation system** that is fully dockerized using **Docker Compose**. For a comprehensive understanding of the system's architecture, implementation, and evaluation, please refer to:

- **[Movie Recommendation System - Documentation](https://github.com/Amineki6/movie-recommendation-system/blob/main/Movie%20Recommendation%20System%20-%20Documentation.pdf)**: Detailed documentation of the codebase, microservices, evaluation, and user experience.

---

## **Prerequisites**
Before starting, ensure you have the following installed:

1. **Docker** – [Download and install](https://www.docker.com/get-started)
2. **Docker Compose** – Included with Docker Desktop or install separately
3. **Java** - To install Java version 17 on Linux, follow these steps:

    Run the following command to check which Java version is currently installed:
    ```
    java -version
    ```
    if it shows Java 17, you can skip to the next section.
    otherwise:
    ```
    sudo apt update
    sudo apt install openjdk-17-jdk -y
    ```
    After installation, verify that Java 17 is installed:
    ```
    java -version
    ```
    You should see output similar to:
    ```
    openjdk version "17.0.x"
    ```

4. **Maven**: To install Maven on Linux, follow these steps:

    first run this command:
    ```
    sudo apt install maven -y
    ```
    verify your installation with this command:
    ```
    mvn --version
    ```


---

## **Project Structure**

The project follows a microservices architecture, with each service contained within its own directory:

```
analytics_service/
auth_service/
database_service/
feedback_service/
kafka_service/
model_service/
nginx/
telemetry_service/
ui_service/
web/
apis.txt
docker-compose.yml
```

## **Setup and Running the System**

### **1. Clone the Repository**

```sh
git clone https://gitlab.informatik.uni-bremen.de/mkina/aia_e_assignments.git
cd "aia_e_assignments/Assignment 6/movie_recommendation_system"
```

### **2. Build the Kafka Service**
Navigate to the `kafka_service` directory and build the Kafka service:
```sh
cd kafka_service
mvn clean install -DskipTests
cd ..
```

### **3. Start the Containers**
Run the following command to build and start all services:
```sh
docker-compose up --build
```
(*On newer versions of docker compose, try this command instead*)
```
docker compose up --build
```


If you don’t need to rebuild the images, use (without dash for newer versions):
```sh
docker-compose up -d
```
(*Runs in detached mode*)

### **4. Verify Running Services**
Check if all services are running:
```sh
docker ps
```
If there are issues, check logs:
```sh
docker-compose logs -f
```

### **5. Initialize Redis Namespaces (First Time Only)**
Once all services are up and running, initialize Redis namespaces by running the following command in a terminal:
```sh
curl -X POST http://localhost:7070/initialize
```
(*This step is necessary only once when you first build the images.*)

### **6. Start the UI**
Navigate to the `web` folder and run the UI service:
```sh
cd web
python start-web.py
```

This will start up the UI for the system.

### **7. Monitoring Services**
- **Grafana Dashboard:** Accessible at:
  ```
  http://localhost:3000
  ```
- **Prometheus Metrics:** Accessible at:
  ```
  http://localhost:9090
  ```

### **8. Stop the System**
To stop all running services:
```sh
docker-compose down
```

---

## **Troubleshooting**

- **Port conflicts?** Stop conflicting processes.
- **Cache issues?** Force rebuild with:
  ```sh
  docker-compose up --force-recreate --build
  ```
- **Kafka issues?** Ensure the kafka service is up and running with:
  ```sh
  docker-compose logs kafka_service
  ```

---

