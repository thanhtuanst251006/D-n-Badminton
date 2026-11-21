FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home app

WORKDIR /app
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY src/ src/
COPY .streamlit/ .streamlit/
COPY --chown=app:app data/ data/

USER app
EXPOSE 8501
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s \
    CMD ["python", "-c", "from urllib.request import urlopen; urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3).close()"]
CMD ["python", "-m", "streamlit", "run", "app/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
