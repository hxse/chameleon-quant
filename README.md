# chameleon-quant
  * `docker compose up`
    * on windows `docker compose -f .\compose-win.yml up`
  * clear useless images
    * `docker image prune -a`
  * `docker pull hxse/chameleon-quant:latest`
  * `docker run -d -v ~/chameleon-quant/csv:/app/src/csv -v ~/chameleon-quant/fig_data:/app/src/fig_data -v ~/chameleon-quant/strategy:/app/src/strategy  -e PYTHONUNBUFFERED=1 --name chameleon-quant --restart=always hxse/chameleon-quant:latest`
# chameleon-fastapi
  * `docker pull hxse/chameleon-fastapi:latest`
  * `docker run -d -p 2197:2197 -v ~/chameleon-quant/csv:/app/src/csv -v ~/chameleon-quant/fig_data:/app/src/fig_data -v ~/chameleon-quant/strategy:/app/src/strategy  -e PYTHONUNBUFFERED=1 --name chameleon-fastapi --restart=always hxse/chameleon-fastapi:latest`
