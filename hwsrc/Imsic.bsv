package Imsic;

// 一颗核的 IMSIC，只有机器级中断文件（AIA 第 3 章）。控制口 regs 是中断文件的那一页（seteipnum_le 在 0x000），
// hart 口给核用：csr 按 miselect 的值寻址（核把 mireg 的读写转过来）、topei 给 mtopei 读、claim 给 mtopei 写、meip 接 mip.MEIP。
// 状态只在 step 一条规则里写：控制口写号、CSR 写、领取都走线，同拍的次序因此只写在一处——
// CSR 整字写 → 领取清这一拍开头报出的号 → 新到的号置上（同号同拍到达不丢）。
// CSR 口若直接写 eie、阈值，就要排在读它们的 step 之后，而它送 eip 的线又要排在 step 之前，成环
//
// 两层照 rom 的 mkRomOf / mkRom：mkImsicOf 对号数参数化；mkImsic 是息壤例化的那一层，号数定在 63。
// 号数不做成旋钮：息壤的整数参数第一次量价目表会取范围里的离格点（rom 取了 34、160），碰上不是 64k−1 的值
// 编译期检查就拦下、量不出来；choice 只能是特性，进的是配置结构体，进不了接口的类型参数

import Vector::*;
import RegIf::*;
import ImsicSel::*;

typedef struct {
  Bit#(0) none;
} ImsicCfg;

interface ImsicHart;
  interface RegIf#(8, 32) csr;
  (* always_ready *) method Bit#(32) topei;
  (* always_ready *) method Action   claim;
  (* always_ready *) method Bool     meip;
endinterface

// 号数在类型里：ImsicCore#(63)、ImsicCore#(127) ……
interface ImsicCore#(numeric type ids);
  interface RegIf#(12, 32) regs;
  interface ImsicHart      hart;
endinterface

interface ImsicIfc#(numeric type aw, numeric type dw);
  interface RegIf#(aw, dw) regs;
  interface ImsicHart      hart;
endinterface

module mkImsicOf(ImsicCore#(ids))
  provisos (Add#(ids, 1, n), Add#(1, _a, n), Add#(n, _b, 2048));

  Integer idsN = idsChecked(valueOf(ids));

  Reg#(Bit#(n))  eip <- mkReg(0);
  Reg#(Bit#(n))  eie <- mkReg(0);
  Reg#(Bit#(11)) thr <- mkReg(0);
  Reg#(Bool)     dlv <- mkReg(False);

  RWire#(Bit#(11))                   setW   <- mkRWire;
  RWire#(Tuple2#(Bit#(6), Bit#(32))) eipW   <- mkRWire;
  RWire#(Tuple2#(Bit#(6), Bit#(32))) eieW   <- mkRWire;
  RWire#(Bit#(11))                   thrW   <- mkRWire;
  RWire#(Bool)                       dlvW   <- mkRWire;
  PulseWire                          claimP <- mkPulseWire;

  // 第 k 个 32 位字：XLEN 32 时 eip k 管 k×32 到 k×32+31 号（AIA 3.8.3），越过实现的号读 0、写丢掉
  function Bit#(32) wordOf(Bit#(n) v, Bit#(6) k);
    Bit#(2048) w = zeroExtend(v);
    return truncate(w >> {k, 5'b0});
  endfunction
  function Bit#(n) wordSet(Bit#(n) v, Bit#(6) k, Bit#(32) x);
    Bit#(2048) w = zeroExtend(v);
    Bit#(2048) m = zeroExtend(32'hFFFF_FFFF) << {k, 5'b0};
    Bit#(2048) y = zeroExtend(x) << {k, 5'b0};
    return truncate((w & ~m) | (y & m));
  endfunction

  Bit#(n) pv = eip;
  Bit#(n) ev = eie;
  function Bool isLive(Integer i) =
    pv[i] == 1 && ev[i] == 1 && i != 0 && (thr == 0 || fromInteger(i) < thr);
  Vector#(n, Bool) live = genWith(isLive);
  Bit#(11) top = lowest(live);

  rule step;
    Bit#(n) p   = eip;
    Bit#(n) e   = eie;
    Bit#(n) one = 1;
    if (eipW.wget matches tagged Valid {.k, .x}) p = wordSet(p, k, x);
    if (eieW.wget matches tagged Valid {.k, .x}) e = wordSet(e, k, x);
    if (claimP) p = p & ~(one << top);
    if (setW.wget matches tagged Valid .i) p = p | (one << i);
    p[0] = 0;
    e[0] = 0;
    eip <= p;
    eie <= e;
    if (thrW.wget matches tagged Valid .t) thr <= t;
    if (dlvW.wget matches tagged Valid .d) dlv <= d;
  endrule

  interface RegIf regs;
    method ActionValue#(RegRsp#(32)) access(RegReq#(12, 32) r);
      // 只支持对齐的 32 位读写（AIA 3.5），别的访问答错、不改状态；整页读恒 0
      Bool whole = r.addr[1:0] == 0 && (!r.write || r.wstrb == 4'hF);
      if (whole && r.write && r.addr == 12'h000 && r.wdata != 0 && r.wdata <= fromInteger(idsN))
        setW.wset(truncate(r.wdata));
      return RegRsp { rdata: 0, err: !whole };
    endmethod
  endinterface

  interface ImsicHart hart;
    interface RegIf csr;
      method ActionValue#(RegRsp#(32)) access(RegReq#(8, 32) r);
        Bit#(8)  s  = r.addr;
        Bit#(32) rd = 0;
        if (s == 8'h70) begin
          rd = dlv ? 1 : 0;
          // WARL：只收 0 与 1（0x40000000 本次不做）
          if (r.write && (r.wdata == 0 || r.wdata == 1)) dlvW.wset(r.wdata == 1);
        end else if (s == 8'h72) begin
          rd = zeroExtend(thr);
          if (r.write && r.wdata <= fromInteger(idsN)) thrW.wset(truncate(r.wdata));
        end else if (s >= 8'h80 && s <= 8'hBF) begin
          Bit#(6) k = truncate(s - 8'h80);
          rd = wordOf(eip, k);
          if (r.write) eipW.wset(tuple2(k, r.wdata));
        end else if (s >= 8'hC0) begin
          Bit#(6) k = truncate(s - 8'hC0);
          rd = wordOf(eie, k);
          if (r.write) eieW.wset(tuple2(k, r.wdata));
        end
        return RegRsp { rdata: rd, err: False };
      endmethod
    endinterface
    method Bit#(32) topei = topeiOf(top);
    method Action claim = claimP.send;
    method Bool meip = dlv && top != 0;
  endinterface
endmodule

// 息壤例化的那一层：控制口的地址宽 12、数据宽 32 由契约定死，号数 63
module mkImsic#(ImsicCfg cfg)(ImsicIfc#(aw, dw))
  provisos (Add#(0, aw, 12), Add#(0, dw, 32));
  ImsicCore#(63) c <- mkImsicOf;
  interface regs = c.regs;
  interface hart = c.hart;
endmodule

endpackage
