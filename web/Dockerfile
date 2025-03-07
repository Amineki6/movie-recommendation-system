# Use an official PHP image with Apache
FROM php:8.2-apache

# Install PostgreSQL extension and required PHP modules
RUN apt-get update && apt-get install -y \
    libpq-dev \
    && docker-php-ext-install pdo pdo_pgsql pgsql

# Enable required Apache modules
RUN a2enmod rewrite headers

# Allow .htaccess files to override Apache settings
RUN sed -i 's/AllowOverride None/AllowOverride All/' /etc/apache2/apache2.conf

# Set working directory
WORKDIR /var/www/html

# Copy only the PHP directory to the container
COPY php/ /var/www/html/

# Expose Apache port
EXPOSE 80
