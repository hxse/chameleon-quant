# chameleon-quant
  * docker run -d -p 2197:8080 -v ~/chameleon-quant/csv:/src/csv -v ~/chameleon-quant/strategy:/src/strategy  -e PYTHONUNBUFFERED=1 --name chameleon-quant --restart=always :latest
