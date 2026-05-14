# HuggingFace Spaces deployment for the Streamlit demo.
# HF's "Streamlit SDK" was retired — Spaces now hosts custom apps via
# Docker. This image is the same thing the Streamlit SDK used to set up
# automatically: Python + Streamlit + the app, on HF's expected port 7860.

FROM python:3.14-slim

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
