FROM python:alpine3.24

# This is not contained in the above image
RUN apk add --no-cache tcpdump

WORKDIR /test

ENV PATH="/venv/bin:$PATH"
RUN python3 -m venv /venv

COPY . .

# Emulates the MTU setup of the customer's AWS CRDB nodes from the incident
CMD ["/bin/sh", "-c", "ip link set dev eth0 mtu 9001 && exec python3 client.py"]