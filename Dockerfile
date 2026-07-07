FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p patient_data output

# Default: run the demo pipeline (no API keys needed).
# Override at `docker run` time to pass real args, e.g.:
#   docker run --env-file .env medsaathi python cli.py --image /data/rx.jpg --consent ...
ENTRYPOINT ["python", "cli.py"]
CMD ["--demo"]
