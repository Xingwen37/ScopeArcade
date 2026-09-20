set_device -device_version B GW5AST-LV138PG484AC1/I0
set_option -verilog_std sysv2017
add_file uart_rx.sv
add_file uart_tx.sv
add_file renderer.sv
add_file board.cst
add_file timing.sdc
set_option -top_module renderer
set_option -output_base_name racer_xy
run all
