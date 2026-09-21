"""imsic 的行为测试台：测试台直接驱中断文件那一页与给核的 CSR 口，不带核。判据见 notes/规范对照/imsic.md。

一，控制口：写号置位；0、64、1000 不是实现的号，不改状态；最大号 63 收得下；大端口忽略；
    非整字、不对齐的访问答错不改状态；整页读恒 0。
二，号小者胜；阈值 P 让 P 与更大的号不算。
三，eidelivery 只管 meip，不管 topei；WARL 只收 0 与 1（在 0 时写 7，存布尔的实现照收就会变成 1）。
四，领取清的是这一拍报的号；同拍新到的号在清之后置上，同号同拍到达不丢。
五，保留的选择号读 0 写忽略；eip0 第 0 位与 63 个号之外的 eip2 恒 0。
"""
import json
import pathlib
import sys

out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
out.mkdir(parents=True, exist_ok=True)
cfg = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
label = cfg.get("label", "")

verdict = ("writes to seteipnum_le set only implemented identities, other accesses leave state alone and read zero, "
           "the lowest pending and enabled identity below the threshold is reported, eidelivery gates only meip and "
           "keeps illegal values out, a claim clears the identity reported in the same cycle without losing one that "
           "arrives with it, and reserved selects and bits read zero")

