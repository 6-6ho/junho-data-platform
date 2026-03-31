import { useQuery } from '@tanstack/react-query';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, ReferenceLine,
} from 'recharts';
import { Layers, Zap, DollarSign, Clock, Activity, TrendingUp } from 'lucide-react';
import { fetchSummary, fetchHourlyTraffic, fetchHourlyThroughput, fetchFunnel } from '../api/client';

const C = ['#22C55E','#3B82F6','#A855F7','#F59E0B','#EF4444','#06B6D4','#EC4899','#F97316'];
const TIP = {
  contentStyle: { backgroundColor:'#101010', border:'1px solid #2E2E2E', borderRadius:3, fontSize:11, fontFamily:"'IBM Plex Mono',monospace", padding:'6px 8px' },
  itemStyle: { color:'#E0E0E0', fontSize:11, fontFamily:"'IBM Plex Mono',monospace" },
};
const AX = { fill:'#454545', fontSize:10, fontFamily:"'IBM Plex Mono',monospace" };
const GR = { strokeDasharray:'2 6', stroke:'rgba(255,255,255,.03)', vertical:false as const };

const fmt = (n: number|null|undefined) => { if(n==null) return '--'; if(n>=1e9) return `${(n/1e9).toFixed(1)}B`; if(n>=1e6) return `${(n/1e6).toFixed(1)}M`; if(n>=1e3) return `${(n/1e3).toFixed(1)}K`; return n.toLocaleString(); };
const krw = (n: number|null|undefined) => { if(n==null) return '--'; if(n>=1e8) return `${(n/1e8).toFixed(1)}억`; if(n>=1e4) return `${(n/1e4).toFixed(0)}만`; return `₩${n.toLocaleString()}`; };
const fresh = (s: number|null|undefined) => { if(s==null) return '--'; if(s<60) return `${s}s`; if(s<3600) return `${Math.floor(s/60)}m`; return `${Math.floor(s/3600)}h`; };
const hm = (t: string) => { try{ return new Date(t).toLocaleTimeString('ko-KR',{hour:'2-digit',minute:'2-digit'}); }catch{ return t; } };

function Sk({ h=240 }: { h?: number }) { return <div className="sk" style={{ width:'100%', height:h }} />; }

