"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { ToastContainer, Toast } from "@/components/ui/toast"
import { useAuth } from "@/context/AuthContext"
import AuthModal from "@/components/AuthModal"
import Gallery from "@/components/Gallery"
import CodeEditor from "@/components/CodeEditor"
import { authApi, jobApi } from "@/lib/api"
import {
  Loader2,
  Download,
  Copy,
  Check,
  Play,
  AlertCircle,
  RotateCcw,
  Trash2,
  Shuffle,
  Square,
  Circle,
  Code as CodeIcon,
  Terminal,
  FileText,
  StopCircle,
  Film,
  User,
  LogOut,
} from "lucide-react"

interface Job {
  id: string
  prompt: string
  status: "queued" | "running" | "succeeded" | "failed"
  progress?: number
  created_at: string
  updated_at: string
  plan_json?: {
    title: string
    template?: string
    parameters?: Record<string, any>
    scenes?: Array<{
      scene_id: string
      description?: string
      template?: string
      templates?: string[]
      depends_on?: string[]
      parameters?: Record<string, any>
      objects?: Array<{ id: string; type: string; parameters?: Record<string, any> }>
      animations?: Array<{ object_id: string; action: string; parameters?: Record<string, any>; duration?: number }>
      narration?: string
    }>
    // Legacy support for older plans
    nodes?: Array<{ id: string; label: string; shape?: string; color?: string }>
    edges?: Array<{ from_id: string; to_id: string; label?: string }>
    steps?: Array<{
      type: string
      node_id?: string
      edge_index?: number
      text?: string
      direction?: string
      distance?: number
      angle?: number
      scale_factor?: number
    }>
  }
  video_filename?: string
  video_url?: string
  code?: string
  logs?: string
  error?: string
}

const EXAMPLE_PROMPTS = [
  "Matrix multiplication of [[1, 2], [3, 4]] and [[5, 6], [7, 8]] with step-by-step highlights",
  "Projectile motion of a ball launched at 45 degrees",
  "Visualize eigenvectors of matrix [[2, 1], [1, 2]]",
  "Simple neural network: input layer (3), hidden layer (4), output (1)",
  "Explain cache miss with client server cache db",
  "Process flow: User -> Auth -> API -> Database",
]

const PROMPT_CATEGORIES = [
  { label: "Linear Algebra", color: "bg-teal/10 text-teal-dark border-teal/20" },
  { label: "Physics", color: "bg-peach/10 text-peach border-peach/20" },
  { label: "Algorithms", color: "bg-teal/10 text-teal-dark border-teal/20" },
  { label: "System Design", color: "bg-peach/10 text-peach border-peach/20" },
]

