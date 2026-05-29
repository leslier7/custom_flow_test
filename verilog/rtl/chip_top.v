// Stage 3: IO pad ring wrapping the hardened proj2_Proj2XcelChip macro.
// All logic lives inside the Stage 2 macro; this module is purely structural.
`ifndef CHIP_TOP_V
`define CHIP_TOP_V

module chip_top (
  inout wire clk,
  inout wire reset,
  inout wire cs,
  inout wire sclk,
  inout wire mosi,
  inout wire miso,
  inout wire debug_mode,
  inout wire debug_out,
  inout wire gp0,
  inout wire gp1,
  inout wire clk_out
);

  wire clk_core, reset_core, cs_core, sclk_core, mosi_core;
  wire miso_core, debug_mode_core, debug_out_core;
  wire gp0_core, gp1_core, clk_out_core;

  // --- Input pads ---

  sky130_fd_io__top_gpio_ovtv2 clk_io (
    .PAD(clk), .IN(clk_core), .OUT(1'b0),
    .OE_N(1'b1), .INP_DIS(1'b0), .DM(3'b001),
    .HLD_H_N(1'b1), .HLD_OVR(1'b0), .SLOW(1'b0), .SLEW_CTL(2'b00),
    .VTRIP_SEL(1'b0), .HYS_TRIM(1'b0), .IB_MODE_SEL(2'b00), .VINREF(1'b0),
    .ENABLE_H(1'b1), .ENABLE_INP_H(1'b1), .ENABLE_VDDA_H(1'b0),
    .ENABLE_VDDIO(1'b1), .ENABLE_VSWITCH_H(1'b0),
    .ANALOG_EN(1'b0), .ANALOG_SEL(1'b0), .ANALOG_POL(1'b0),
    .AMUXBUS_A(), .AMUXBUS_B(),
    .PAD_A_NOESD_H(), .PAD_A_ESD_0_H(), .PAD_A_ESD_1_H(),
    .IN_H(), .TIE_HI_ESD(), .TIE_LO_ESD()
  );

  sky130_fd_io__top_gpio_ovtv2 reset_io (
    .PAD(reset), .IN(reset_core), .OUT(1'b0),
    .OE_N(1'b1), .INP_DIS(1'b0), .DM(3'b001),
    .HLD_H_N(1'b1), .HLD_OVR(1'b0), .SLOW(1'b0), .SLEW_CTL(2'b00),
    .VTRIP_SEL(1'b0), .HYS_TRIM(1'b0), .IB_MODE_SEL(2'b00), .VINREF(1'b0),
    .ENABLE_H(1'b1), .ENABLE_INP_H(1'b1), .ENABLE_VDDA_H(1'b0),
    .ENABLE_VDDIO(1'b1), .ENABLE_VSWITCH_H(1'b0),
    .ANALOG_EN(1'b0), .ANALOG_SEL(1'b0), .ANALOG_POL(1'b0),
    .AMUXBUS_A(), .AMUXBUS_B(),
    .PAD_A_NOESD_H(), .PAD_A_ESD_0_H(), .PAD_A_ESD_1_H(),
    .IN_H(), .TIE_HI_ESD(), .TIE_LO_ESD()
  );

  sky130_fd_io__top_gpio_ovtv2 cs_io (
    .PAD(cs), .IN(cs_core), .OUT(1'b0),
    .OE_N(1'b1), .INP_DIS(1'b0), .DM(3'b001),
    .HLD_H_N(1'b1), .HLD_OVR(1'b0), .SLOW(1'b0), .SLEW_CTL(2'b00),
    .VTRIP_SEL(1'b0), .HYS_TRIM(1'b0), .IB_MODE_SEL(2'b00), .VINREF(1'b0),
    .ENABLE_H(1'b1), .ENABLE_INP_H(1'b1), .ENABLE_VDDA_H(1'b0),
    .ENABLE_VDDIO(1'b1), .ENABLE_VSWITCH_H(1'b0),
    .ANALOG_EN(1'b0), .ANALOG_SEL(1'b0), .ANALOG_POL(1'b0),
    .AMUXBUS_A(), .AMUXBUS_B(),
    .PAD_A_NOESD_H(), .PAD_A_ESD_0_H(), .PAD_A_ESD_1_H(),
    .IN_H(), .TIE_HI_ESD(), .TIE_LO_ESD()
  );

  sky130_fd_io__top_gpio_ovtv2 sclk_io (
    .PAD(sclk), .IN(sclk_core), .OUT(1'b0),
    .OE_N(1'b1), .INP_DIS(1'b0), .DM(3'b001),
    .HLD_H_N(1'b1), .HLD_OVR(1'b0), .SLOW(1'b0), .SLEW_CTL(2'b00),
    .VTRIP_SEL(1'b0), .HYS_TRIM(1'b0), .IB_MODE_SEL(2'b00), .VINREF(1'b0),
    .ENABLE_H(1'b1), .ENABLE_INP_H(1'b1), .ENABLE_VDDA_H(1'b0),
    .ENABLE_VDDIO(1'b1), .ENABLE_VSWITCH_H(1'b0),
    .ANALOG_EN(1'b0), .ANALOG_SEL(1'b0), .ANALOG_POL(1'b0),
    .AMUXBUS_A(), .AMUXBUS_B(),
    .PAD_A_NOESD_H(), .PAD_A_ESD_0_H(), .PAD_A_ESD_1_H(),
    .IN_H(), .TIE_HI_ESD(), .TIE_LO_ESD()
  );

  sky130_fd_io__top_gpio_ovtv2 mosi_io (
    .PAD(mosi), .IN(mosi_core), .OUT(1'b0),
    .OE_N(1'b1), .INP_DIS(1'b0), .DM(3'b001),
    .HLD_H_N(1'b1), .HLD_OVR(1'b0), .SLOW(1'b0), .SLEW_CTL(2'b00),
    .VTRIP_SEL(1'b0), .HYS_TRIM(1'b0), .IB_MODE_SEL(2'b00), .VINREF(1'b0),
    .ENABLE_H(1'b1), .ENABLE_INP_H(1'b1), .ENABLE_VDDA_H(1'b0),
    .ENABLE_VDDIO(1'b1), .ENABLE_VSWITCH_H(1'b0),
    .ANALOG_EN(1'b0), .ANALOG_SEL(1'b0), .ANALOG_POL(1'b0),
    .AMUXBUS_A(), .AMUXBUS_B(),
    .PAD_A_NOESD_H(), .PAD_A_ESD_0_H(), .PAD_A_ESD_1_H(),
    .IN_H(), .TIE_HI_ESD(), .TIE_LO_ESD()
  );

  sky130_fd_io__top_gpio_ovtv2 debug_mode_io (
    .PAD(debug_mode), .IN(debug_mode_core), .OUT(1'b0),
    .OE_N(1'b1), .INP_DIS(1'b0), .DM(3'b001),
    .HLD_H_N(1'b1), .HLD_OVR(1'b0), .SLOW(1'b0), .SLEW_CTL(2'b00),
    .VTRIP_SEL(1'b0), .HYS_TRIM(1'b0), .IB_MODE_SEL(2'b00), .VINREF(1'b0),
    .ENABLE_H(1'b1), .ENABLE_INP_H(1'b1), .ENABLE_VDDA_H(1'b0),
    .ENABLE_VDDIO(1'b1), .ENABLE_VSWITCH_H(1'b0),
    .ANALOG_EN(1'b0), .ANALOG_SEL(1'b0), .ANALOG_POL(1'b0),
    .AMUXBUS_A(), .AMUXBUS_B(),
    .PAD_A_NOESD_H(), .PAD_A_ESD_0_H(), .PAD_A_ESD_1_H(),
    .IN_H(), .TIE_HI_ESD(), .TIE_LO_ESD()
  );

  sky130_fd_io__top_gpio_ovtv2 gp0_io (
    .PAD(gp0), .IN(gp0_core), .OUT(1'b0),
    .OE_N(1'b1), .INP_DIS(1'b0), .DM(3'b001),
    .HLD_H_N(1'b1), .HLD_OVR(1'b0), .SLOW(1'b0), .SLEW_CTL(2'b00),
    .VTRIP_SEL(1'b0), .HYS_TRIM(1'b0), .IB_MODE_SEL(2'b00), .VINREF(1'b0),
    .ENABLE_H(1'b1), .ENABLE_INP_H(1'b1), .ENABLE_VDDA_H(1'b0),
    .ENABLE_VDDIO(1'b1), .ENABLE_VSWITCH_H(1'b0),
    .ANALOG_EN(1'b0), .ANALOG_SEL(1'b0), .ANALOG_POL(1'b0),
    .AMUXBUS_A(), .AMUXBUS_B(),
    .PAD_A_NOESD_H(), .PAD_A_ESD_0_H(), .PAD_A_ESD_1_H(),
    .IN_H(), .TIE_HI_ESD(), .TIE_LO_ESD()
  );

  sky130_fd_io__top_gpio_ovtv2 gp1_io (
    .PAD(gp1), .IN(gp1_core), .OUT(1'b0),
    .OE_N(1'b1), .INP_DIS(1'b0), .DM(3'b001),
    .HLD_H_N(1'b1), .HLD_OVR(1'b0), .SLOW(1'b0), .SLEW_CTL(2'b00),
    .VTRIP_SEL(1'b0), .HYS_TRIM(1'b0), .IB_MODE_SEL(2'b00), .VINREF(1'b0),
    .ENABLE_H(1'b1), .ENABLE_INP_H(1'b1), .ENABLE_VDDA_H(1'b0),
    .ENABLE_VDDIO(1'b1), .ENABLE_VSWITCH_H(1'b0),
    .ANALOG_EN(1'b0), .ANALOG_SEL(1'b0), .ANALOG_POL(1'b0),
    .AMUXBUS_A(), .AMUXBUS_B(),
    .PAD_A_NOESD_H(), .PAD_A_ESD_0_H(), .PAD_A_ESD_1_H(),
    .IN_H(), .TIE_HI_ESD(), .TIE_LO_ESD()
  );

  // --- Output pads ---

  sky130_fd_io__top_gpio_ovtv2 miso_io (
    .PAD(miso), .OUT(miso_core), .IN(),
    .OE_N(1'b0), .INP_DIS(1'b1), .DM(3'b110),
    .HLD_H_N(1'b1), .HLD_OVR(1'b0), .SLOW(1'b0), .SLEW_CTL(2'b00),
    .VTRIP_SEL(1'b0), .HYS_TRIM(1'b0), .IB_MODE_SEL(2'b00), .VINREF(1'b0),
    .ENABLE_H(1'b1), .ENABLE_INP_H(1'b0), .ENABLE_VDDA_H(1'b0),
    .ENABLE_VDDIO(1'b1), .ENABLE_VSWITCH_H(1'b0),
    .ANALOG_EN(1'b0), .ANALOG_SEL(1'b0), .ANALOG_POL(1'b0),
    .AMUXBUS_A(), .AMUXBUS_B(),
    .PAD_A_NOESD_H(), .PAD_A_ESD_0_H(), .PAD_A_ESD_1_H(),
    .IN_H(), .TIE_HI_ESD(), .TIE_LO_ESD()
  );

  sky130_fd_io__top_gpio_ovtv2 debug_out_io (
    .PAD(debug_out), .OUT(debug_out_core), .IN(),
    .OE_N(1'b0), .INP_DIS(1'b1), .DM(3'b110),
    .HLD_H_N(1'b1), .HLD_OVR(1'b0), .SLOW(1'b0), .SLEW_CTL(2'b00),
    .VTRIP_SEL(1'b0), .HYS_TRIM(1'b0), .IB_MODE_SEL(2'b00), .VINREF(1'b0),
    .ENABLE_H(1'b1), .ENABLE_INP_H(1'b0), .ENABLE_VDDA_H(1'b0),
    .ENABLE_VDDIO(1'b1), .ENABLE_VSWITCH_H(1'b0),
    .ANALOG_EN(1'b0), .ANALOG_SEL(1'b0), .ANALOG_POL(1'b0),
    .AMUXBUS_A(), .AMUXBUS_B(),
    .PAD_A_NOESD_H(), .PAD_A_ESD_0_H(), .PAD_A_ESD_1_H(),
    .IN_H(), .TIE_HI_ESD(), .TIE_LO_ESD()
  );

  sky130_fd_io__top_gpio_ovtv2 clk_out_io (
    .PAD(clk_out), .OUT(clk_out_core), .IN(),
    .OE_N(1'b0), .INP_DIS(1'b1), .DM(3'b110),
    .HLD_H_N(1'b1), .HLD_OVR(1'b0), .SLOW(1'b0), .SLEW_CTL(2'b00),
    .VTRIP_SEL(1'b0), .HYS_TRIM(1'b0), .IB_MODE_SEL(2'b00), .VINREF(1'b0),
    .ENABLE_H(1'b1), .ENABLE_INP_H(1'b0), .ENABLE_VDDA_H(1'b0),
    .ENABLE_VDDIO(1'b1), .ENABLE_VSWITCH_H(1'b0),
    .ANALOG_EN(1'b0), .ANALOG_SEL(1'b0), .ANALOG_POL(1'b0),
    .AMUXBUS_A(), .AMUXBUS_B(),
    .PAD_A_NOESD_H(), .PAD_A_ESD_0_H(), .PAD_A_ESD_1_H(),
    .IN_H(), .TIE_HI_ESD(), .TIE_LO_ESD()
  );

  // --- Hardened chip core macro ---

  proj2_Proj2XcelChip core (
    .clk(clk_core),
    .reset(reset_core),
    .cs(cs_core),
    .sclk(sclk_core),
    .mosi(mosi_core),
    .miso(miso_core),
    .debug_mode(debug_mode_core),
    .debug_out(debug_out_core),
    .gp0(gp0_core),
    .gp1(gp1_core),
    .clk_out(clk_out_core)
  );

endmodule

`endif
