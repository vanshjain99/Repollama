import React, { useEffect, useRef, useState } from "react";
import {
  Film,
  Play,
  RefreshCw,
  Clock,
  HardDrive,
  Download,
  VideoOff
} from "lucide-react";

interface VideoFile {
  filename: string;
  title: string;
  url: string;
  size_bytes: number;
  created_at: number;
  format: string;
}

export const VideoPlayerGallery: React.FC = () => {
  const [videos, setVideos] = useState<VideoFile[]>([]);
  const [selectedVideo, setSelectedVideo] = useState<VideoFile | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1.0);
  const videoRef = useRef<HTMLVideoElement>(null);

  const fetchVideos = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/api/v1/videos");
      if (res.ok) {
        const data = await res.json();
        const videoList: VideoFile[] = data.videos || [];
        setVideos(videoList);
        if (videoList.length > 0) {
          setSelectedVideo(videoList[0]);
        }
      }
    } catch (err) {
      console.error("Failed to load videos:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVideos();
  }, []);

  const handleSelectVideo = (vid: VideoFile) => {
    setSelectedVideo(vid);
  };

  const handleSpeedChange = (speed: number) => {
    setPlaybackSpeed(speed);
    if (videoRef.current) {
      videoRef.current.playbackRate = speed;
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (timestamp: number) => {
    if (!timestamp) return "Unknown date";
    const date = new Date(timestamp * 1000);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="border border-zinc-200 dark:border-zinc-900 rounded-xl bg-zinc-100/30 dark:bg-zinc-950/40 p-6 space-y-6 shadow-sm hover:border-zinc-300 dark:hover:border-zinc-800/80 transition-all duration-200">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-200 dark:border-zinc-900 pb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-pink-500/10 border border-pink-500/20 flex items-center justify-center text-pink-500">
            <Film className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
              Automated Workflow Video Gallery
            </h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Playback recorded browser walkthroughs from <code className="font-mono text-[11px] bg-zinc-200 dark:bg-zinc-900 px-1 py-0.5 rounded">.repollama_data/videos/</code>
            </p>
          </div>
        </div>

        <button
          onClick={fetchVideos}
          className="p-2 text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-200 rounded-lg hover:bg-zinc-200/50 dark:hover:bg-zinc-800 transition-colors cursor-pointer"
          title="Refresh videos list"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Main Layout: Player & Gallery Selection */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left/Main Area: Video Player */}
        <div className="lg:col-span-2 space-y-3">
          {selectedVideo ? (
            <div className="space-y-3">
              {/* Standard <video> tag with controls */}
              <div className="relative rounded-xl overflow-hidden bg-black border border-zinc-800 shadow-lg group">
                <video
                  ref={videoRef}
                  src={`http://localhost:8000${selectedVideo.url}`}
                  controls
                  className="w-full aspect-video object-contain"
                />

                {/* Overlay Controls / Playback Speed controls */}
                <div className="absolute top-3 right-3 flex items-center gap-2 bg-zinc-900/80 backdrop-blur-md px-2.5 py-1 rounded-lg border border-zinc-700 text-xs text-zinc-200 z-10">
                  <span className="text-[10px] text-zinc-400 font-mono">Speed:</span>
                  {[0.75, 1.0, 1.5, 2.0].map((s) => (
                    <button
                      key={s}
                      onClick={() => handleSpeedChange(s)}
                      className={`px-1.5 py-0.5 rounded text-[11px] font-mono transition-colors cursor-pointer ${
                        playbackSpeed === s
                          ? "bg-violet-600 text-white font-bold"
                          : "hover:bg-zinc-700 text-zinc-300"
                      }`}
                    >
                      {s}x
                    </button>
                  ))}
                </div>
              </div>

              {/* Video Details Bar */}
              <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-lg bg-white dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-900 text-xs">
                <div>
                  <h4 className="font-semibold text-zinc-800 dark:text-zinc-100 flex items-center gap-2">
                    <span>{selectedVideo.title}</span>
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-zinc-200 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 uppercase">
                      {selectedVideo.format}
                    </span>
                  </h4>
                  <div className="flex items-center gap-4 text-[11px] text-zinc-500 mt-1">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3 text-zinc-400" /> {formatDate(selectedVideo.created_at)}
                    </span>
                    <span className="flex items-center gap-1">
                      <HardDrive className="w-3 h-3 text-zinc-400" /> {formatFileSize(selectedVideo.size_bytes)}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <a
                    href={`http://localhost:8000${selectedVideo.url}`}
                    download={selectedVideo.filename}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-zinc-200 hover:bg-zinc-300 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-200 text-xs font-medium transition-colors"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download</span>
                  </a>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center p-12 text-center rounded-xl border border-dashed border-zinc-300 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/20 space-y-3">
              <div className="w-12 h-12 rounded-full bg-zinc-200 dark:bg-zinc-800 flex items-center justify-center text-zinc-400">
                <VideoOff className="w-6 h-6" />
              </div>
              <div>
                <h4 className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
                  No Walkthrough Videos Found
                </h4>
                <p className="text-[11px] text-zinc-500 max-w-sm mt-1">
                  Recorded browser walkthrough videos saved in <code className="font-mono bg-zinc-200 dark:bg-zinc-800 px-1 py-0.5 rounded">.repollama_data/videos/</code> will automatically appear here.
                </p>
              </div>
              <p className="text-[11px] text-zinc-400 italic">
                Run CLI command: <code className="font-mono text-violet-500">repollama record &lt;url&gt; &lt;actions&gt;</code> to capture a video.
              </p>
            </div>
          )}
        </div>

        {/* Right Area: Video Gallery List */}
        <div className="space-y-3">
          <label className="text-xs font-medium text-zinc-500 dark:text-zinc-400 block">
            Video Gallery ({videos.length})
          </label>

          {loading ? (
            <div className="p-8 text-center text-xs text-zinc-500 flex items-center justify-center gap-2">
              <RefreshCw className="w-4 h-4 animate-spin" /> Loading videos...
            </div>
          ) : videos.length === 0 ? (
            <div className="p-4 text-center text-xs text-zinc-500 italic border border-zinc-200 dark:border-zinc-800 rounded-lg">
              No .webm or .mp4 files in video folder.
            </div>
          ) : (
            <div className="space-y-2 max-h-[340px] overflow-y-auto pr-1">
              {videos.map((vid) => {
                const isSelected = selectedVideo?.filename === vid.filename;
                return (
                  <button
                    key={vid.filename}
                    onClick={() => handleSelectVideo(vid)}
                    className={`w-full text-left p-3 rounded-lg border transition-all duration-200 cursor-pointer flex items-center gap-3 ${
                      isSelected
                        ? "bg-pink-500/10 border-pink-500/50 text-pink-900 dark:text-pink-200 shadow-sm"
                        : "bg-white dark:bg-zinc-900/40 border-zinc-200 dark:border-zinc-900 text-zinc-700 dark:text-zinc-300 hover:border-zinc-300 dark:hover:border-zinc-800"
                    }`}
                  >
                    <div className="w-9 h-9 rounded bg-zinc-900 text-pink-400 flex items-center justify-center flex-shrink-0">
                      <Play className="w-4 h-4 fill-pink-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold truncate">{vid.title}</p>
                      <p className="text-[10px] text-zinc-500 truncate font-mono mt-0.5">
                        {formatFileSize(vid.size_bytes)} • {vid.format.toUpperCase()}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default VideoPlayerGallery;
