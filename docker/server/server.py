import os
import socket

SERVER_HOST = "0.0.0.0"
SERVER_PORT = 55001

BUFFER_SIZE = 4096 # this emulates sizes of writes to disk chunks in CRDB storage engine
SPACER = "<space>"

s = socket.socket()

s.bind((SERVER_HOST, SERVER_PORT))

# Setting arbitrary num of connections for this test, realistically this would 
# be equal to the number of nodes (1 snapshot per node in CRDB at a time, to 
# more closely repro the original behavior)
s.listen(5)
print(f"Listening on {SERVER_HOST}:{SERVER_PORT}")

while True:
    client_socket, address = s.accept() 
    print(f"[+] {address} is connected.")

    received = b""
    while not received.endswith(b"\n"):
        received += client_socket.recv(1)

    filename, filesize = received.decode().strip().split(SPACER)
    filename = os.path.join("file_dest", os.path.basename(filename))
    filesize = int(filesize)

    with open(filename, "wb") as f:
        bytes_received = 0
        while bytes_received < filesize:
            bytes_read = client_socket.recv(min(BUFFER_SIZE, filesize - bytes_received))
            if not bytes_read:
                break
            f.write(bytes_read)
            bytes_received += len(bytes_read)

    print(f"File {filename} received successfully.")
    client_socket.close()