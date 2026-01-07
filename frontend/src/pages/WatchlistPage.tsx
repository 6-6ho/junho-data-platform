import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchFavorites, createFavoriteGroup, deleteFavoriteGroup, addFavoriteItem, deleteFavoriteItem, fetchTicker } from '../api/client';
import { Plus, Trash2, TrendingUp, TrendingDown, Loader2 } from 'lucide-react';

// --- Components ---

function WatchlistItem({ item, onDelete }: { item: any, onDelete: () => void }) {
    const { data: ticker, isLoading } = useQuery({
        queryKey: ['ticker', item.symbol],
        queryFn: () => fetchTicker(item.symbol),
        refetchInterval: 5000 // Auto-refresh price every 5s
    });

    const price = ticker ? parseFloat(ticker.lastPrice) : 0;
    const change = ticker ? parseFloat(ticker.priceChangePercent) : 0;
    const isUp = change >= 0;

    return (
        <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '8px 0',
            borderBottom: '1px solid var(--border-color)'
        }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontWeight: 600, fontSize: '14px' }}>{item.symbol.replace('USDT', '')}</span>
                <span style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>/USDT</span>
            </div>

            {isLoading ? (
                <Loader2 className="animate-spin" size={14} style={{ color: 'var(--text-tertiary)' }} />
            ) : (
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span style={{ fontFamily: 'monospace', fontSize: '14px' }}>${price.toLocaleString()}</span>
                    <span style={{
                        display: 'flex',
                        alignItems: 'center',
                        color: isUp ? 'var(--binance-green)' : 'var(--binance-red)',
                        fontSize: '13px',
                        fontWeight: 500
                    }}>
                        {isUp ? <TrendingUp size={12} style={{ marginRight: '2px' }} /> : <TrendingDown size={12} style={{ marginRight: '2px' }} />}
                        {change.toFixed(2)}%
                    </span>
                    <button
                        onClick={onDelete}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-tertiary)', padding: '2px' }}
                        title="Remove"
                    >
                        <Trash2 size={14} />
                    </button>
                </div>
            )}
        </div>
    );
}

function WatchlistGroup({ group }: { group: any }) {
    const queryClient = useQueryClient();
    const [newItemSymbol, setNewItemSymbol] = useState('');

    const deleteGroupMut = useMutation({
        mutationFn: deleteFavoriteGroup,
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['favorites'] })
    });

    const addItemMut = useMutation({
        mutationFn: ({ groupId, symbol }: { groupId: string, symbol: string }) => addFavoriteItem(groupId, symbol),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['favorites'] });
            setNewItemSymbol('');
        }
    });

    const deleteItemMut = useMutation({
        mutationFn: deleteFavoriteItem,
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['favorites'] })
    });

    const handleAddItem = (e: React.FormEvent) => {
        e.preventDefault();
        if (newItemSymbol.trim()) {
            let symbol = newItemSymbol.trim().toUpperCase();
            if (!symbol.endsWith('USDT')) {
                symbol += 'USDT';
            }
            addItemMut.mutate({ groupId: group.group_id, symbol });
        }
    };

    return (
        <div className="card" style={{ display: 'flex', flexDirection: 'column', height: 'fit-content' }}>
            {/* Group Header */}
            <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: 600, fontSize: '16px' }}>{group.name}</span>
                <button
                    onClick={() => { if (confirm('Delete group?')) deleteGroupMut.mutate(group.group_id); }}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-tertiary)' }}
                >
                    <Trash2 size={16} />
                </button>
            </div>

            {/* List */}
            <div style={{ padding: '12px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {group.items.map((item: any) => (
                    <WatchlistItem
                        key={item.item_id}
                        item={item}
                        onDelete={() => deleteItemMut.mutate(item.item_id)}
                    />
                ))}

                {group.items.length === 0 && (
                    <div style={{ color: 'var(--text-tertiary)', fontSize: '13px', textAlign: 'center', padding: '12px 0' }}>
                        Empty section
                    </div>
                )}
            </div>

            {/* Add Item Input */}
            <div style={{ padding: '12px', borderTop: '1px solid var(--border-color)' }}>
                <form onSubmit={handleAddItem} style={{ display: 'flex', gap: '8px' }}>
                    <input
                        type="text"
                        value={newItemSymbol}
                        onChange={(e) => setNewItemSymbol(e.target.value)}
                        placeholder="Add Symbol (e.g. BTC)"
                        style={{
                            flex: 1,
                            background: 'var(--binance-bg-3)',
                            border: '1px solid var(--border-color)',
                            padding: '6px 8px',
                            borderRadius: '4px',
                            color: 'var(--text-primary)',
                            fontSize: '13px',
                            textTransform: 'uppercase'
                        }}
                    />
                    <button
                        type="submit"
                        disabled={!newItemSymbol.trim()}
                        style={{
                            background: 'var(--binance-yellow)',
                            color: '#0b0e11',
                            border: 'none',
                            borderRadius: '4px',
                            padding: '6px',
                            cursor: newItemSymbol.trim() ? 'pointer' : 'not-allowed',
                            display: 'flex', alignItems: 'center', justifyContent: 'center'
                        }}
                    >
                        <Plus size={16} />
                    </button>
                </form>
            </div>
        </div>
    );
}

// --- Main Page ---

export default function WatchlistPage() {
    const queryClient = useQueryClient();
    const [newGroupName, setNewGroupName] = useState('');
    const { data: favorites, isLoading } = useQuery({
        queryKey: ['favorites'],
        queryFn: fetchFavorites
    });

    const createGroupMut = useMutation({
        mutationFn: createFavoriteGroup,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['favorites'] });
            setNewGroupName('');
        }
    });

    const handleCreateGroup = (e: React.FormEvent) => {
        e.preventDefault();
        if (newGroupName.trim()) {
            createGroupMut.mutate(newGroupName.trim());
        }
    };

    if (isLoading) return <div style={{ padding: '20px', color: 'var(--text-tertiary)' }}>Loading Watchlist...</div>;

    return (
        <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
            {/* Top Bar */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h2 style={{ fontSize: '24px', fontWeight: 600, color: 'var(--binance-yellow)', margin: 0 }}>Watchlist</h2>

                <form onSubmit={handleCreateGroup} style={{ display: 'flex', gap: '8px' }}>
                    <input
                        type="text"
                        value={newGroupName}
                        onChange={(e) => setNewGroupName(e.target.value)}
                        placeholder="New Section Name"
                        style={{
                            background: 'var(--binance-bg-card)',
                            border: '1px solid var(--border-color)',
                            padding: '8px 12px',
                            borderRadius: '4px',
                            color: 'var(--text-primary)',
                            fontSize: '14px'
                        }}
                    />
                    <button
                        type="submit"
                        disabled={!newGroupName.trim()}
                        className="btn btn-primary"
                        style={{ padding: '8px 16px' }}
                    >
                        + Create Section
                    </button>
                </form>
            </div>

            {/* Grid */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
                gap: '20px',
                alignItems: 'start'
            }}>
                {favorites && favorites.map((group: any) => (
                    <WatchlistGroup key={group.group_id} group={group} />
                ))}

                {(!favorites || favorites.length === 0) && (
                    <div style={{
                        gridColumn: '1 / -1',
                        textAlign: 'center',
                        padding: '40px',
                        color: 'var(--text-tertiary)',
                        border: '1px dashed var(--border-color)',
                        borderRadius: '8px'
                    }}>
                        Create a section to start adding symbols
                    </div>
                )}
            </div>
        </div>
    );
}