export default function OverviewPage() {
  const { data: sum, isLoading: sl } = useQuery({ queryKey:['summary'], queryFn:fetchSummary, refetchInterval:30_000 });
  const { data: traffic=[], isLoading: tl } = useQuery<Record<string,unknown>[]>({ queryKey:['hourly-traffic'], queryFn:fetchHourlyTraffic, refetchInterval:30_000 });
  const { data: thru=[], isLoading: hl } = useQuery<{hour:string;total_orders:number}[]>({ queryKey:['hourly-throughput'], queryFn:fetchHourlyThroughput, refetchInterval:30_000 });
  const { data: fun, isLoading: fl } = useQuery<{page_view:number;add_to_cart:number;purchase:number;conversion_rate:number}>({ queryKey:['funnel'], queryFn:fetchFunnel, refetchInterval:30_000 });

  const cats = Array.from(new Set(traffic.flatMap(r=>Object.keys(r).filter(k=>k!=='time'))));
  const major = cats.filter(c=>traffic.reduce((s,r)=>s+((r[c] as number)??0),0)>1000);
  const avg = thru.length>0 ? Math.round(thru.reduce((s,r)=>s+(r.total_orders??0),0)/thru.length) : 0;
  const funnel = fun ? [
    {step:'페이지 조회',count:fun.page_view??0,color:'#22C55E'},
    {step:'장바구니',count:fun.add_to_cart??0,color:'#3B82F6'},
    {step:'구매',count:fun.purchase??0,color:'#A855F7'},
  ] : [];
  const maxF = funnel.length>0 ? Math.max(...funnel.map(f=>f.count)) : 1;

  return (
    <div>
      {sl ? (
        <div className="m4">{[0,1,2,3].map(i=><div key={i} className="mc"><Sk h={48}/></div>)}</div>
      ) : (
        <div className="m4">
          <div className="mc bl">
            <div className="ml"><Layers size={12}/> TOTAL EVENTS</div>
            <div className="mv">{fmt(sum?.total_events)}</div>
            <div className="ms">전체 누적</div>
          </div>
          <div className="mc">
            <div className="ml"><Zap size={12}/> 24H THROUGHPUT</div>
            <div className="mv g">{fmt(sum?.today_events)}</div>
            <div className="ms">오늘 이벤트</div>
          </div>
          <div className="mc yl">
            <div className="ml"><DollarSign size={12}/> 24H REVENUE</div>
            <div className="mv">{krw(sum?.today_revenue)}</div>
            <div className="ms">오늘 매출</div>
          </div>
          <div className="mc cy">
            <div className="ml"><Clock size={12}/> FRESHNESS</div>
            <div className="mv g">{fresh(sum?.data_freshness_sec)}</div>
            <div className="ms">최신 이벤트 기준</div>
          </div>
        </div>
      )}

      <div className="g2">
        <div className="pn">
          <div className="ph"><Activity size={13}/><span className="pt">Category Traffic</span><span className="pm">24h</span></div>
          <div className="pb">
            {tl ? <Sk/> : traffic.length>0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <AreaChart data={traffic}>
                  <defs>{major.map((c,i)=>(<linearGradient key={c} id={`g-${c}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={C[i%C.length]} stopOpacity={.3}/><stop offset="100%" stopColor={C[i%C.length]} stopOpacity={0}/></linearGradient>))}</defs>
                  <CartesianGrid {...GR}/>
                  <XAxis dataKey="time" tick={AX} tickLine={false} axisLine={false} tickFormatter={hm}/>
                  <YAxis tick={AX} tickLine={false} axisLine={false} tickFormatter={(v:number)=>fmt(v)}/>
                  <Tooltip {...TIP} labelFormatter={(t)=>{try{return new Date(t as string).toLocaleString('ko-KR')}catch{return String(t)}}}/>
                  {major.map((c,i)=>(<Area key={c} type="monotone" dataKey={c} stackId="1" stroke={C[i%C.length]} strokeWidth={1.5} fill={`url(#g-${c})`}/>))}
                </AreaChart>
              </ResponsiveContainer>
            ) : <div className="empty">데이터 없음</div>}
          </div>
        </div>
        <div className="pn">
          <div className="ph"><TrendingUp size={13}/><span className="pt">Hourly Throughput</span><span className="pm">avg {fmt(avg)}/h</span></div>
          <div className="pb">
            {hl ? <Sk/> : thru.length>0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={thru}>
                  <CartesianGrid {...GR}/>
                  <XAxis dataKey="hour" tick={AX} tickLine={false} axisLine={false} tickFormatter={hm}/>
                  <YAxis tick={AX} tickLine={false} axisLine={false} tickFormatter={(v:number)=>fmt(v)}/>
                  <Tooltip {...TIP} formatter={(v:number|undefined)=>[(v??0).toLocaleString(),'주문']} labelFormatter={(h)=>{try{return new Date(h as string).toLocaleString('ko-KR')}catch{return String(h)}}}/>
                  {avg>0 && <ReferenceLine y={avg} stroke="#F59E0B" strokeDasharray="4 4" strokeOpacity={.5} label={{value:`avg ${fmt(avg)}`,fill:'#F59E0B',fontSize:10,fontFamily:"'IBM Plex Mono'"}}/>}
                  <Line type="monotone" dataKey="total_orders" stroke="#22C55E" strokeWidth={2} dot={false} activeDot={{r:3,fill:'#22C55E',stroke:'#0E0E0E',strokeWidth:2}}/>
                </LineChart>
              </ResponsiveContainer>
            ) : <div className="empty">데이터 없음</div>}
          </div>
        </div>
      </div>

      {fl ? <div className="pn"><div className="ph"><span className="pt">Conversion Funnel</span></div><div className="pb"><Sk h={80}/></div></div>
      : funnel.length>0 && (
        <div className="pn">
          <div className="ph">
            <span className="pt">Conversion Funnel</span>
            {fun?.conversion_rate!=null && <span className="pm" style={{color:'var(--accent)',fontWeight:600}}>CVR {fun.conversion_rate.toFixed(2)}%</span>}
          </div>
          <div className="pb">
            {funnel.map((f,i)=>{
              const pct = maxF>0 ? (f.count/maxF)*100 : 0;
              const cr = i>0&&funnel[i-1].count>0 ? ((f.count/funnel[i-1].count)*100).toFixed(1) : null;
              return (
                <div className="fn" key={f.step}>
                  <span className="fn-l">{f.step}</span>
                  <div className="fn-t"><div className="fn-f" style={{width:`${pct}%`,background:`linear-gradient(90deg,${f.color},${f.color}bb)`,boxShadow:`0 0 8px ${f.color}22`}}/></div>
                  <span className="fn-v">{fmt(f.count)}</span>
                  <span className="fn-p">{cr?`${cr}%`:''}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
