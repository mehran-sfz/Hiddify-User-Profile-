# Use the official Python image from the Docker Hub
FROM python:3.11-slim-buster

# Set the working directory in the container
WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y build-essential libpq-dev
RUN rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --upgrade pip && pip install -r requirements.txt
