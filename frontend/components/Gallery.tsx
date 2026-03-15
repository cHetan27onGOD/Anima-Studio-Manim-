"use client";

import { useState, useEffect } from "react";
import { jobApi } from "@/lib/api";
import { 
  Play, 
  Trash2, 
  Code as CodeIcon, 
  Clock, 
  CheckCircle2, 
  XCircle, 
  Loader2,
  ExternalLink
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useAuth } from "@/context/AuthContext";

interface Job {
  id: string;
  prompt: string;
  status: string;
  video_filename?: string;
  created_at: string;
}

export default function Gallery({ onSelectJob }: { onSelectJob: (id: string) => void }) {
  const { user } = useAuth();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchJobs = async () => {
    try {
      const response = await jobApi.list();
      setJobs(response.data);
    } catch (error) {
      console.error("Failed to fetch jobs", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      fetchJobs();
      const interval = setInterval(fetchJobs, 10000); // Refresh every 10s
      return () => clearInterval(interval);
    }
  }, [user]);

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this animation?")) return;
    try {
      await jobApi.delete(id);
      setJobs(jobs.filter(j => j.id !== id));
    } catch (error) {
      alert("Failed to delete job");
    }
  };

  if (loading) return <div className="flex justify-center p-8"><Loader2 className="animate-spin" /></div>;
  if (jobs.length === 0) return (
    <div className="text-center p-12 bg-white rounded-3xl border border-ink/5">
      <p className="text-ink-muted">No animations yet. Start by typing a prompt above!</p>
    </div>
  );

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {jobs.map((job) => (
        <Card 
          key={job.id} 
          className="group overflow-hidden border-ink/10 hover:border-teal/30 hover:shadow-xl transition-all cursor-pointer bg-white rounded-2xl"
          onClick={() => onSelectJob(job.id)}
        >
          <div className="aspect-video bg-ink/5 relative flex items-center justify-center">
            {job.status === "succeeded" && job.video_filename ? (
              <video 
                src={jobApi.getVideo(job.video_filename)} 
                className="w-full h-full object-cover"
                muted
                onMouseOver={e => e.currentTarget.play()}
                onMouseOut={e => { e.currentTarget.pause(); e.currentTarget.currentTime = 0; }}
              />
            ) : (
              <div className="flex flex-col items-center gap-2">
                {(job.status === "running" || job.status === "queued") ? (
                  <Loader2 className="w-8 h-8 animate-spin text-teal" />
                ) : (
                  <XCircle className="w-8 h-8 text-peach" />
                )}
                <span className="text-xs font-bold uppercase tracking-widest text-ink-muted">{job.status}</span>
              </div>
            )}
            <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity">
              <Button 
                variant="destructive" 
                size="icon" 
                className="h-8 w-8 rounded-full bg-white/90 text-peach hover:bg-peach hover:text-white border-none shadow-sm"
                onClick={(e) => handleDelete(e, job.id)}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>
          <CardContent className="p-4">
            <h3 className="font-bold text-ink line-clamp-1 mb-1">{job.prompt}</h3>
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-ink-muted flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {new Date(job.created_at).toLocaleDateString()}
              </span>
              <div className="flex items-center gap-2">
                 <CodeIcon className="w-4 h-4 text-ink-muted group-hover:text-teal transition-colors" />
                 <Play className="w-4 h-4 text-ink-muted group-hover:text-teal transition-colors" />
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
