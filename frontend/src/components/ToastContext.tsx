import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { X, AlertCircle, CheckCircle, TrendingUp } from 'lucide-react';
import clsx from 'clsx';

type ToastType = 'success' | 'error' | 'info' | 'rise';

interface Toast {
    id: string;
    message: string;
    type: ToastType;
    duration?: number;
}

interface ToastContextType {
    addToast: (message: string, type: ToastType, duration?: number) => void;
    removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function useToast() {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error('useToast must be used within a ToastProvider');
    }
    return context;
}

export function ToastProvider({ children }: { children: ReactNode }) {
    const [toasts, setToasts] = useState<Toast[]>([]);

    const addToast = useCallback((message: string, type: ToastType = 'info', duration = 3000) => {
        const id = Math.random().toString(36).substr(2, 9);
        setToasts((prev) => [...prev, { id, message, type, duration }]);

        if (duration > 0) {
            setTimeout(() => {
                removeToast(id);
            }, duration);
        }
    }, []);

    const removeToast = useCallback((id: string) => {
        setToasts((prev) => prev.filter((toast) => toast.id !== id));
    }, []);

    return (
        <ToastContext.Provider value={{ addToast, removeToast }}>
            {children}
            <div className="toast-container" style={{
                position: 'fixed',
                bottom: '24px',
                right: '24px',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
                zIndex: 9999,
                pointerEvents: 'none' // Allow clicks through container
            }}>
                {toasts.map((toast) => (
                    <div
                        key={toast.id}
                        className={clsx(
                            "toast-item animate-slide-in",
                            toast.type === 'rise' ? 'toast-rise' : '',
                            toast.type === 'error' ? 'toast-error' : '',
                            toast.type === 'success' ? 'toast-success' : ''
                        )}
                        style={{
                            minWidth: '300px',
                            background: 'var(--binance-bg-2)',
                            border: '1px solid var(--border-color)',
                            borderRadius: '8px',
                            padding: '16px',
                            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
                            pointerEvents: 'auto', // Allow interaction with toast
                            display: 'flex',
                            alignItems: 'start',
                            justifyContent: 'space-between',
                            color: 'var(--text-primary)',
                            borderLeft: toast.type === 'rise' ? '4px solid var(--binance-green)' : '4px solid var(--text-tertiary)'
                        }}
                    >
                        <div style={{ display: 'flex', gap: '12px' }}>
                            {toast.type === 'rise' && <TrendingUp size={20} style={{ color: 'var(--binance-green)' }} />}
                            {toast.type === 'error' && <AlertCircle size={20} style={{ color: 'var(--binance-red)' }} />}
                            {toast.type === 'success' && <CheckCircle size={20} style={{ color: 'var(--binance-green)' }} />}

                            <div style={{ fontSize: '14px', lineHeight: '1.4' }}>
                                {toast.message}
                            </div>
                        </div>
                        <button
                            onClick={() => removeToast(toast.id)}
                            style={{ background: 'none', border: 'none', color: 'var(--text-tertiary)', cursor: 'pointer' }}
                        >
                            <X size={16} />
                        </button>
                    </div>
                ))}
            </div>
        </ToastContext.Provider>
    );
}
