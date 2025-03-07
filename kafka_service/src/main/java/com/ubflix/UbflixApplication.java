package com.ubflix;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;


@SpringBootApplication(scanBasePackages = "com.ubflix")
public class UbflixApplication {

	public static void main(String[] args) {
		SpringApplication.run(UbflixApplication.class, args);
	}

}

