import React from "react";
import { SandboxController } from "../dashboard/components/SandboxController";
import { WorkflowExplorer } from "../dashboard/components/WorkflowExplorer";
import { VideoPlayerGallery } from "../dashboard/components/VideoPlayerGallery";

export const SandboxView: React.FC = () => {
  return (
    <div className="space-y-8 animate-fade-in">
      <div className="space-y-1">
        <h2 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
          Runtime Sandbox & Workflow Explorer
        </h2>
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          Manage isolated container runtimes, inspect browser agent sequence diagrams, and view automated video walkthroughs.
        </p>
      </div>

      <SandboxController />
      <WorkflowExplorer />
      <VideoPlayerGallery />
    </div>
  );
};

export default SandboxView;
