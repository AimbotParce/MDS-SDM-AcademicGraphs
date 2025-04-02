FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src .

# Default to running a Bash shell (services will override this in compose)
CMD ["bash"]
