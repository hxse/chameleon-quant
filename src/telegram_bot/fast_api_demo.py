from typing import Union

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse, HTMLResponse
import uvicorn

import sys
from pathlib import Path

if sys.platform.startswith("linux"):
    print("Linux")
    config_path = "/root/chameleon-quant/strategy/config.json"
elif sys.platform.startswith("win"):
    config_path = "src/strategy/config.json"
    print("Windows")
elif sys.platform.startswith("darwin"):
    print("macOS")
else:
    print("Unsatisfactory")

app = FastAPI()


@app.get("/fig_html/{symbol}/{mode}/{period}/{file_name}", response_class=HTMLResponse)
async def read_items(symbol: str, mode: str, period: str, file_name: str):
    file_path = (
        Path(config_path).parent.parent
        / "fig_data"
        / f"{symbol}/{mode}/{period}/{file_name}"
    )
    print(file_path)
    with open(file_path, "rb") as f:
        data = f.read()
    return data


@app.get("/")
def main():
    return {"Hello": "World"}


if __name__ == "__main__":
    print("run fast_api")
    uvicorn.run("fast_api_demo:app", host="0.0.0.0", port=2197)
