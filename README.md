# imsic

Incoming MSI controller of the RISC-V Advanced Interrupt Architecture, one per hart.

![maturity](https://img.shields.io/badge/maturity-simulated-yellow) ![license](https://img.shields.io/badge/license-MulanPSL--2.0-blue)

Part of the [Tape-Out](https://github.com/Tape-Out) IP library: Bluespec IP over the
bus-neutral contracts in [`hwcore`](https://github.com/Tape-Out/hwcore), assembled by
[`xirang`](https://github.com/Tape-Out/xirang). Maturity runs `planned` -> `simulated` ->
`fpga-proven` -> `asic-ready` -> `silicon-proven`.

## Status

Simulated. The machine-level interrupt file works on its own in simulation; connecting it to [`hart`](https://github.com/Tape-Out/hart) is still to come.

The IP has two sides:

| Port | Who uses it | Content |
| :-- | :-- | :-- |
| `regs` | the bus, one 4 KiB page | `seteipnum_le` at 0x000 sets the pending bit of the identity written; `seteipnum_be` at 0x004 is ignored on this little-endian library; every other word reads zero |
| `hart.csr` | the core, addressed by the value of `miselect` | `eidelivery` (0x70), `eithreshold` (0x72), `eip0`–`eip63` (0x80–0xBF), `eie0`–`eie63` (0xC0–0xFF) |
| `hart.topei`, `hart.claim` | the core's `mtopei` | the lowest pending and enabled identity below the threshold, in the `mtopei` format; writing `mtopei` claims the identity reported in the same cycle |
| `hart.meip` | the core's `mip.MEIP` | high when delivery is enabled and there is an identity to report |

Behaviour follows the AIA chapter 3:

- Lower identity numbers have higher priority.
- A write of an identity that is not implemented is ignored, and so are partial or misaligned accesses to the page, which also answer with an error.
- `eidelivery` only accepts 0 and 1.
- Bit 0 of `eip0` and `eie0` reads zero.

When a claim and a new MSI land in the same cycle, the claim clears the identity reported at the start of the cycle and the new MSI is recorded after it, so an MSI that arrives for the identity being claimed is not lost. The specification leaves this ordering open.

The module is parameterised by the number of identities, checked at compile time to be one less than a multiple of 64 between 63 and 2047. The instance xirang builds has 63.

Not implemented yet:

- supervisor-level and guest interrupt files;
- delivery from a PLIC or APLIC through `eidelivery`;
- major interrupt priorities and `mtopi`.

## License

Mulan PSL v2.
