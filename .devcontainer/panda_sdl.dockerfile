
# Use the base image with Python 3.10
FROM mcr.microsoft.com/devcontainers/base:ubuntu

# Set variables for Spinnaker filenames
ARG SPINNAKER_VERSION=spinnaker-4.0.0.116-amd64-pkg-22.04
ARG SPINNAKER_PYTHON_VERSION=spinnaker_python-4.0.0.116-cp310-cp310-linux_x86_64

# Make variables for the tar files
ARG SPINNAKER_TAR_FILE=${SPINNAKER_VERSION}.tar.gz
ARG SPINNAKER_PYTHON_TAR_FILE=${SPINNAKER_PYTHON_VERSION}.tar.gz

# Make whl file for the Spinnaker Python SDK
ARG SPINNAKER_PYTHON_VERSION=${SPINNAKER_PYTHON_VERSION}.whl


# Set the main python version to 3.10
ARG PYTHON_VERSION=3.10

# Install Python 3.10
RUN apt-get update && apt-get install -y python${PYTHON_VERSION} python3-pip && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libavcodec58 \
    libavformat58 \
    libbz2-dev \
    libdouble-conversion3 \
    libffi-dev \
    liblzma-dev \
    libncurses5-dev \
    libncursesw5-dev \
    libpcre2-16-0 \
    libraw1394-dev \
    libreadline-dev \
    libsqlite3-dev \
    libssl-dev \
    libswresample3 \
    libswscale5 \
    libudev-dev \
    libusb-1.0-0 \
    libxcb-xinerama0 \
    libxcb-xinput0 \
    qt5-qmake \
    qtbase5-dev \
    qtbase5-dev-tools \
    qtchooser \
    software-properties-common \
    tar \
    tk-dev \
    wget \
    xz-utils \
    zlib1g-dev \
    zstd 

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_22.x -o nodesource_setup.sh && \
 bash nodesource_setup.sh && \
 apt-get install -y nodejs && \
 node -v

RUN apt-get clean \
    && apt-get update \
    && apt-get install dpkg \
    && apt --fix-broken install -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the Spinnaker tar file into container
COPY /installers/${SPINNAKER_TAR_FILE} /tmp/${SPINNAKER_TAR_FILE}

# Copy Spinnaker Python SDK tar file into container
COPY /installers/${SPINNAKER_PYTHON_TAR_FILE} /tmp/${SPINNAKER_PYTHON_TAR_FILE}

# Create a usrgroup called flirimaging
RUN groupadd flirimaging

# Add root user to the flirimaging group
RUN usermod -aG flirimaging root



# To install Spinnaker:
# Extract the tar file
# Get the first directory that matches the pattern
# Run the install script
RUN cd /tmp && tar -xzf ${SPINNAKER_TAR_FILE} && \ 
cd $(ls | grep spinnaker- | head -n 1) && \ 
echo -e "yes\nyes\n\nyes\nyes\nno\nno" | sh install_spinnaker.sh

# Install Spinnaker Python SDK
RUN cd /tmp && tar -xzf ${SPINNAKER_PYTHON_TAR_FILE} && pip install ${SPINNAKER_PYTHON_VERSION}

# Switch to the new user (uncomment if needed)
# ARG USER_UID=1000
# ARG USER_GID=1000
# ARG USERNAME=vscode
# RUN groupmod -g ${USER_GID} ${USERNAME} \
#     && usermod -u ${USER_UID} -g ${USER_GID} ${USERNAME} \
#     && chown -R ${USER_UID}:${USER_GID} /home/${USERNAME}
# USER ${USERNAME}