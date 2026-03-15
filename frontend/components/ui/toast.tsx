import * as React from "react"
import { cn } from "@/lib/utils"
import { X, CheckCircle2, AlertCircle, Info } from "lucide-react"

export interface Toast {
  id: string
  type: "success" | "error" | "info"
  message: string
}

interface ToastProps {
  toast: Toast
  onClose: (id: string) => void
}

export function ToastItem({ toast, onClose }: ToastProps) {
  React.useEffect(() => {
    const timer = setTimeout(() => {
      onClose(toast.id)
    }, 4000) // Slightly shorter for single toast

    return () => clearTimeout(timer)
  }, [toast.id, onClose])

  const config = {
    success: {
      bg: "bg-teal/10 border-teal/30 text-teal-dark",
      icon: <CheckCircle2 className="h-5 w-5 text-teal flex-shrink-0" />,
    },
    error: {
      bg: "bg-red-50 border-red-200 text-red-900",
      icon: <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0" />,
    },
    info: {
      bg: "bg-paper-dark border-ink/20 text-ink",
      icon: <Info className="h-5 w-5 text-ink-muted flex-shrink-0" />,
    },
  }[toast.type]

  return (
    <div
      className={cn(
        "flex items-center gap-3 px-4 py-3.5 rounded-xl border shadow-lg backdrop-blur-sm animate-slide-in",
        config.bg
      )}
    >
      {config.icon}
      <p className="flex-1 text-sm font-medium">{toast.message}</p>
      <button
        onClick={() => onClose(toast.id)}
        className="p-1 hover:bg-black/10 rounded-md transition-colors"
        aria-label="Close notification"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  )
}

export function ToastContainer({ toasts, onClose }: { toasts: Toast[]; onClose: (id: string) => void }) {
  // Only show the most recent toast (limit to 1)
  const latestToast = toasts.length > 0 ? [toasts[toasts.length - 1]] : []

  return (
    <div className="fixed top-6 right-6 z-50 max-w-md">
      {latestToast.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onClose={onClose} />
      ))}
    </div>
  )
}
