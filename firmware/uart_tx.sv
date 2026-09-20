// SPDX-License-Identifier: LicenseRef-GWFlow-Personal-NonCommercial-1.0
module uart_tx #(
    parameter integer CLOCK_HZ = 50_000_000,
    parameter integer BAUD = 115_200
) (
    input  logic       clk,
    input  logic [7:0] data,
    input  logic       valid,
    output logic       ready,
    output logic       tx = 1'b1
);
    localparam integer CLKS_PER_BIT = CLOCK_HZ / BAUD;
    localparam integer COUNT_WIDTH = $clog2(CLKS_PER_BIT + 1);
    typedef enum logic [1:0] {IDLE, START, DATA, STOP} state_t;
    state_t state = IDLE;
    logic [COUNT_WIDTH-1:0] clock_count = '0;
    logic [2:0] bit_index = '0;
    logic [7:0] latched = '0;

    assign ready = (state == IDLE);

    always_ff @(posedge clk) begin
        case (state)
            IDLE: begin
                tx <= 1'b1;
                clock_count <= '0;
                bit_index <= '0;
                if (valid) begin
                    latched <= data;
                    tx <= 1'b0;
                    state <= START;
                end
            end
            START: begin
                tx <= 1'b0;
                if (clock_count == CLKS_PER_BIT - 1) begin
                    clock_count <= '0;
                    tx <= latched[0];
                    state <= DATA;
                end else clock_count <= clock_count + 1'b1;
            end
            DATA: begin
                tx <= latched[bit_index];
                if (clock_count == CLKS_PER_BIT - 1) begin
                    clock_count <= '0;
                    if (bit_index == 3'd7) begin
                        tx <= 1'b1;
                        state <= STOP;
                    end else begin
                        bit_index <= bit_index + 1'b1;
                        tx <= latched[bit_index + 1'b1];
                    end
                end else clock_count <= clock_count + 1'b1;
            end
            STOP: begin
                tx <= 1'b1;
                if (clock_count == CLKS_PER_BIT - 1) begin
                    clock_count <= '0;
                    state <= IDLE;
                end else clock_count <= clock_count + 1'b1;
            end
            default: state <= IDLE;
        endcase
    end
endmodule
