import React from "react";
import { useParams } from "react-router";

export const ExplorerPage: React.FC = () => {
  const { repoId } = useParams();
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white">File & Symbol Explorer</h1>
      <p className="text-sm text-[#a1a1aa]">Repository: {repoId}</p>
    </div>
  );
};
