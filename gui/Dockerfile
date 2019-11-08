FROM python:3.7.4-slim

# Update the aptitude package listing so that packages may be loaded and installed
RUN apt-get update

# Install python binaries to make pip installs a little smoother
RUN apt-get install -y python3-django

# Move to a new directory at "/usr/wres-gui"
WORKDIR /usr/maas_portal

# Copy the requirements.txt file in the current directory for the application to the
# working directory of the docker image (/usr/wres-gui)
COPY ./requirements.txt ./

# Install all the python packages described in the requirements file
RUN pip install -r requirements.txt

# Ensures that raw data directed at a terminal moves in one go rather than being buffered
ENV PYTHONUNBUFFERED 1

# Copy selected portions of the project into the working directory (/usr/maas_portal)
COPY ./manage.py ./
COPY ./static ./static
COPY ./schemas ./schemas
COPY ./maas_experiment ./maas_experiment
COPY ./MaaS ./MaaS
COPY ./entrypoint.sh ./

# Set the entry point so that it is run every time the container is started
ENTRYPOINT ["/usr/maas_portal/entrypoint.sh"]
