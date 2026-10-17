import os
import socket
import time

SPACER = "<space>"
BUFFER_SIZE = 4096 

host = "192.168.97.2"
port = 55001

FILE_SOURCE_DIR = "file_source"
FILE_SIZE = 245 * 1024 * 1024
FILE_COUNT = 3
WRITE_CHUNK_SIZE = 1024 * 1024

os.makedirs(FILE_SOURCE_DIR, exist_ok=True)
files = []
for index in range(1, FILE_COUNT + 1):
    path = os.path.join(FILE_SOURCE_DIR, f"test_file{index}.snp")
    files.append(path)
    if os.path.isfile(path) and os.path.getsize(path) == FILE_SIZE:
        continue

    with open(path, "wb") as f:
        remaining = FILE_SIZE
        chunk = b"0" * WRITE_CHUNK_SIZE
        while remaining:
            bytes_to_write = min(WRITE_CHUNK_SIZE, remaining)
            f.write(chunk[:bytes_to_write])
            remaining -= bytes_to_write

print(f"Starting loop, stop it with Ctrl^C")
while True:
    for index, filename in enumerate(files):
        filesize = os.path.getsize(filename)

        s = socket.socket()
        print(f"[Connecting to server {host}:{port}")
        s.connect((host, port))
        print(f"Connected.")

        s.sendall(f"{filename}{SPACER}{filesize}\n".encode())

        # sends files to ensure continual throughput on a continual loop
        with open(filename, "rb") as f:
            while True:
                bytes_read = f.read(BUFFER_SIZE)
                if not bytes_read:
                    break
                s.sendall(bytes_read)
        print(f"File {filename} Complete.")
        s.close()
        time.sleep(2)
