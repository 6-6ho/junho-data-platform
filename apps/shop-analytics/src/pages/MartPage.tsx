import { useQuery } from '@tanstack/react-query';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { TrendingUp, Users, Link2, CalendarDays } from 'lucide-react';
import { fetchMartDailySales, fetchMartRFM, fetchMartAssociation, fetchMartWeeklyTrend } from '../api/client';

const C = ['#22C55E','#3B82F6','#A855F7','#F59E0B','#EF4444'];
const TIP = {
  contentStyle:{backgroundColor:'#101010',border:'1px solid #2E2E2E',borderRadius:3,fontSize:11,fontFamily:"'IBM Plex Mono',monospace",padding:'6px 8px'},
  itemStyle:{color:'#E0E0E0',fontSize:11,fontFamily:"'IBM Plex Mono',monospace"},
};
const AX = {fill:'#454545',fontSize:10,fontFamily:"'IBM Plex Mono',monospace"};
const GR = {strokeDasharray:'2 6',stroke:'rgba(255,255,255,.03)',vertical:false as const};

const krw = (n:number|null|undefined) => { if(n==null) return '--'; if(n>=1e12) return `${(n/1e12).toFixed(1)}조`; if(n>=1e8) return `${(n/1e8).toFixed(1)}억`; if(n>=1e4) return `${(n/1e4).toFixed(0)}만`; return `₩${n.toLocaleString()}`; };
const fN = (n:number|null|undefined) => { if(n==null) return '--'; if(n>=1e9) return `${(n/1e9).toFixed(1)}B`; if(n>=1e6) return `${(n/1e6).toFixed(1)}M`; if(n>=1e3) return `${(n/1e3).toFixed(1)}K`; return n.toLocaleString(); };
const fD = (d:string) => { try{return new Date(d).toLocaleDateString('ko-KR',{month:'short',day:'numeric'})}catch{return d} };

function Sk({h=240}:{h?:number}){return <div className="sk" style={{width:'100%',height:h}}/>}

interface Sales { date:string; category:string; revenue:number; orders:number; avg_value:number }
interface RFM { segment:string; user_count:number }
interface Assoc { antecedents:string; consequents:string; confidence:number; lift:number; support:number }
interface Weekly { week:string; revenue:number; orders:number }