TEMPLATE = r'''package Imsic@L@Tb;

// 由 htest/mkimsictb.py 生成，勿手改

import StmtFSM::*;
import RegIf::*;
import Imsic::*;

(* synthesize *)
module mkImsic@L@Tb(Empty);
  ImsicIfc#(12, 32) d <- mkImsic(ImsicCfg { none: ? });

  Reg#(Bit#(32)) rv      <- mkReg(0);
  Reg#(Bool)     lastErr <- mkReg(False);
  Reg#(Bool)     bad     <- mkReg(False);
  Reg#(Bit#(32)) cyc     <- mkReg(0);

  function Action mm(Bit#(12) a, Bit#(32) v, Bit#(4) s) = action
    let x <- d.regs.access(RegReq { addr: a, write: True, wdata: v, wstrb: s });
    lastErr <= x.err;
  endaction;
  function Action mmr(Bit#(12) a) = action
    let x <- d.regs.access(RegReq { addr: a, write: False, wdata: 0, wstrb: 4'hF });
    rv <= x.rdata;
    lastErr <= x.err;
  endaction;
  function Action cw(Bit#(8) sel, Bit#(32) v) = action
    let x <- d.hart.csr.access(RegReq { addr: sel, write: True, wdata: v, wstrb: 4'hF });
  endaction;
  function Action cr(Bit#(8) sel) = action
    let x <- d.hart.csr.access(RegReq { addr: sel, write: False, wdata: 0, wstrb: 4'hF });
    rv <= x.rdata;
  endaction;
  function Action chk(String what, Bit#(32) got, Bit#(32) want) = action
    if (got != want) begin
      $display("FAIL %s: got %08h want %08h", what, got, want);
      bad <= True;
    end
  endaction;

  Stmt test = seq
    mm(12'h000, 5, 4'hF);
    cr(8'h80);  chk("seteipnum_le 5 sets bit 5 of eip0", rv, 32'h20);
    mm(12'h000, 0, 4'hF);
    mm(12'h000, 64, 4'hF);
    mm(12'h000, 1000, 4'hF);
    cr(8'h80);  chk("identities 0, 64 and 1000 are not implemented and leave eip0 alone", rv, 32'h20);
    cr(8'h81);  chk("eip1 after the invalid writes", rv, 0);
    mm(12'h000, 63, 4'hF);
    cr(8'h81);  chk("identity 63, the largest implemented, is accepted", rv, 32'h8000_0000);
    cw(8'h81, 0);
    mm(12'h004, 7, 4'hF);
    cr(8'h80);  chk("seteipnum_be is ignored on a little-endian system", rv, 32'h20);
    mm(12'h000, 9, 4'h1);
    chk("a one-byte write to seteipnum_le answers an error", zeroExtend(pack(lastErr)), 1);
    mm(12'h001, 9, 4'hF);
    chk("a misaligned write answers an error", zeroExtend(pack(lastErr)), 1);
    cr(8'h80);  chk("the partial and misaligned writes leave eip0 alone", rv, 32'h20);
    mmr(12'h000); chk("seteipnum_le reads zero", rv, 0);
    mmr(12'h004); chk("seteipnum_be reads zero", rv, 0);
    mmr(12'h008); chk("a reserved word reads zero", rv, 0);
    chk("a reserved word reads without an error", zeroExtend(pack(lastErr)), 0);

    cw(8'hC0, 32'h28);
    mm(12'h000, 3, 4'hF);
    chk("identities 3 and 5 pending and enabled report 3", d.hart.topei, 32'h0003_0003);
    cw(8'h72, 3);
    chk("eithreshold 3 hides 3 and 5", d.hart.topei, 0);
    cw(8'h72, 4);
    chk("eithreshold 4 lets 3 through", d.hart.topei, 32'h0003_0003);
    cw(8'h72, 0);

    cw(8'h70, 0);
    chk("eidelivery 0 holds meip low", zeroExtend(pack(d.hart.meip)), 0);
    chk("eidelivery does not affect topei", d.hart.topei, 32'h0003_0003);
    cw(8'h70, 7);
    cr(8'h70);  chk("eidelivery keeps 0 when 7 is written", rv, 0);
    cw(8'h70, 1);
    chk("eidelivery 1 raises meip with 3 pending", zeroExtend(pack(d.hart.meip)), 1);

    cw(8'hC0, 32'h2A);
    action d.hart.claim; mm(12'h000, 1, 4'hF); endaction
    cr(8'h80);  chk("claiming 3 while 1 arrives clears only 3", rv, 32'h22);
    chk("after the claim 1 is reported", d.hart.topei, 32'h0001_0001);
    action d.hart.claim; mm(12'h000, 1, 4'hF); endaction
    cr(8'h80);  chk("claiming 1 while 1 arrives again keeps it pending", rv, 32'h22);
    d.hart.claim;
    d.hart.claim;
    cr(8'h80);  chk("two more claims clear 1 and then 5", rv, 0);
    chk("nothing left to report", d.hart.topei, 0);
    chk("and meip drops", zeroExtend(pack(d.hart.meip)), 0);

    cw(8'h71, 32'hFFFF_FFFF);
    cr(8'h71);  chk("reserved select 0x71 reads zero", rv, 0);
    cr(8'h73);  chk("reserved select 0x73 reads zero", rv, 0);
    cw(8'h80, 1);
    cr(8'h80);  chk("bit 0 of eip0 is read-only zero", rv, 0);
    cw(8'h82, 32'hFFFF_FFFF);
    cr(8'h82);  chk("eip2 does not exist with 63 identities", rv, 0);
    cw(8'hC1, 32'hFFFF_FFFF);
    cr(8'hC1);  chk("eie1 holds identities 32 to 63", rv, 32'hFFFF_FFFF);
    cw(8'h81, 32'h8000_0000);
    chk("identity 63 pending and enabled is reported", d.hart.topei, 32'h003F_003F);
  endseq;

  FSM fsm <- mkFSM(test);
  Reg#(Bool) started <- mkReg(False);

  rule go (!started);
    started <= True;
    fsm.start;
  endrule

  rule count;
    cyc <= cyc + 1;
    if (cyc > 2000) begin
      $display("TIMEOUT");
      $finish(1);
    end
  endrule

  rule fin (started && fsm.done);
    if (bad) $display("FAILED");
    else $display("PASS imsic: @VERDICT@");
    $finish(bad ? 1 : 0);
  endrule
endmodule

endpackage
'''

(out / f"Imsic{label}Tb.bsv").write_text(TEMPLATE.replace("@L@", label).replace("@VERDICT@", verdict),
                                         encoding="utf-8")
print(f"  imsic 行为测试台就位：63 个号，标签 {label or '（空）'}")
