import { useQuery } from '@tanstack/react-query';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { Shield, AlertTriangle, GitCompareArrows, Activity } from 'lucide-react';
import { fetchDQScoreTrend, fetchDQReconciliation, fetchDQAnomalyRawCount, fetchDQCategoryHealth, fetchDQRulesSummary, fetchDQAnomalies } from '../api/client';

const TIP = {
  contentStyle:{backgroundColor:'#101010',border:'1px solid #2E2E2E',borderRadius:3,fontSize:11,fontFamily:"'IBM Plex Mono',monospace",padding:'6px 8px'},
  itemStyle:{color:'#E0E0E0',fontSize:11,fontFamily:"'IBM Plex Mono',monospace"},
};
const AX = {fill:'#454545',fontSize:10,fontFamily:"'IBM Plex Mono',monospace"};
const GR = {strokeDasharray:'2 6',stroke:'rgba(255,255,255,.03)'};
const DIM_B:Record<string,string> = {Completeness:'b-b',Validity:'b-g',Timeliness:'b-y',Consistency:'b-p'};
const LAY_B:Record<string,string> = {Stream:'b-c',ETL:'b-p'};
const SEV_B:Record<string,string> = {critical:'b-r',warning:'b-y',info:'b-b'};
const ANOM_L:Record<string,string> = {payment_drop:'결제 급감',category_drop:'카테고리 급감',abnormal_price_spike:'이상 가격',reconciliation_mismatch:'교차검증 불일치'};
const fmtD = (d:string) => { try{return new Date(d).toLocaleDateString('ko-KR',{month:'short',day:'numeric'})}catch{return d} };
const fmtT = (h:string) => { try{return new Date(h).toLocaleTimeString('ko-KR',{hour:'2-digit',minute:'2-digit'})}catch{return h} };
const fmtDT = (d:string) => { try{const x=new Date(d);return `${x.toLocaleDateString('ko-KR',{month:'short',day:'numeric'})} ${x.toLocaleTimeString('ko-KR',{hour:'2-digit',minute:'2-digit'})}`}catch{return d} };
const fmtN = (n:number|null|undefined) => { if(n==null) return '--'; if(n>=1e6) return `${(n/1e6).toFixed(1)}M`; if(n>=1e3) return `${(n/1e3).toFixed(1)}K`; return n.toLocaleString(); };

function Sk({h=240}:{h?:number}){return <div className="sk" style={{width:'100%',height:h}}/>}

function Gauge({score}:{score:number}) {
  const sz=40, r=16, circ=2*Math.PI*r, off=circ-(score/100)*circ;
  const col = score>=90?'var(--accent)':score>=70?'var(--yellow)':'var(--red)';
  return (
    <svg width={sz} height={sz} viewBox={`0 0 ${sz} ${sz}`} style={{transform:'rotate(-90deg)',flexShrink:0}}>
      <circle cx={sz/2} cy={sz/2} r={r} className="gauge-bg"/>
      <circle cx={sz/2} cy={sz/2} r={r} className="gauge-v" stroke={col} strokeDasharray={circ} strokeDashoffset={off}/>
    </svg>
  );
}

interface ScoreRow { date:string; completeness_score:number; validity_score:number; timeliness_score:number; total_score:number }
interface ReconRow { hour:string; category_total:number; payment_total:number; diff_pct:number }
interface CatRow { category:string; event_count:number; purchase_count:number; total_revenue:number }
interface RuleRow { dimension:string; rule_name:string; target:string; layer:string; trigger_count_7d:number; status:string }
interface AnomRow { detected_at:string; anomaly_type:string; dimension:string; expected_value:number|null; actual_value:number|null; severity:string; notes:string|null }

