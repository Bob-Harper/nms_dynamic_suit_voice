import os
import json
import websocket

VOSK_SERVER = "ws://localhost:2700"
SOURCE_DIR = r"C:\Local\NMS_LLM\AUDIO"


def transcribe_file(file_path):
    ws = websocket.create_connection(VOSK_SERVER)
    with open(file_path, "rb") as f:
        while chunk := f.read(4000):
            ws.send_binary(chunk)
        ws.send('{"eof" : 1}')

    text = ""
    while True:
        response_raw = ws.recv()
        response = json.loads(response_raw)
        if "text" in response:
            text = response["text"]
        if response.get("partial") == "" or response.get("final", False):
            break
    ws.close()
    return text


with open("transcriptions.csv", "w", encoding="utf-8") as out_file:
    out_file.write("Filename,Transcription\n")
    for root, dirs, files in os.walk(SOURCE_DIR):
        for file in files:
            if file.endswith(".wav"):
                path = os.path.join(root, file)
                text = transcribe_file(path)
                out_file.write(f"{file},{text}\n")
                print(f"{file},{text}")
