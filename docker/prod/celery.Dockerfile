# Use the official Python image as a base image
FROM python:3.11-slim-bullseye

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# Install necessary packages, including PostgreSQL client (psql)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file to the working directory
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Add Users
RUN addgroup --system celery && adduser --system --ingroup celery celery

# copy scripts and +x them
COPY ./docker/dev/ /scripts
RUN chmod -R +x /scripts
RUN chown -R celery:celery /scripts

# copy application code to WORKDIR
COPY --chown=celery:celery . /app

# make celery owner of the WORKDIR directory as well
RUN chown celery:celery /app

USER celery
WORKDIR /app

ENTRYPOINT ["/scripts/celery.entrypoint.sh"]
