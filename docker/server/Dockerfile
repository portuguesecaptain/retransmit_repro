FROM python:alpine3.24

# This is not contained in the above image
RUN apk add --no-cache tcpdump

WORKDIR /test

ENV PATH="/venv/bin:$PATH"
RUN python3 -m venv /venv

COPY . .

# This replicates on-prem nodes
CMD ["python3", "server.py"]