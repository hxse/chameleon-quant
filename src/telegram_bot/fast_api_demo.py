from typing import Union

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse, HTMLResponse
import uvicorn

import sys
from pathlib import Path

if sys.platform.startswith("linux"):
    print("Linux")
    file_path = "/root/chameleon-quant/strategy/config.json"
elif sys.platform.startswith("win"):
    file_path = "src/strategy/config.json"
    print("Windows")
elif sys.platform.startswith("darwin"):
    print("macOS")
else:
    print("Unsatisfactory")

app = FastAPI()


@app.get("/fig_html/", response_class=HTMLResponse)
async def read_items():
    with open(Path(file_path).parent / "fig.html", "rb") as f:
        data = f.read()
    return data


@app.get("/")
def main():
    return {"Hello": "World"}


if __name__ == "__main__":
    print("hello")
    uvicorn.run("fast_api_demo:app", host="127.0.0.1", port=2197)
