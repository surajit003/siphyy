# HuggingFace Spaces deployment for the Streamlit demo.
# HF's "Streamlit SDK" was retired — Spaces now hosts custom apps via
# Docker. This image is the same thing the Streamlit SDK used to set up
# automatically: Python + Streamlit + the app, on HF's expected port 7860.

FROM python:3.14-slim

# git is required by requirements.txt to fetch `siphyy @ git+https://...`.
# The slim image strips it by default. ca-certificates is what lets git
# verify the GitHub TLS handshake — usually present in slim, included
# explicitly so a future Debian point-release change can't surprise us.
RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# HF Spaces require running as a non-root user.
ARG USERNAME=user
ARG UID=1000
RUN useradd --create-home --uid $UID --shell /bin/bash $USERNAME

WORKDIR /app

# Install dependencies first so layer caching benefits unchanged builds.
COPY --chown=$USERNAME:$USERNAME requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app.
COPY --chown=$USERNAME:$USERNAME . .

USER $USERNAME

# HF Spaces routes external traffic to port 7860.
EXPOSE 7860

CMD ["streamlit", "run", "app.py", \
     "--server.port=7860", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
