"use client";

import { useState, useEffect } from "react";
import Editor from "@monaco-editor/react";
import { Button } from "@/components/ui/button";
import { Play, Save, Loader2, X, RefreshCcw } from "lucide-react";
import { jobApi } from "@/lib/api";

export default function CodeEditor({ jobId, onClose, onUpdate }: { 
  jobId: string, 
  onClose: () => void,
  onUpdate: () => void 
}) {
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const fetchJob = async () => {
      try {
        const response = await jobApi.get(jobId);
        setCode(response.data.code || "");
      } catch (error) {
        console.error("Failed to fetch job code", error);
      } finally {
        setLoading(false);
      }
    };
    fetchJob();
  }, [jobId]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await jobApi.updateCode(jobId, code);
      onUpdate();
      onClose();
    } catch (error) {
      alert("Failed to save and re-render");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="flex justify-center p-12"><Loader2 className="animate-spin text-teal" /></div>;

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-white">
      <div className="flex items-center justify-between px-6 py-4 border-b border-ink/10 bg-white">
        <div className="flex items-center gap-4">
          <h2 className="text-xl font-bold text-ink">Manim Code Editor</h2>
          <span className="px-2 py-0.5 rounded bg-teal/10 text-teal text-[10px] font-bold uppercase tracking-widest">Job ID: {jobId.slice(0, 8)}...</span>
        </div>
        <div className="flex items-center gap-3">
          <Button 
            variant="outline" 
            onClick={onClose}
            className="rounded-xl border-ink/10 hover:bg-ink/5 transition-all"
          >
            <X className="w-4 h-4 mr-2" />
            Cancel
          </Button>
          <Button 
            onClick={handleSave} 
            disabled={saving}
            className="bg-teal text-white hover:bg-teal-dark rounded-xl px-6 transition-all shadow-lg shadow-teal/20"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <RefreshCcw className="w-4 h-4 mr-2" />}
            Save & Re-render
          </Button>
        </div>
      </div>
      
      <div className="flex-1 overflow-hidden relative">
        <Editor
          height="100%"
          defaultLanguage="python"
          theme="vs-light"
          value={code}
          onChange={(value) => setCode(value || "")}
          options={{
            fontSize: 14,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            automaticLayout: true,
            padding: { top: 20, bottom: 20 },
            lineNumbers: "on",
            glyphMargin: true,
            folding: true,
            lineDecorationsWidth: 10,
            lineNumbersMinChars: 3,
          }}
        />
      </div>
    </div>
  );
}
