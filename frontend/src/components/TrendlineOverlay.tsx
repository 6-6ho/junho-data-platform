import { useRef, useState, useEffect } from 'react';
import { type IChartApi, type ISeriesApi, type Time, type Coordinate } from 'lightweight-charts';
import { createTrendline, deleteTrendline } from '../api/client'; // updateTrendline removed
import { clsx } from 'clsx';
import { X } from 'lucide-react';

interface Point {
    time: number; // unix timestamp (seconds)
    price: number;
}

interface Trendline {
    line_id: string;
    symbol: string;
    p1: number;
    t1_ms: number;
    p2: number;
    t2_ms: number;
    enabled: boolean;
}

interface Props {
    chart: IChartApi | null;
    series: ISeriesApi<"Candlestick"> | null;
    symbol: string;
    trendlines: Trendline[];
    onUpdate: () => void;
    isDrawing: boolean;
    onDrawingComplete: () => void;
}

export default function TrendlineOverlay({
    chart, series, symbol, trendlines, onUpdate, isDrawing, onDrawingComplete
}: Props) {
    const svgRef = useRef<SVGSVGElement>(null);
    /* Unused in V1
    const [dragState, setDragState] = useState<{
        lineId: string | 'new',
        handle: 'p1' | 'p2' | 'move',
        startMouse: { x: number, y: number },
        itemSnapshot?: any
    } | null>(null);
    */

    // Temporary line being drawn
    const [newPoint1, setNewPoint1] = useState<Point | null>(null);
    const [mousePos, setMousePos] = useState<{ x: number, y: number } | null>(null);

    // Helper to convert data -> coordinate
    const toCoords = (t_ms: number, p: number) => {
        if (!chart || !series) return null;
        const time = (t_ms / 1000) as Time;
        const x = chart.timeScale().timeToCoordinate(time);
        const y = series.priceToCoordinate(p);
        return (x === null || y === null) ? null : { x, y };
    };

    // Helper to convert coordinate -> data
    const fromCoords = (x: number, y: number) => {
        if (!chart || !series) return null;
        const t = chart.timeScale().coordinateToTime(x as Coordinate);
        const p = series.coordinateToPrice(y as Coordinate);
        if (t === null || p === null) return null;
        // t is usually unix seconds (number) or object.
        return { t_ms: (t as number) * 1000, p };
    };

    // Force re-render on chart scroll
    const [, setTick] = useState(0);
    useEffect(() => {
        if (!chart) return;
        const handler = () => setTick(t => t + 1);
        chart.timeScale().subscribeVisibleTimeRangeChange(handler);
        return () => chart.timeScale().unsubscribeVisibleTimeRangeChange(handler);
    }, [chart]);

    // Mouse Handlers
    const handleMouseDown = (e: React.MouseEvent) => {
        const rect = svgRef.current?.getBoundingClientRect();
        if (!rect) return;
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        if (isDrawing && !newPoint1) {
            // Start drawing
            const pt = fromCoords(x, y);
            if (pt) setNewPoint1({ time: pt.t_ms / 1000, price: pt.p });
        } else if (isDrawing && newPoint1) {
            // Finish drawing handled in Click or second MouseDown?
            // Let's stick to Drag-To-Draw for v1 consistency with Spec.
            // Spec says: "Click-Drag to create". 
            // So MouseDown = Start, MouseUp = End.
        }
    };

    const handleMouseMove = (e: React.MouseEvent) => {
        const rect = svgRef.current?.getBoundingClientRect();
        if (!rect) return;
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        setMousePos({ x, y });

        if (isDrawing && newPoint1) {
            // Visual feedback only
        }
    };

    const handleMouseUp = async (e: React.MouseEvent) => {
        if (isDrawing && newPoint1) {
            const rect = svgRef.current?.getBoundingClientRect();
            if (!rect) return;
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            const pt2 = fromCoords(x, y);
            if (pt2) {
                // Create Line
                await createTrendline({
                    symbol,
                    t1_ms: newPoint1.time * 1000,
                    p1: newPoint1.price,
                    t2_ms: pt2.t_ms,
                    p2: pt2.p,
                    basis: 'close',
                    mode: 'both'
                });
                setNewPoint1(null);
                onDrawingComplete();
                onUpdate();
            }
        }
    };

    // Render Lines
    const renderLines = () => {
        return trendlines.map(line => {
            const start = toCoords(line.t1_ms, line.p1);
            const end = toCoords(line.t2_ms, line.p2);

            // If points are off-screen, lightweight-charts returns null often.
            // But for trendlines we might want to extrapolate? 
            // For V1 MVP, just hide if endpoints invalid or clamp?
            // Lightweight charts returns null if coordinate is "NaN" but usually gives values even if offscreen.
            // Let's allow nulls to skip rendering for robustness.
            if (!start || !end) return null;

            // const isSelected = false;

            return (
                <g key={line.line_id} className="group cursor-pointer">
                    {/* Invisible hit area */}
                    <line x1={start.x} y1={start.y} x2={end.x} y2={end.y} stroke="transparent" strokeWidth="10" />
                    {/* Visible Line */}
                    <line
                        x1={start.x} y1={start.y} x2={end.x} y2={end.y}
                        stroke={line.enabled ? "#3b82f6" : "#64748b"}
                        strokeWidth="2"
                        strokeDasharray={line.enabled ? "" : "4 4"}
                    />
                    {/* Handles (Endpoints) - simplistic */}
                    <circle cx={start.x} cy={start.y} r="4" className="fill-blue-500 opacity-0 group-hover:opacity-100" />
                    <circle cx={end.x} cy={end.y} r="4" className="fill-blue-500 opacity-0 group-hover:opacity-100" />

                    {/* Delete Button on Hover (Center) */}
                    <foreignObject
                        x={(start.x + end.x) / 2 - 12}
                        y={(start.y + end.y) / 2 - 12}
                        width="24" height="24"
                        className="opacity-0 group-hover:opacity-100"
                    >
                        <button
                            onClick={(e) => { e.stopPropagation(); deleteTrendline(line.line_id).then(onUpdate); }}
                            className="bg-slate-800 rounded-full p-1 text-red-500 border border-slate-700 hover:bg-slate-700"
                        >
                            <X size={14} />
                        </button>
                    </foreignObject>
                </g>
            );
        });
    };

    return (
        <svg
            ref={svgRef}
            className={clsx("absolute inset-0 w-full h-full z-10", isDrawing ? "cursor-crosshair" : "cursor-default")}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
        >
            {renderLines()}

            {/* Drawing Preview */}
            {isDrawing && newPoint1 && mousePos && (() => {
                const start = toCoords(newPoint1.time * 1000, newPoint1.price);
                if (!start) return null;
                return (
                    <line
                        x1={start.x} y1={start.y} x2={mousePos.x} y2={mousePos.y}
                        stroke="#fbbf24" strokeWidth="2" strokeDasharray="4 2"
                    />
                );
            })()}
        </svg>
    );
}
