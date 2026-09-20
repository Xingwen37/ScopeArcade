// Private double-buffered line transport for the XY recruitment demo.
module renderer #(parameter integer BAUD=1000000,parameter integer WATCHDOG_CYCLES=50000000)(
 input clk,input uart_rx_pin,output uart_tx_pin,
 output reg [13:0] dac_a=8192,output [13:4] dac_b,output [2:0] b_low,
 output reg clk_a=0,clk_b=0,wrt_a=0,wrt_b=0,output pa_en,output reg aux_trigger=0);
 assign pa_en=0;assign b_low=0;
 reg [13:0] b_word=8192;assign dac_b=b_word[13:4];
 wire [7:0] rx_data;wire rx_valid,rx_error,tx_ready;
 reg [7:0] tx_data=0;reg tx_valid=0;
 uart_rx #(.BAUD(BAUD)) receiver(clk,uart_rx_pin,rx_data,rx_valid,rx_error);
 uart_tx #(.BAUD(BAUD)) sender(clk,tx_data,tx_valid,tx_ready,uart_tx_pin);
 reg [31:0] memory[0:255];
 reg display_bank=0,pending=0,live=0;
 reg [6:0] line_count=0,pending_count=0,received_count=0;
 reg [7:0] seq_rx=0,pending_seq=0;
 reg [3:0] state=0;
 reg [6:0] write_index=0;
 reg [1:0] byte_index=0;
 reg [31:0] assembly=0;
 reg [15:0] crc=16'hffff;
 reg [7:0] crc_hi=0;
 reg [19:0] timeout_count=0;
 reg [25:0] stale=0;
 reg [7:0] tick=0;
 reg [12:0] slot_cycle=0;
 reg [6:0] sample_index=0,line_index=0;
 reg [31:0] line=0;
 integer fraction,x0,y0,x1,y1,x_interp,y_interp;
 function [15:0] crc_byte;
 input [15:0] prior;input [7:0] value;
 integer i;reg [15:0] c;
 begin c=prior^{value,8'b0};for(i=0;i<8;i=i+1)c=c[15]?(c<<1)^16'h1021:c<<1;crc_byte=c;end
 endfunction
 always @(posedge clk)begin
  tx_valid<=0;
  if(stale<WATCHDOG_CYCLES)stale<=stale+1'b1;else live<=0;
  if(state!=0)begin
   timeout_count<=timeout_count+1'b1;
   if(timeout_count==499999)begin state<=0;timeout_count<=0;end
  end else timeout_count<=0;
  if(rx_error)state<=0;
  if(rx_valid && !pending)begin
   timeout_count<=0;
   case(state)
    0:if(rx_data==8'ha5)state<=1;
    1:if(rx_data==8'h5a)state<=2;else if(rx_data!=8'ha5)state<=0;
    2:begin seq_rx<=rx_data;crc<=crc_byte(16'hffff,rx_data);state<=3;end
    3:begin
     if(rx_data>0 && rx_data<=72)begin received_count<=rx_data;write_index<=0;byte_index<=0;crc<=crc_byte(crc,rx_data);state<=4;end
     else state<=0;
    end
    4:begin
     crc<=crc_byte(crc,rx_data);assembly<={assembly[23:0],rx_data};byte_index<=byte_index+1'b1;
     if(byte_index==3)begin
      memory[{!display_bank,write_index}]<={assembly[23:0],rx_data};
      if(write_index==received_count-1)state<=5;else write_index<=write_index+1'b1;
     end
    end
    5:begin crc_hi<=rx_data;state<=6;end
    6:begin
     state<=0;
     if({crc_hi,rx_data}==crc)begin pending<=1;pending_count<=received_count;pending_seq<=seq_rx;end
    end
    default:state<=0;
   endcase
  end
  if(slot_cycle==6399)begin
   slot_cycle<=0;
   if(line_index==71)begin
    line_index<=0;
    if(pending)begin
     display_bank<=!display_bank;line_count<=pending_count;pending<=0;live<=1;stale<=0;
     if(tx_ready)begin tx_data<=pending_seq;tx_valid<=1;end
    end
   end else line_index<=line_index+1'b1;
  end else slot_cycle<=slot_cycle+1'b1;
  // 1us E14 trigger at2us; SDG adds12us delay and76us visible window.
  if(slot_cycle==100)aux_trigger<=live && line_index<line_count;
  if(slot_cycle==150)aux_trigger<=0;
  if(tick==49)begin tick<=0;sample_index<=sample_index+1'b1;end
  else tick<=tick+1'b1;
  if(live && line_index<line_count)line<=memory[{display_bank,line_index}];
  else line<=32'h80808080;
  if(tick==2)begin dac_a<=14'd6144+{x_interp[7:0],4'b0};b_word<=14'd6144+{y_interp[7:0],4'b0};end
  if(tick==12)begin clk_a<=1;clk_b<=1;end
  if(tick==19)begin wrt_a<=1;wrt_b<=1;end
  if(tick==25)begin clk_a<=0;clk_b<=0;end
  if(tick==31)begin wrt_a<=0;wrt_b<=0;end
 end
 always @*begin
  x0={24'b0,line[31:24]};y0={24'b0,line[23:16]};x1={24'b0,line[15:8]};y1={24'b0,line[7:0]};
  if(sample_index<20)fraction=0;else if(sample_index>84)fraction=64;else fraction=sample_index-20;
  x_interp=x0+(((x1-x0)*fraction)>>>6);y_interp=y0+(((y1-y0)*fraction)>>>6);
 end
endmodule
