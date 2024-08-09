# Use the official Python image as a base image
FROM python:3.11-slim-bullseye

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# Copy the requirements file to the working directory
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Add Users
RUN addgroup --system django && adduser --system --ingroup django django

# copy scripts and +x them
COPY ./docker/dev/ /scripts
RUN chmod -R +x /scripts
RUN chown -R django:django /scripts

# copy application code to WORKDIR
COPY --chown=django:django . /app

# make django owner of the WORKDIR directory as well
RUN chown django:django /app

USER django
WORKDIR /app

ENTRYPOINT ["/scripts/entrypoint.sh"]