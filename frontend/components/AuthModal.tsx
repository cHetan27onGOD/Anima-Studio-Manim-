"use client"

import { useState } from "react"
import { useAuth } from "@/context/AuthContext"
import { authApi } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Loader2, AlertCircle } from "lucide-react"

export default function AuthModal({ onClose }: { onClose: () => void }) {
  const { login } = useAuth()
  const [isLogin, setIsLogin] = useState(true)
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [fullName, setFullName] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      if (isLogin) {
        const formData = new FormData()
        formData.append("username", email)
        formData.append("password", password)
        const response = await authApi.login(formData)
        login(response.data.access_token)
        onClose()
      } else {
        await authApi.register({ email, password, full_name: fullName })
        setIsLogin(true)
        setError("Registration successful! Please login.")
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.message || err.response?.data?.detail || "An error occurred"
      setError(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <Card className="w-full max-w-md bg-white shadow-2xl border-ink/10">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold text-center">
            {isLogin ? "Welcome Back" : "Create Account"}
          </CardTitle>
          <p className="text-sm text-ink-muted text-center">
            {isLogin ? "Enter your credentials to continue" : "Join AnimAI to save your animations"}
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="p-3 rounded-lg bg-peach/10 border border-peach/20 flex items-center gap-2 text-peach text-sm">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <p>{error}</p>
              </div>
            )}
            
            {!isLogin && (
              <div className="space-y-1">
                <label className="text-xs font-semibold uppercase tracking-wider text-ink-muted">Full Name</label>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full px-4 py-2 rounded-lg border border-ink/10 focus:outline-none focus:ring-2 focus:ring-teal/20 focus:border-teal transition-all"
                  placeholder="John Doe"
                />
              </div>
            )}
            
            <div className="space-y-1">
              <label className="text-xs font-semibold uppercase tracking-wider text-ink-muted">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2 rounded-lg border border-ink/10 focus:outline-none focus:ring-2 focus:ring-teal/20 focus:border-teal transition-all"
                placeholder="name@example.com"
              />
            </div>
            
            <div className="space-y-1">
              <label className="text-xs font-semibold uppercase tracking-wider text-ink-muted">Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-2 rounded-lg border border-ink/10 focus:outline-none focus:ring-2 focus:ring-teal/20 focus:border-teal transition-all"
                placeholder="••••••••"
              />
            </div>
            
            <Button type="submit" className="w-full py-6 bg-ink text-white hover:bg-ink-dark transition-all rounded-xl text-lg font-semibold" disabled={loading}>
              {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : (isLogin ? "Login" : "Register")}
            </Button>
            
            <div className="text-center mt-4">
              <button
                type="button"
                onClick={() => setIsLogin(!isLogin)}
                className="text-sm text-teal hover:underline"
              >
                {isLogin ? "Don't have an account? Register" : "Already have an account? Login"}
              </button>
            </div>
            
            <div className="text-center mt-2">
              <button
                type="button"
                onClick={onClose}
                className="text-sm text-ink-muted hover:text-ink"
              >
                Cancel
              </button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
