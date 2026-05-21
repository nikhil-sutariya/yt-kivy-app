FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# System dependencies
RUN apt update && apt install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    git \
    zip \
    unzip \
    openjdk-17-jdk \
    autoconf \
    libtool \
    pkg-config \
    zlib1g-dev \
    libncurses5-dev \
    libncursesw5-dev \
    cmake \
    libffi-dev \
    libssl-dev \
    build-essential \
    ccache \
    wget \
    curl \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Environment variables
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV ANDROID_HOME=/opt/android-sdk
ENV ANDROID_SDK_ROOT=/opt/android-sdk
ENV PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools

# Install Android SDK command line tools
RUN mkdir -p /opt/android-sdk/cmdline-tools && \
    cd /opt/android-sdk/cmdline-tools && \
    wget https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip -O tools.zip && \
    unzip tools.zip && \
    mv cmdline-tools latest && \
    rm tools.zip

# Accept licenses and install SDK components
RUN yes | sdkmanager --licenses

RUN sdkmanager \
    "platform-tools" \
    "platforms;android-33" \
    "build-tools;33.0.2" \
    "ndk;25.2.9519653"

# Create app directory
WORKDIR /app

# Copy project
COPY . /app

# Python virtual environment
RUN python3.11 -m venv venv

# Install Python dependencies
RUN . venv/bin/activate && \
    pip install --upgrade pip setuptools wheel && \
    pip install \
        cython==0.29.37 \
        buildozer \
        kivy==2.3.0

# Default shell
SHELL ["/bin/bash", "-c"]

# Build command
CMD source venv/bin/activate && buildozer android debug