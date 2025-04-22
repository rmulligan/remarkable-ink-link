
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies: Java, Go, git, wget
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       openjdk-17-jre-headless \
       golang-go \
       git \
       wget \
    && rm -rf /var/lib/apt/lists/*

# Install drawj2d (native ink converter)
RUN wget -qO /tmp/drawj2d.deb \
        "https://download.sourceforge.net/project/drawj2d/1.3.4/drawj2d_1.3.4-4.1_all.deb" \
    && apt-get update \
    && apt-get install -y --no-install-recommends /tmp/drawj2d.deb \
    && rm -f /tmp/drawj2d.deb \
    && rm -rf /var/lib/apt/lists/* \
    # Ensure drawj2d is executable
    && chmod +x /usr/bin/drawj2d || true

# Install fonts for document conversion (provide Liberation Sans and DejaVu Sans Mono)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       fonts-liberation \
       fonts-dejavu-core \
       poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Build and install ddvk rmapi (reMarkable cloud client)
RUN git clone https://github.com/ddvk/rmapi.git /tmp/rmapi \
    && cd /tmp/rmapi \
    && go build -o /usr/local/bin/rmapi . \
    && rm -rf /tmp/rmapi \
    # Prepare rmapi config directory for credentials
    && mkdir -p /root/.config/rmapi && chmod 700 /root/.config/rmapi

RUN pip install --upgrade pip && pip install poetry

COPY pyproject.toml poetry.lock README.md /app/
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

COPY . /app
RUN poetry install --no-interaction --no-ansi

## Expose default InkLink server port
EXPOSE 9999

# Default to running the HTTP server on all interfaces
CMD ["poetry", "run", "inklink", "server", "--host", "0.0.0.0", "--port", "9999"]