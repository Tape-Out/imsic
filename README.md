# imsic

Incoming MSI controller for the RISC-V Advanced Interrupt Architecture: one per hart,
receiving message-signalled interrupts and presenting them to the core over CSRs.

![maturity](https://img.shields.io/badge/maturity-planned-lightgrey) ![license](https://img.shields.io/badge/license-MulanPSL--2.0-blue)

Part of the [Tape-Out](https://github.com/Tape-Out) IP library: Bluespec IP over the
bus-neutral contracts in [`hwcore`](https://github.com/Tape-Out/hwcore), assembled by
[`loom`](https://github.com/Tape-Out/loom). Maturity runs `planned` -> `simulated` ->
`fpga-proven` -> `asic-ready` -> `silicon-proven`.

## Scope

Interrupt files hold `eip` and `eie` bit arrays sized 63 to 2047 identities, plus
`eithreshold` and `eidelivery`. A hart gets at least two files, machine and supervisor,
and one more per guest when the hypervisor extension is present. Only `seteipnum_le` and
`seteipnum_be` are memory-mapped; everything else is reached through `miselect`/`mireg`
and the `*topei` registers.

The specification is the ratified
[RISC-V Advanced Interrupt Architecture v1.0](https://docs.riscv.org/reference/aia/v1.0/IMSIC.html).

## Status

Planned. The entry in [`index`](https://github.com/Tape-Out/index) tracks what lands when.

## License

Mulan PSL v2.
