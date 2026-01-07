import { useQuery } from '@tanstack/react-query';
import { fetchKlines } from '../api/client';
import { type UTCTimestamp } from 'lightweight-charts';

export interface CandleData {
    time: UTCTimestamp;
    open: number;
    high: number;
    low: number;
    close: number;
}

export interface VolumeData {
    time: UTCTimestamp;
    value: number;
    color: string;
}

export function useChartData(symbol: string, interval: string = '15m') {
    return useQuery({
        queryKey: ['klines', symbol, interval],
        queryFn: async () => {
            // API returns: [ [t, o, h, l, c, v], ... ]
            const raw = await fetchKlines(symbol, interval);

            const candles: CandleData[] = [];
            const volume: VolumeData[] = [];

            raw.forEach((k: any) => {
                const time = (k[0] / 1000) as UTCTimestamp;
                const open = parseFloat(k[1]);
                const close = parseFloat(k[4]);

                candles.push({
                    time,
                    open,
                    high: parseFloat(k[2]),
                    low: parseFloat(k[3]),
                    close,
                });

                volume.push({
                    time,
                    value: parseFloat(k[5]),
                    color: close >= open ? '#26a69a' : '#ef5350', // Green/Red
                });
            });

            return { candles, volume };
        },
        refetchInterval: 10000,
    });
}
