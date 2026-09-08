# imsic

Incoming MSI controller for the RISC-V Advanced Interrupt Architecture: one per hart,
receiving message-signalled interrupts and presenting them to the core over CSRs.

![maturity](https://img.shields.io/badge/maturity-planned-lightgrey) ![license](https://img.shields.io/badge/license-MulanPSL--2.0-blue)

Part of the [Tape-Out](https://github.com/Tape-Out) IP library: Bluespec IP over the
bus-neutral contracts in [`hwcore`](https://github.com/Tape-Out/hwcore), assembled by
[`loom`](https://github.com/Tape-Out/loom). Maturity runs `planned` -> `simulated` ->
`fpga-proven` -> `asic-ready` -> `silicon-proven`.

## Why this is its own repository

An IMSIC shares no hardware with a PLIC. A PLIC is one device for the whole chip, its
state lives on the bus, and most of its area is a priority arbitration tree. An IMSIC is
one instance per hart, its state is reached through CSRs, and its entire memory-mapped
surface is two write-only registers in a 4 KiB page. Different body, different count,
different access path, so it does not belong in [`plic`](https://github.com/Tape-Out/plic).

It is separate from [`hart`](https://github.com/Tape-Out/hart) for a different reason:
in Bluespec a repository boundary is not a synthesis boundary. A module without
`(* synthesize *)` is inlined wherever it is used, so `hart` pays nothing for depending
on this package, while anyone pairing it with their own core can still take it alone.

## Scope

Interrupt files hold `eip` and `eie` bit arrays sized 63 to 2047 identities, plus
`eithreshold` and `eidelivery`. A hart gets at least two files, machine and supervisor,
and one more per guest when the hypervisor extension is present. Only `seteipnum_le` and
`seteipnum_be` are memory-mapped; everything else is reached through `miselect`/`mireg`
and the `*topei` registers.

The specification is the ratified
[RISC-V Advanced Interrupt Architecture v1.0](https://docs.riscv.org/reference/aia/v1.0/IMSIC.html).

## License

Mulan PSL v2.
