MEMORY
{
  /* Keep 0x70000..0x7FFFF exclusively for RMK's 16 storage sectors. */
  FLASH : ORIGIN = 0x00000000, LENGTH = 448K
  RAM : ORIGIN = 0x20000000, LENGTH = 64K

  /* These values correspond to the nRF52832 WITH Adafruit nRF52 bootloader */
  /* FLASH : ORIGIN = 0x00001000, LENGTH = 508K */
  /* RAM : ORIGIN = 0x20000008, LENGTH = 63K */
}