export default function MartPage() {
  const {data:sales=[],isLoading:sL} = useQuery<Sales[]>({queryKey:['mart-sales'],queryFn:()=>fetchMartDailySales(7),staleTime:300_000});
  const {data:rfm=[],isLoading:rL} = useQuery<RFM[]>({queryKey:['mart-rfm'],queryFn:fetchMartRFM,staleTime:300_000});
  const {data:assoc=[],isLoading:aL} = useQuery<Assoc[]>({queryKey:['mart-assoc'],queryFn:()=>fetchMartAssociation(10),staleTime:300_000});
  const {data:weekly=[],isLoading:wL} = useQuery<Weekly[]>({queryKey:['mart-weekly'],queryFn:()=>fetchMartWeeklyTrend(8),staleTime:300_000});

  const groups = new Map<string,Sales[]>();
  sales.forEach(r=>{const e=groups.get(r.date)||[];e.push(r);groups.set(r.date,e)});
  const dates = Array.from(groups.keys()).sort().reverse();
  const wData = [...weekly].sort((a,b)=>new Date(a.week).getTime()-new Date(b.week).getTime());
  const totalUsers = rfm.reduce((s,r)=>s+(r.user_count??0),0);

  return (
    <div>
      <div className="pn">
        <div className="ph"><TrendingUp size={13}/><span className="pt">Weekly Trend</span><span className="pm">8w · revenue + orders</span></div>
        <div className="pb">
          {wL ? <Sk/> : wData.length>0 ? (
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={wData}>
                <CartesianGrid {...GR}/>
                <XAxis dataKey="week" tick={AX} tickLine={false} axisLine={false} tickFormatter={fD}/>
                <YAxis yAxisId="l" tick={AX} tickLine={false} axisLine={false} tickFormatter={(v:number)=>krw(v)}/>
                <YAxis yAxisId="r" orientation="right" tick={AX} tickLine={false} axisLine={false} tickFormatter={(v:number)=>fN(v)}/>
                <Tooltip {...TIP} formatter={(v:number|undefined,name?:string)=>{if(name==='매출')return[krw(v??0),name];return[fN(v??0),name??'']}} labelFormatter={(d)=>{try{return`${new Date(d as string).toLocaleDateString('ko-KR')} 주차`}catch{return String(d)}}}/>
                <Line yAxisId="l" type="monotone" dataKey="revenue" stroke="#22C55E" strokeWidth={2} name="매출" dot={{r:3,fill:'#22C55E',stroke:'#0E0E0E',strokeWidth:2}} activeDot={{r:4,fill:'#22C55E',stroke:'#0E0E0E',strokeWidth:2}}/>
                <Line yAxisId="r" type="monotone" dataKey="orders" stroke="#3B82F6" strokeWidth={2} name="주문수" dot={{r:3,fill:'#3B82F6',stroke:'#0E0E0E',strokeWidth:2}} activeDot={{r:4,fill:'#3B82F6',stroke:'#0E0E0E',strokeWidth:2}}/>
              </LineChart>
            </ResponsiveContainer>
          ) : <div className="empty">데이터 없음</div>}
        </div>
      </div>

      <div className="g2">
        <div className="pn">
          <div className="ph"><Users size={13}/><span className="pt">RFM Segments</span><span className="pm">{totalUsers.toLocaleString()} users</span></div>
          <div className="pb">
            {rL ? <Sk h={220}/> : rfm.length>0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={rfm} layout="vertical" margin={{left:4}}>
                  <CartesianGrid strokeDasharray="2 6" stroke="rgba(255,255,255,.03)" horizontal={false}/>
                  <XAxis type="number" tick={AX} tickLine={false} axisLine={false} tickFormatter={(v:number)=>fN(v)}/>
                  <YAxis type="category" dataKey="segment" width={56} tick={{fill:'#7A7A7A',fontSize:11,fontFamily:"'IBM Plex Sans'"}} tickLine={false} axisLine={false}/>
                  <Tooltip {...TIP} formatter={(v:number|undefined)=>[(v??0).toLocaleString(),'고객 수']}/>
                  <Bar dataKey="user_count" name="고객 수" radius={[0,3,3,0]} barSize={18}>
                    {rfm.map((_,i)=><Cell key={i} fill={C[i%C.length]} fillOpacity={.85}/>)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : <div className="empty">데이터 없음</div>}
          </div>
        </div>
        <div className="pn">
          <div className="ph"><Link2 size={13}/><span className="pt">Association Rules</span><span className="pm">Top 10</span></div>
          <div className="pb f">
            {aL ? <div style={{padding:12}}><Sk h={180}/></div> : (
              <table className="dt"><thead><tr><th>선행</th><th>후행</th><th className="r">Conf.</th><th className="r">Lift</th></tr></thead>
              <tbody>{assoc.length>0 ? assoc.map((r,i)=>(
                <tr key={i}>
                  <td style={{fontSize:11}}>{r.antecedents}</td>
                  <td style={{fontSize:11}}>{r.consequents}</td>
                  <td className="r">{((r.confidence??0)*100).toFixed(1)}%</td>
                  <td className="r" style={{color:r.lift>2?'#22C55E':'#7A7A7A',fontWeight:r.lift>2?600:400}}>{r.lift.toFixed(2)}</td>
                </tr>
              )) : <tr><td colSpan={4} className="empty">데이터 없음</td></tr>}</tbody></table>
            )}
          </div>
        </div>
      </div>

      <div className="pn">
        <div className="ph"><CalendarDays size={13}/><span className="pt">Daily Sales</span><span className="pm">7d · by category</span></div>
        <div className="pb f">
          {sL ? <div style={{padding:12}}><Sk h={200}/></div> : (
            <div className="tscr">
              <table className="dt"><thead><tr><th>날짜</th><th>카테고리</th><th className="r">매출</th><th className="r">주문수</th><th className="r">객단가</th></tr></thead>
              <tbody>{dates.length>0 ? dates.map(d=>{
                const rows=groups.get(d)!;
                return rows.map((r,i)=>(
                  <tr key={`${d}-${r.category}`}>
                    {i===0 && <td className="n" rowSpan={rows.length} style={{verticalAlign:'top',whiteSpace:'nowrap'}}>{(()=>{try{return new Date(d).toLocaleDateString('ko-KR',{month:'short',day:'numeric',weekday:'short'})}catch{return d}})()}</td>}
                    <td className="n">{r.category}</td>
                    <td className="r">{krw(r.revenue)}</td>
                    <td className="r">{fN(r.orders)}</td>
                    <td className="r">{krw(r.avg_value)}</td>
                  </tr>
                ));
              }) : <tr><td colSpan={5} className="empty">데이터 없음</td></tr>}</tbody></table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
