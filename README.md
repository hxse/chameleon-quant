# chameleon-quant
  * `docker run -d -p 2197:8080 -v ~/chameleon-quant/csv:/app/src/csv -v ~/chameleon-quant/strategy:/app/src/strategy  -e PYTHONUNBUFFERED=1 --name chameleon-quant --restart=always hxse/chameleon-quant:latest`