export default function Home() {
  const { user, logout } = useAuth()
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [prompt, setPrompt] = useState("")
  const [job, setJob] = useState<Job | null>(null)
  const [loading, setLoading] = useState(false)
  const [polling, setPolling] = useState(false)
  const [activeTab, setActiveTab] = useState("preview")
  const [showEditor, setShowEditor] = useState(false)
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)
  const [showGallery, setShowGallery] = useState(false)
  const [toasts, setToasts] = useState<Toast[]>([])
  const [copiedStates, setCopiedStates] = useState<{ [key: string]: boolean }>({})
  const [showRawJSON, setShowRawJSON] = useState(false)
  const pollIntervalRef = useRef<NodeJS.Timeout>()
  const pollCountRef = useRef(0)
  const toastShownRef = useRef(false)

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

  const showToast = useCallback((type: Toast["type"], message: string) => {
    const id = Math.random().toString(36).substr(2, 9)
    setToasts((prev) => [...prev, { id, type, message }])
  }, [])

  const closeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const pollJobStatus = useCallback((jobId: string) => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
    }

    const poll = async () => {
      try {
        const response = await jobApi.get(jobId)
        const jobData: Job = response.data
        setJob(jobData)
        setSelectedJobId(jobId)

        // Stop polling if job is finished
        if (jobData.status === "succeeded" || jobData.status === "failed") {
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current)
          }
          setLoading(false)
          setPolling(false)

          // Show toast only once
          if (!toastShownRef.current) {
            toastShownRef.current = true
            if (jobData.status === "succeeded") {
              showToast("success", "Animation ready!")
            } else {
              showToast("error", "Animation failed")
            }
          }
        }

        // Backoff: after 15 polls (15s), slow down to 3s
        pollCountRef.current++
        if (pollCountRef.current > 15 && pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current)
          pollIntervalRef.current = setInterval(poll, 3000)
        }
      } catch (err) {
        showToast("error", "Network error while checking job status")
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current)
        }
        setLoading(false)
        setPolling(false)
      }
    }

    // Initial poll immediately, then every 1s
    poll()
    pollIntervalRef.current = setInterval(poll, 1000)
  }, [showToast])

  const resumeJob = useCallback(async (jobId: string) => {
    try {
      const response = await jobApi.get(jobId)
      const jobData: Job = response.data
      setJob(jobData)
      setSelectedJobId(jobId)

      // Resume polling if still in progress
      if (jobData.status === "queued" || jobData.status === "running") {
        setPolling(true)
        pollJobStatus(jobId)
      }
    } catch (err) {
      // Silently fail - just don't resume
    }
  }, [pollJobStatus])

  // Load saved prompt and last job on mount
   useEffect(() => {
     const savedPrompt = localStorage.getItem("lastPrompt")
     const savedJobId = localStorage.getItem("lastJobId")
 
     if (savedPrompt) {
       setPrompt(savedPrompt)
     }
 
     if (savedJobId) {
       // Try to resume last job
       resumeJob(savedJobId)
     }
   }, [user, resumeJob])

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
      }
    }
  }, [])

  // Keyboard shortcut: Ctrl/Cmd + Enter to generate
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault()
        if (prompt.trim() && !loading) {
          handleGenerate()
        }
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [prompt, loading])

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      showToast("error", "Please enter a prompt")
      return
    }

    if (prompt.length > 500) {
      showToast("error", "Prompt too long (max 500 characters)")
      return
    }

    setLoading(true)
    setJob(null)
    setActiveTab("preview")
    pollCountRef.current = 0
    toastShownRef.current = false // Reset toast flag for new job

    // Save prompt to localStorage
    localStorage.setItem("lastPrompt", prompt)

    if (!user) {
      setShowAuthModal(true)
      setLoading(false)
      return
    }

    try {
      const response = await jobApi.create(prompt)
      const data = response.data

      // Save job ID
      localStorage.setItem("lastJobId", data.job_id)

      // Start polling
      setPolling(true)
      pollJobStatus(data.job_id)

      showToast("success", "Animation job created!")
    } catch (err) {
      showToast("error", err instanceof Error ? err.message : "Failed to create job")
      setLoading(false)
    }
  }

  const handleClear = () => {
    setPrompt("")
    localStorage.removeItem("lastPrompt")
  }

  const handleRandomExample = () => {
    const random = EXAMPLE_PROMPTS[Math.floor(Math.random() * EXAMPLE_PROMPTS.length)]
    setPrompt(random)
  }

  const handleRetry = () => {
    handleGenerate()
  }

  const handleRunAgain = () => {
    if (job?.prompt) {
      setPrompt(job.prompt)
      handleGenerate()
    }
  }

  const handleStopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
    }
    setPolling(false)
    setLoading(false)
    showToast("info", "Stopped checking status")
  }, [showToast])

  const getPromptQuality = (text: string): { score: number; label: string; color: string } => {
    let score = 0
    if (text.length > 20) score += 25
    if (text.length > 50) score += 25
    if (/circle|square|triangle|star|rectangle|hexagon/i.test(text)) score += 25
    if (/move|rotate|scale|animate/i.test(text)) score += 25
    
    if (score >= 75) return { score, label: "Excellent", color: "bg-teal text-white" }
    if (score >= 50) return { score, label: "Good", color: "bg-peach text-white" }
    if (score >= 25) return { score, label: "Fair", color: "bg-ink-muted text-white" }
    return { score, label: "Basic", color: "bg-paper-darker text-ink-muted" }
  }

  const copyToClipboard = async (text: string, key: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedStates((prev) => ({ ...prev, [key]: true }))
      showToast("success", "Copied to clipboard!")

      setTimeout(() => {
        setCopiedStates((prev) => ({ ...prev, [key]: false }))
      }, 2000)
    } catch (err) {
      showToast("error", "Failed to copy")
    }
  }

  const getStatusConfig = (status: Job["status"]) => {
    const configs = {
      queued: {
        color: "bg-yellow-100 text-yellow-800 border-yellow-200",
        label: "Queued",
        icon: <Loader2 className="h-3.5 w-3.5 animate-spin" />,
      },
      running: {
        color: "bg-blue-100 text-blue-800 border-blue-200",
        label: "Running",
        icon: <Loader2 className="h-3.5 w-3.5 animate-spin" />,
      },
      succeeded: {
        color: "bg-green-100 text-green-800 border-green-200",
        label: "Succeeded",
        icon: <Check className="h-3.5 w-3.5" />,
      },
      failed: {
        color: "bg-red-100 text-red-800 border-red-200",
        label: "Failed",
        icon: <AlertCircle className="h-3.5 w-3.5" />,
      },
    }
    return configs[status]
  }

  const handleSelectJob = (id: string) => {
    setSelectedJobId(id)
    resumeJob(id)
    setShowGallery(false)
  }

  const videoUrl = job?.video_url || (job?.video_filename ? jobApi.getVideo(job.video_filename) : null)
  const promptQuality = getPromptQuality(prompt)

  return (
    <>
      <ToastContainer toasts={toasts} onClose={closeToast} />

      <div className="min-h-screen flex">
        {/* Left Rail Navigation */}
        <aside className="hidden lg:flex w-16 border-r border-ink/10 bg-white flex-col items-center py-6 gap-6">
          {/* Logo Mark */}
          <div className="relative">
            <div className="h-10 w-10 rounded-xl bg-teal flex items-center justify-center relative overflow-hidden">
              <Film className="h-5 w-5 text-white relative z-10" />
              <div className="absolute inset-0 bg-gradient-to-br from-teal-light/20 to-transparent"></div>
            </div>
          </div>
          
          {/* Nav Anchors */}
          <nav className="flex flex-col gap-4 mt-8">
            <button 
              className="group relative p-2 rounded-lg hover:bg-teal/10 transition-colors"
              title="Prompt Studio"
            >
              <Square className="h-5 w-5 text-ink-muted group-hover:text-teal" />
            </button>
            <button 
              className="group relative p-2 rounded-lg hover:bg-teal/10 transition-colors"
              title="Preview Monitor"
            >
              <Circle className="h-5 w-5 text-ink-muted group-hover:text-teal" />
            </button>
            <button 
              className="group relative p-2 rounded-lg hover:bg-teal/10 transition-colors"
              title="Details"
            >
              <FileText className="h-5 w-5 text-ink-muted group-hover:text-teal" />
            </button>
          </nav>
        </aside>

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col">
          {/* Header */}
          <header className="border-b border-ink/10 bg-white/95 backdrop-blur-sm sticky top-0 z-10">
            <div className="max-w-7xl mx-auto px-6 lg:px-8 py-4 flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-display font-bold text-ink tracking-tight">AnimaStudio</h1>
                <p className="text-sm text-ink-muted mt-0.5">Prompt-driven motion graphics</p>
              </div>
              <div className="flex items-center gap-4">
                <div className="hidden md:flex items-center gap-3 text-xs text-ink-muted">
                  <span>Keyboard:</span>
                  <kbd>⌘ Enter</kbd>
                  <span className="text-ink-muted/50">to generate</span>
                </div>
                
                {user ? (
                  <div className="flex items-center gap-4">
                    <button 
                      onClick={() => setShowGallery(!showGallery)}
                      className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all ${showGallery ? 'bg-ink text-white shadow-lg' : 'bg-white text-ink border border-ink/10 hover:bg-ink/5'}`}
                    >
                      <Film className="h-4 w-4" />
                      {showGallery ? 'Close Gallery' : 'My Animations'}
                    </button>
                    <div className="h-8 w-px bg-ink/10"></div>
                    <div className="flex items-center gap-3">
                      <div className="flex flex-col items-end">
                        <span className="text-xs font-bold text-ink">{user.full_name || "User"}</span>
                        <span className="text-[10px] text-ink-muted">{user.email}</span>
                      </div>
                      <button 
                        onClick={logout}
                        className="p-2 rounded-full hover:bg-peach/10 text-ink-muted hover:text-peach transition-colors"
                        title="Logout"
                      >
                        <LogOut className="h-5 w-5" />
                      </button>
                    </div>
                  </div>
                ) : (
                  <Button 
                    onClick={() => setShowAuthModal(true)}
                    className="bg-teal text-white hover:bg-teal-dark px-6 py-2 rounded-full font-semibold transition-all"
                  >
                    Sign In
                  </Button>
                )}
              </div>
            </div>
          </header>

          {/* Two-Column Studio Layout */}
          <main className="flex-1 overflow-auto">
            <div className="max-w-7xl mx-auto px-6 lg:px-8 py-8">
              {showGallery ? (
                <div className="space-y-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-2xl font-display font-bold text-ink">My Animation Gallery</h2>
                      <p className="text-sm text-ink-muted">View and manage your previous creations</p>
                    </div>
                    <Button onClick={() => setShowGallery(false)} variant="outline" className="rounded-xl">
                      Back to Studio
                    </Button>
                  </div>
                  <Gallery onSelectJob={handleSelectJob} />
                </div>
              ) : (
                <div className="grid lg:grid-cols-2 gap-8 lg:gap-12">
                {/* Left: Prompt Studio */}
                <div className="space-y-6">
                  <div>
                    <h2 className="text-lg font-display font-semibold text-ink mb-1">Prompt Studio</h2>
                    <p className="text-sm text-ink-muted">Describe your animation scene</p>
                  </div>

                  {/* Editor Card */}
                  <div className="studio-card p-6 space-y-4">
                    {/* Mini Toolbar */}
                    <div className="flex items-center justify-between pb-3 border-b border-ink/10">
                      <span className="text-xs font-medium text-ink-muted uppercase tracking-wide">Scene Prompt</span>
                      <div className="flex items-center gap-2">
                        {/* Category Chips */}
                        <div className="hidden md:flex gap-1.5">
                          {PROMPT_CATEGORIES.slice(0, 2).map((cat, idx) => (
                            <button
                              key={idx}
                              onClick={() => {
                                const examples = {
                                  Systems: "Show login flow: user -> frontend -> api -> database",
                                  Math: "Explain Pythagorean theorem with triangles",
                                }
                                setPrompt(examples[cat.label as keyof typeof examples] || EXAMPLE_PROMPTS[0])
                              }}
                              className={`px-2 py-1 text-xs rounded-md border transition-smooth ${cat.color}`}
                            >
                              {cat.label}
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Textarea */}
                    <Textarea
                      value={prompt}
                      onChange={(e) => setPrompt(e.target.value)}
                      placeholder="Two circles moving right with smooth motion..."
                      className="min-h-[180px] resize-none text-base border-ink/10 focus:border-teal focus:ring-teal"
                      disabled={loading}
                    />

                    {/* Prompt Quality Meter */}
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <span className="text-ink-muted">{prompt.length}/500</span>
                        {prompt.length > 450 && (
                          <span className="text-peach font-medium">Near limit</span>
                        )}
                      </div>
                      {prompt.trim() && (
                        <div className="flex items-center gap-2">
                          <span className="text-ink-muted">Quality:</span>
                          <div className={`px-2 py-0.5 rounded text-xs font-medium ${promptQuality.color}`}>
                            {promptQuality.label}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Action Buttons */}
                    <div className="flex gap-2 pt-2">
                      <button
                        onClick={handleGenerate}
                        disabled={loading || !prompt.trim()}
                        className="btn-studio flex-1"
                      >
                        {loading ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Rendering...
                          </>
                        ) : (
                          <>
                            <Play className="mr-2 h-4 w-4" />
                            Generate Animation
                          </>
                        )}
                      </button>
                      <button
                        onClick={handleClear}
                        disabled={loading || !prompt}
                        className="btn-ghost"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                      <button
                        onClick={handleRandomExample}
                        disabled={loading}
                        className="btn-ghost"
                      >
                        <Shuffle className="h-4 w-4" />
                      </button>
                    </div>
                  </div>

                  {/* Prompt Library */}
                  <div className="studio-card p-5">
                    <h3 className="text-sm font-semibold text-ink mb-3">Prompt Library</h3>
                    <div className="grid gap-2">
                      {EXAMPLE_PROMPTS.map((example, idx) => (
                        <button
                          key={idx}
                          onClick={() => setPrompt(example)}
                          disabled={loading}
                          className="text-left px-3 py-2.5 rounded-lg border border-ink/10 hover:border-teal/50 hover:bg-teal/5 transition-smooth text-sm text-ink disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {example}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Tips */}
                  <div className="studio-card p-5 bg-gradient-to-br from-teal/5 to-transparent border-teal/20">
                    <h3 className="font-semibold text-sm text-ink mb-2.5 flex items-center gap-2">
                      <span className="text-lg">💡</span>
                      Crafting Better Prompts
                    </h3>
                    <ul className="space-y-1.5 text-xs text-ink-muted leading-relaxed">
                      <li>• Use descriptive language for nodes and edges</li>
                      <li>• Specify shapes: circles, squares, triangles, stars, hexagons</li>
                      <li>• Add motion verbs: move, rotate, scale, animate</li>
                      <li>• Include colors for visual variety</li>
                    </ul>
                  </div>
                </div>

                {/* Right: Preview Monitor */}
                <div className="lg:sticky lg:top-24 lg:self-start space-y-4">
                  <div>
                    <h2 className="text-lg font-display font-semibold text-ink mb-1">Preview Monitor</h2>
                    <p className="text-sm text-ink-muted">Animation output & details</p>
                  </div>

                  {/* Right: Preview Monitor */}
                  <div className="studio-card min-h-[700px] max-h-screen overflow-hidden flex flex-col">
                    {!job ? (
                      <div className="flex-1 flex flex-col items-center justify-center p-12 text-center">
                        <div className="h-24 w-24 rounded-2xl bg-paper-darker flex items-center justify-center mb-6 relative">
                          <Film className="h-12 w-12 text-ink-muted" />
                          <div className="absolute -top-1 -right-1 h-4 w-4 bg-teal rounded-full"></div>
                        </div>
                        <h3 className="text-xl font-display font-semibold text-ink mb-2">No render yet</h3>
                        <p className="text-sm text-ink-muted max-w-sm">
                          Craft your scene prompt on the left, then click <strong>Generate Animation</strong> to see the magic
                        </p>
                      </div>
                    ) : (
                      <>
                        {/* Job Header */}
                        <div className="p-5 pb-4 border-b border-ink/10">
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-3">
                              <div
                                className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium ${
                                  getStatusConfig(job.status).color
                                }`}
                              >
                                {getStatusConfig(job.status).icon}
                                {getStatusConfig(job.status).label}
                              </div>
                              {polling && (
                                <button
                                  onClick={handleStopPolling}
                                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium text-ink-muted hover:text-ink hover:bg-paper-dark transition-smooth"
                                >
                                  <StopCircle className="h-3.5 w-3.5" />
                                  Stop
                                </button>
                              )}
                            </div>
                            {job.status === "succeeded" && (
                              <button
                                onClick={handleRunAgain}
                                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-teal/10 text-teal-dark hover:bg-teal/20 transition-smooth"
                              >
                                <RotateCcw className="h-3.5 w-3.5" />
                                Run Again
                              </button>
                            )}
                          </div>
                          <p className="text-xs text-ink-muted font-mono">ID: {job.id.slice(0, 12)}</p>
                        </div>

                        {/* Tabs */}
                        <div className="p-5 pb-3">
                          <Tabs>
                            <TabsList className="w-full grid grid-cols-4 bg-paper-dark p-1">
                              <TabsTrigger active={activeTab === "preview"} onClick={() => setActiveTab("preview")}>
                                <Film className="h-4 w-4 mr-1.5" />
                                Preview
                              </TabsTrigger>
                              <TabsTrigger active={activeTab === "blueprint"} onClick={() => setActiveTab("blueprint")}>
                                <FileText className="h-4 w-4 mr-1.5" />
                                Blueprint
                              </TabsTrigger>
                              <TabsTrigger active={activeTab === "script"} onClick={() => setActiveTab("script")}>
                                <CodeIcon className="h-4 w-4 mr-1.5" />
                                Script
                              </TabsTrigger>
                              <TabsTrigger active={activeTab === "console"} onClick={() => setActiveTab("console")}>
                                <Terminal className="h-4 w-4 mr-1.5" />
                                Console
                              </TabsTrigger>
                            </TabsList>
                          </Tabs>
                        </div>

                        {/* Tab Content */}
                        <div className="flex-1 overflow-auto custom-scrollbar px-5 pb-5">
                          {/* Preview Tab */}
                          {activeTab === "preview" && (
                            <div className="space-y-4">
                              {job.status === "succeeded" && videoUrl ? (
                                <>
                                  <div className="monitor-frame">
                                    <div className="relative rounded-lg overflow-hidden bg-black">
                                      <video
                                        controls
                                        className="w-full"
                                        src={videoUrl}
                                        autoPlay
                                        loop
                                      >
                                        Your browser does not support video.
                                      </video>
                                    </div>
                                  </div>
                                  <div className="flex gap-2">
                                    <a
                                      href={videoUrl}
                                      download
                                      className="flex-1 btn-studio text-center"
                                    >
                                      <Download className="mr-2 h-4 w-4 inline" />
                                      Download
                                    </a>
                                    <button
                                      onClick={() => copyToClipboard(job.prompt, "prompt")}
                                      className="flex-1 btn-ghost"
                                    >
                                      {copiedStates.prompt ? (
                                        <>
                                          <Check className="mr-2 h-4 w-4 text-teal" />
                                          Copied
                                        </>
                                      ) : (
                                        <>
                                          <Copy className="mr-2 h-4 w-4" />
                                          Copy Prompt
                                        </>
                                      )}
                                    </button>
                                  </div>
                                </>
                              ) : job.status === "failed" ? (
                                <div className="bg-red-50 border border-red-200 rounded-xl p-6 space-y-4">
                                  <div className="flex items-start gap-3">
                                    <AlertCircle className="h-6 w-6 text-red-600 mt-0.5 flex-shrink-0" />
                                    <div className="flex-1">
                                      <h4 className="font-semibold text-red-900 text-sm mb-1.5">
                                        Render failed
                                      </h4>
                                      <p className="text-sm text-red-700 leading-relaxed">
                                        {job.error || "An unknown error occurred during rendering"}
                                      </p>
                                    </div>
                                  </div>
                                  <button
                                    onClick={handleRetry}
                                    className="w-full btn-ghost border-red-300 text-red-700 hover:bg-red-50"
                                  >
                                    <RotateCcw className="mr-2 h-4 w-4" />
                                    Retry Render
                                  </button>
                                </div>
                              ) : (
                                <div className="monitor-frame flex items-center justify-center min-h-[300px] bg-paper-dark rounded-xl border-2 border-dashed border-ink/10">
                                  <div className="text-center space-y-6 max-w-sm px-6">
                                    <div className="relative inline-block">
                                      <div className="h-16 w-16 rounded-full border-4 border-teal/20 border-t-teal animate-spin mx-auto"></div>
                                      <div className="absolute inset-0 flex items-center justify-center">
                                        <Film className="h-6 w-6 text-teal/40" />
                                      </div>
                                    </div>
                                    
                                    <div className="space-y-2">
                                      <h4 className="font-bold text-ink text-lg capitalize">{job.status}...</h4>
                                      <p className="text-sm text-ink-muted leading-relaxed">
                                        {job.status === "running" 
                                          ? "Our engine is crafting your motion graphic. This usually takes 1-3 minutes." 
                                          : "Your request is in line. We'll start processing it momentarily."}
                                      </p>
                                    </div>

                                    {/* Progress Bar */}
                                    {job.status === "running" && typeof job.progress === "number" && (
                                      <div className="space-y-2">
                                        <div className="h-2 w-full bg-teal/10 rounded-full overflow-hidden">
                                          <div 
                                            className="h-full bg-teal transition-all duration-500 ease-out"
                                            style={{ width: `${job.progress}%` }}
                                          ></div>
                                        </div>
                                        <p className="text-[10px] font-bold text-teal uppercase tracking-wider">{job.progress}% Complete</p>
                                      </div>
                                    )}
                                    
                                    <button 
                                      onClick={handleStopPolling}
                                      className="text-xs font-semibold text-peach hover:text-peach-dark transition-colors uppercase tracking-widest"
                                    >
                                      Stop Monitoring
                                    </button>
                                  </div>
                                </div>
                              )}
                            </div>
                          )}

                          {/* Blueprint Tab */}
                          {activeTab === "blueprint" && (
                            <div className="space-y-5">
                              {job.plan_json ? (
                                <>
                                  <div className="flex items-center justify-between">
                                    <h3 className="text-sm font-semibold text-ink">Animation Blueprint</h3>
                                    <button
                                      onClick={() => setShowRawJSON(!showRawJSON)}
                                      className="text-xs font-medium text-teal-dark hover:text-teal transition-smooth"
                                    >
                                      {showRawJSON ? "Hide" : "Show"} Raw JSON
                                    </button>
                                  </div>

                                  {showRawJSON && (
                                    <div className="space-y-2">
                                      <button
                                        onClick={() => copyToClipboard(JSON.stringify(job.plan_json, null, 2), "plan")}
                                        className="w-full btn-ghost text-xs"
                                      >
                                        {copiedStates.plan ? (
                                          <Check className="mr-1.5 h-3.5 w-3.5 text-teal" />
                                        ) : (
                                          <Copy className="mr-1.5 h-3.5 w-3.5" />
                                        )}
                                        Copy JSON
                                      </button>
                                      <pre className="bg-ink/95 text-paper rounded-lg p-4 overflow-x-auto text-xs leading-relaxed font-mono">
                                        {JSON.stringify(job.plan_json, null, 2)}
                                      </pre>
                                    </div>
                                  )}

                                  {!showRawJSON && (
                                    <div className="space-y-5">
                                      {/* Title */}
                                      <div className="bg-paper-dark rounded-lg p-4 border border-ink/10">
                                        <span className="text-xs font-semibold text-ink-muted uppercase tracking-wide block mb-1.5">
                                          Title
                                        </span>
                                        <p className="text-base font-medium text-ink">{job.plan_json.title}</p>
                                      </div>

                                      {/* Scenes */}
                                      <div>
                                        <span className="text-xs font-semibold text-ink-muted uppercase tracking-wide block mb-2">
                                          Scenes ({job.plan_json.scenes?.length || 0})
                                        </span>
                                        <div className="flex flex-wrap gap-2">
                                          {job.plan_json.scenes?.map((scene) => (
                                            <div
                                              key={scene.scene_id}
                                              className="px-3 py-2 bg-white border border-ink/10 rounded-lg shadow-sm"
                                            >
                                              <span className="text-sm font-medium text-ink block">{scene.scene_id}</span>
                                              <span className="text-xs text-ink-muted mt-0.5 block">
                                                {scene.objects?.length || 0} objects • {scene.animations?.length || 0} animations
                                              </span>
                                            </div>
                                          )) || []}
                                        </div>
                                      </div>

                                      {/* Edges */}
                                      {job.plan_json.edges && job.plan_json.edges.length > 0 && (
                                        <div>
                                          <span className="text-xs font-semibold text-ink-muted uppercase tracking-wide block mb-2">
                                            Edges ({job.plan_json.edges.length})
                                          </span>
                                          <div className="space-y-1.5">
                                            {job.plan_json.edges.map((edge, idx) => (
                                              <div
                                                key={idx}
                                                className="text-xs font-mono bg-white px-3 py-2 rounded-lg border border-ink/10"
                                              >
                                                <span className="text-teal-dark font-medium">{edge.from_id}</span>
                                                <span className="text-ink-muted mx-2">→</span>
                                                <span className="text-teal-dark font-medium">{edge.to_id}</span>
                                                {edge.label && (
                                                  <span className="text-ink-muted ml-2">({edge.label})</span>
                                                )}
                                              </div>
                                            ))}
                                          </div>
                                        </div>
                                      )}

                                      {/* Steps as Timeline */}
                                      {job.plan_json.steps && job.plan_json.steps.length > 0 && (
                                      <div>
                                        <span className="text-xs font-semibold text-ink-muted uppercase tracking-wide block mb-3">
                                          Steps ({job.plan_json.steps.length})
                                        </span>
                                        <div className="relative space-y-3 pl-6">
                                          {/* Timeline line */}
                                          <div className="absolute left-2 top-2 bottom-2 w-px bg-teal/30"></div>

                                          {job.plan_json.steps.map((step, idx) => (
                                            <div key={idx} className="relative">
                                              {/* Timeline dot */}
                                              <div className="absolute -left-6 top-1.5 h-3 w-3 rounded-full bg-teal border-2 border-white shadow-sm"></div>

                                              <div className="bg-white border border-ink/10 rounded-lg p-3 shadow-sm">
                                                <div className="flex items-start gap-2">
                                                  <span className="text-xs font-semibold text-teal-dark min-w-[24px]">
                                                    {idx + 1}
                                                  </span>
                                                  <div className="flex-1">
                                                    <span className="font-mono text-xs font-semibold text-ink block">
                                                      {step.type}
                                                    </span>
                                                    <div className="text-xs text-ink-muted mt-1 space-x-2">
                                                      {step.node_id && <span>node: {step.node_id}</span>}
                                                      {step.edge_index !== undefined && (
                                                        <span>edge: {step.edge_index}</span>
                                                      )}
                                                      {step.text && <span>"{step.text}"</span>}
                                                      {step.direction && <span>dir: {step.direction}</span>}
                                                      {step.distance && <span>dist: {step.distance}</span>}
                                                      {step.angle && <span>angle: {step.angle}°</span>}
                                                    </div>
                                                  </div>
                                                </div>
                                              </div>
                                            </div>
                                          ))}
                                        </div>
                                      </div>
                                      )}
                                    </div>
                                  )}
                                </>
                              ) : (
                                <div className="text-center py-20 text-ink-muted">
                                  <FileText className="h-12 w-12 mx-auto mb-3 opacity-30" />
                                  <p className="text-sm">No blueprint data available</p>
                                </div>
                              )}
                            </div>
                          )}

                          {/* Script Tab */}
                          {activeTab === "script" && (
                            <div className="space-y-3">
                              {job.code ? (
                                <>
                                  <div className="flex items-center justify-between">
                                    <h3 className="text-sm font-semibold text-ink">Generated Manim Code</h3>
                                    <div className="flex items-center gap-2">
                                      <button
                                        onClick={() => {
                                          setSelectedJobId(job.id)
                                          setShowEditor(true)
                                        }}
                                        className="btn-ghost text-xs text-teal hover:bg-teal/5"
                                      >
                                        <CodeIcon className="mr-1.5 h-3.5 w-3.5" />
                                        Edit Code
                                      </button>
                                      <button
                                        onClick={() => copyToClipboard(job.code || "", "code")}
                                        className="btn-ghost text-xs"
                                      >
                                        {copiedStates.code ? (
                                          <Check className="mr-1.5 h-3.5 w-3.5 text-teal" />
                                        ) : (
                                          <Copy className="mr-1.5 h-3.5 w-3.5" />
                                        )}
                                        Copy Code
                                      </button>
                                    </div>
                                  </div>
                                  <pre className="bg-ink/95 text-paper rounded-lg p-4 overflow-x-auto text-xs leading-relaxed font-mono">
                                    <code>{job.code}</code>
                                  </pre>
                                </>
                              ) : (
                                <div className="text-center py-20 text-ink-muted">
                                  <CodeIcon className="h-12 w-12 mx-auto mb-3 opacity-30" />
                                  <p className="text-sm">No code generated yet</p>
                                </div>
                              )}
                            </div>
                          )}

                          {/* Console Tab */}
                          {activeTab === "console" && (
                            <div className="space-y-3">
                              {job.logs ? (
                                <>
                                  <div className="flex items-center justify-between">
                                    <h3 className="text-sm font-semibold text-ink">Execution Logs</h3>
                                    <button
                                      onClick={() => copyToClipboard(job.logs || "", "logs")}
                                      className="btn-ghost text-xs"
                                    >
                                      {copiedStates.logs ? (
                                        <Check className="mr-1.5 h-3.5 w-3.5 text-teal" />
                                      ) : (
                                        <Copy className="mr-1.5 h-3.5 w-3.5" />
                                      )}
                                      Copy Logs
                                    </button>
                                  </div>
                                  <pre className="bg-ink/95 text-paper rounded-lg p-4 overflow-x-auto text-xs leading-relaxed font-mono">
                                    <code>{job.logs}</code>
                                  </pre>
                                </>
                              ) : (
                                <div className="text-center py-20 text-ink-muted">
                                  <Terminal className="h-12 w-12 mx-auto mb-3 opacity-30" />
                                  <p className="text-sm">No logs available yet</p>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </main>

          {showEditor && selectedJobId && (
            <CodeEditor 
              jobId={selectedJobId} 
              onClose={() => setShowEditor(false)} 
              onUpdate={() => resumeJob(selectedJobId)} 
            />
          )}

          {/* Footer */}
          <footer className="border-t border-ink/10 mt-16 py-8 bg-white">
            <div className="max-w-7xl mx-auto px-6 lg:px-8 text-center">
              <p className="text-sm text-ink-muted">
                Crafted with <span className="text-teal">●</span> using Next.js, FastAPI, Celery & Manim
              </p>
              <p className="text-xs text-ink-muted/70 mt-1">
                Powered by Gemini AI
              </p>
            </div>
          </footer>
        </div>
      </div>

      {showAuthModal && <AuthModal onClose={() => setShowAuthModal(false)} />}
    </>
  )
}
