xcopy /y "D:\my_repo\chameleon-quant\src\plot\bokeh_plot.py" "D:\my_repo\chameleon-fastapi\src\plot"
xcopy /y "D:\my_repo\chameleon-quant\src\plot\bokeh_server.py" "D:\my_repo\chameleon-fastapi\src\plot"
D: && cd "D:\my_repo\chameleon-fastapi"
".\push git.bat"
