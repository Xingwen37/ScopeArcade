// SPDX-License-Identifier: LicenseRef-GWFlow-Personal-NonCommercial-1.0
module uart_rx #(
    parameter integer CLOCK_HZ = 50_000_000,
    parameter integer BAUD = 115_200
) (
    input  logic       clk,
    input  logic       rx,
    output logic [7:0] data = '0,
    output logic       valid = 1'b0,
    output logic       framing_error = 1'b0
);
    localparam integer CLKS_PER_BIT = CLOCK_HZ / BAUD;
    localparam integer HALF_BIT = CLKS_PER_BIT / 2;
    localparam integer COUNT_WIDTH = $clog2(CLKS_PER_BIT + 1);
    typedef enum logic [1:0] {IDLE, START, DATA, STOP} state_t;

    (* ASYNC_REG = "TRUE" *) logic rx_meta = 1'b1;
    (* ASYNC_REG = "TRUE" *) logic rx_sync = 1'b1;
    state_t state = IDLE;
    logic [COUNT_WIDTH-1:0] countdown = '0;
    logic [2:0] bit_index = '0;
    logic [7:0] shift = '0;

    always_ff @(posedge clk) begin
        rx_meta <= rx;
        rx_sync <= rx_meta;
        valid <= 1'b0;
        framing_error <= 1'b0;

        case (state)
            IDLE: begin
                countdown <= '0;
                bit_index <= '0;
                if (!rx_sync) begin
                    countdown <= HALF_BIT - 1;
                    state <= START;
                end
            end
            START: begin
                if (countdown != 0)
                    countdown <= countdown - 1'b1;
                else if (!rx_sync) begin
                    countdown <= CLKS_PER_BIT - 1;
                    bit_index <= '0;
                    state <= DATA;
                end else begin
                    state <= IDLE;
                end
            end
            DATA: begin
                if (countdown != 0)
                    countdown <= countdown - 1'b1;
                else begin
                    shift[bit_index] <= rx_sync;
                    countdown <= CLKS_PER_BIT - 1;
                    if (bit_index == 3'd7)
                        state <= STOP;
                    else
                        bit_index <= bit_index + 1'b1;
                end
            end
            STOP: begin
                if (countdown != 0)
                    countdown <= countdown - 1'b1;
                else begin
                    if (rx_sync) begin
                        data <= shift;
                        valid <= 1'b1;
                    end else begin
                        framing_error <= 1'b1;
                    end
                    state <= IDLE;
                end
            end
            default: state <= IDLE;
        endcase
    end

`ifdef FORMAL
    logic past_valid = 1'b0;
    always_ff @(posedge clk) begin
        past_valid <= 1'b1;
        assert(bit_index <= 3'd7);
        assert(countdown < CLKS_PER_BIT);
        assert(!(valid && framing_error));
        if (past_valid && $past(valid))
            assert(!valid);
        if (valid)
            assert($past(state) == STOP && $past(countdown) == 0 && $past(rx_sync));
        if (framing_error)
            assert($past(state) == STOP && $past(countdown) == 0 && !$past(rx_sync));
    end
`endif
endmodule