export default function DQPage() {
  const {data:score=[],isLoading:sL} = useQuery<ScoreRow[]>({queryKey:['dq-score'],queryFn:fetchDQScoreTrend,refetchInterval:60_000});
  const {data:recon=[],isLoading:rL} = useQuery<ReconRow[]>({queryKey:['dq-recon'],queryFn:fetchDQReconciliation,refetchInterval:60_000});
  const {data:rawCnt} = useQuery<{total:number;breakdown:Record<string,number>}>({queryKey:['dq-raw'],queryFn:fetchDQAnomalyRawCount,refetchInterval:60_000});
  const {data:cats=[],isLoading:cL} = useQuery<CatRow[]>({queryKey:['dq-cat'],queryFn:fetchDQCategoryHealth,refetchInterval:60_000});
  const {data:rules=[]} = useQuery<RuleRow[]>({queryKey:['dq-rules'],queryFn:fetchDQRulesSummary,refetchInterval:60_000});
  const {data:anoms=[]} = useQuery<AnomRow[]>({queryKey:['dq-anoms'],queryFn:fetchDQAnomalies,refetchInterval:60_000});

  const latest = score.length>0 ? score[score.length-1].total_score : null;
  const anomCnt = rawCnt?.total ?? 0;
  const maxDiff = recon.length>0 ? Math.max(...recon.map(r=>r.diff_pct??0)) : 0;

  return (
    <div>
      {sL ? (
        <div className="m3">{[0,1,2].map(i=><div key={i} className="mc"><Sk h={48}/></div>)}</div>
      ) : (
        <div className="m3">
          <div className={`mc ${latest!==null&&latest>=90?'':'rd'}`}>
            <div className="ml"><Shield size={12}/> DQ SCORE</div>
            <div className="mv-row">
              {latest!==null && <Gauge score={latest}/>}
              <div className={`mv ${latest!==null&&latest>=90?'g':latest!==null?'r':''}`}>{latest??'--'}</div>
            </div>
            <div className="ms">최신 일자 기준</div>
          </div>
          <div className={`mc ${anomCnt>0?'rd':''}`}>
            <div className="ml"><AlertTriangle size={12}/> ANOMALY ISOLATION</div>
            <div className={`mv ${anomCnt>0?'r':'g'}`}>{anomCnt}</div>
            <div className="ms">anomaly_raw 24h</div>
          </div>
          <div className={`mc ${maxDiff>5?'rd':'pr'}`}>
            <div className="ml"><GitCompareArrows size={12}/> MAX DIFF</div>
            <div className={`mv ${maxDiff>5?'r':''}`}>{maxDiff.toFixed(1)}%</div>
            <div className="ms">카테고리 vs 결제 교차검증</div>
          </div>
        </div>
      )}

      <div className="pn">
        <div className="ph"><Shield size={13}/><span className="pt">DQ Score Trend</span><span className="pm">14d · C / V / T</span></div>
        <div className="pb">
          {sL ? <Sk/> : score.length>0 ? (
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={score}>
                <CartesianGrid {...GR}/>
                <XAxis dataKey="date" tick={AX} tickLine={false} axisLine={false} tickFormatter={fmtD}/>
                <YAxis domain={[0,100]} tick={AX} tickLine={false} axisLine={false}/>
                <Tooltip {...TIP} labelFormatter={(d)=>{try{return fmtD(d as string)}catch{return String(d)}}}/>
                <ReferenceLine y={90} stroke="#EF4444" strokeDasharray="4 4" strokeOpacity={.4} label={{value:'90',fill:'#EF4444',fontSize:10,fontFamily:"'IBM Plex Mono'"}}/>
                <Line type="monotone" dataKey="completeness_score" stroke="#3B82F6" strokeWidth={2} name="Completeness" dot={false}/>
                <Line type="monotone" dataKey="validity_score" stroke="#22C55E" strokeWidth={2} name="Validity" dot={false}/>
                <Line type="monotone" dataKey="timeliness_score" stroke="#F59E0B" strokeWidth={2} name="Timeliness" dot={false}/>
              </LineChart>
            </ResponsiveContainer>
          ) : <div className="empty">데이터 없음</div>}
        </div>
      </div>

      <div className="g2">
        <div className="pn">
          <div className="ph"><GitCompareArrows size={13}/><span className="pt">Reconciliation Diff</span><span className="pm">24h</span></div>
          <div className="pb">
            {rL ? <Sk h={200}/> : recon.length>0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={recon}>
                  <CartesianGrid {...GR}/>
                  <XAxis dataKey="hour" tick={AX} tickLine={false} axisLine={false} tickFormatter={fmtT}/>
                  <YAxis tick={AX} tickLine={false} axisLine={false} tickFormatter={(v:number)=>`${v}%`}/>
                  <Tooltip {...TIP} formatter={(v:number|undefined)=>[`${(v??0).toFixed(1)}%`,'diff']}/>
                  <ReferenceLine y={5} stroke="#EF4444" strokeDasharray="4 4" strokeOpacity={.4} label={{value:'5%',fill:'#EF4444',fontSize:10,fontFamily:"'IBM Plex Mono'"}}/>
                  <Line type="monotone" dataKey="diff_pct" stroke="#A855F7" strokeWidth={2} dot={false} activeDot={{r:3,fill:'#A855F7',stroke:'#0E0E0E',strokeWidth:2}}/>
                </LineChart>
              </ResponsiveContainer>
            ) : <div className="empty">데이터 없음</div>}
          </div>
        </div>
        <div className="pn">
          <div className="ph"><Activity size={13}/><span className="pt">Category Health</span><span className="pm">24h</span></div>
          <div className="pb f">
            {cL ? <div style={{padding:12}}><Sk h={160}/></div> : (
              <div className="tscr">
                <table className="dt"><thead><tr><th>카테고리</th><th className="r">이벤트</th><th className="r">구매</th><th className="r">매출</th></tr></thead>
                <tbody>{cats.length>0 ? cats.map(r=>(
                  <tr key={r.category}><td className="n">{r.category}</td><td className="r">{fmtN(r.event_count)}</td><td className="r">{fmtN(r.purchase_count)}</td><td className="r">{fmtN(r.total_revenue)}</td></tr>
                )) : <tr><td colSpan={4} className="empty">데이터 없음</td></tr>}</tbody></table>
              </div>
            )}
          </div>
        </div>
      </div>

      {anoms.length>0 && (
        <div className="pn">
          <div className="ph"><AlertTriangle size={13}/><span className="pt">Recent Anomalies</span><span className="pm">{anoms.length}건</span></div>
          <div className="pb f">
            <div className="tscr">
              <table className="dt"><thead><tr><th>시각</th><th>유형</th><th>대상</th><th>심각도</th><th className="r">예상</th><th className="r">실제</th></tr></thead>
              <tbody>{anoms.map((a,i)=>(
                <tr key={i}>
                  <td className="d" style={{whiteSpace:'nowrap'}}>{fmtDT(a.detected_at)}</td>
                  <td className="n">{ANOM_L[a.anomaly_type]??a.anomaly_type}</td>
                  <td>{a.dimension}</td>
                  <td><span className={`b ${SEV_B[a.severity]??'b-y'}`}>{a.severity}</span></td>
                  <td className="r">{a.expected_value!=null?fmtN(a.expected_value):'--'}</td>
                  <td className="r">{a.actual_value!=null?fmtN(a.actual_value):'--'}</td>
                </tr>
              ))}</tbody></table>
            </div>
          </div>
        </div>
      )}

      <div className="pn">
        <div className="ph"><Shield size={13}/><span className="pt">DQ Rules</span><span className="pm">{rules.length}개</span></div>
        <div className="pb f">
          <table className="dt"><thead><tr><th>Dimension</th><th>규칙</th><th>대상</th><th>Layer</th><th className="r">7d</th><th>상태</th></tr></thead>
          <tbody>{rules.length>0 ? rules.map((r,i)=>(
            <tr key={i}>
              <td><span className={`b ${DIM_B[r.dimension]??'b-g'}`}>{r.dimension}</span></td>
              <td className="n">{r.rule_name}</td>
              <td className="d">{r.target}</td>
              <td><span className={`b ${LAY_B[r.layer]??'b-b'}`}>{r.layer}</span></td>
              <td className="r" style={{fontWeight:r.trigger_count_7d>0?600:400,color:r.trigger_count_7d>0?'#F59E0B':'#454545'}}>{r.trigger_count_7d}</td>
              <td><span className="b b-g">{r.status}</span></td>
            </tr>
          )) : <tr><td colSpan={6} className="empty">데이터 없음</td></tr>}</tbody></table>
        </div>
      </div>
    </div>
  );
}
