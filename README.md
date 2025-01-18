# chameleon-quant
  * `docker compose up`
    * on windows `docker compose -f .\compose-win.yml up`
  * `docker pull hxse/chameleon-quant:latest`
  * `docker run -d -v ~/chameleon-quant/csv:/app/src/csv -v ~/chameleon-quant/fig_data:/app/src/fig_data -v ~/chameleon-quant/strategy:/app/src/strategy  -e PYTHONUNBUFFERED=1 --name chameleon-quant --restart=always hxse/chameleon-quant:latest`
